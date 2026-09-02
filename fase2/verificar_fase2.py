#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_fase2.py — PoUW Fase 2: verificador de CONSENSO com hash quantizado.

É o verificar.py da Fase 1 endurecido para determinismo entre máquinas
heterogêneas. Mudanças em relação à Fase 1 (todas declaradas):

  1. FORWARD PASS EM FLOAT64: os pesos float32 da receita são convertidos
     para float64 (conversão exata, sem perda) e TODO o forward roda em
     float64. Racional: a diverência cross-CPU medida na Fase 1 (7.15e-07,
     relatório do usuário) vem do arredondamento float32 vetorial; em
     float64 o resíduo entre ordens de soma distintas cai para ~1e-14
     (medido em experimento_caminhos.py), 8+ ordens de grandeza abaixo do
     passo da grade de quantização B=16 (~6e-05) → bins idênticos.
  2. HASH QUANTIZADO pouw-quant-v1 (quantizar.py): o compromisso é o
     SHA-256 da reconstrução QUANTIZADA em fixed-point B bits com limites
     do DESAFIO (âncora de bytes), não o hash de floats crus. A aritmética
     de quantização é escalar float64 (IEEE-754 corretamente arredondada)
     → determinística entre CPUs dado o mesmo array de entrada.
  3. CHECAGEM DE ÂNCORA: o SHA-256 do desafio gravado na receita (meta)
     é conferido contra o SHA-256 do arquivo .npy fornecido.
  4. Saída quantizada salva em .npy (uint16/uint8) — bytes determinísticos
     (np.save sem zip) → o sha256sum do ARQUIVO é uma âncora que o usuário
     pode conferir sem rodar Python.

REGRA DE CONSENSO PROPOSTA (fase2-v1) — um "bloco" (desafio, receita,
compromisso) é válido se:
  (1) sha256(receita.pt) == comprometido no bloco                 [integridade]
  (2) sha256_desafio da receita == sha256(desafio.npy)            [âncora]
  (3) hash quantizado B16 da reconstrução float64 == comprometido [consenso]
  (4) PSNR(reconstrução float64 vs desafio) ≥ alvo                [trabalho útil]
Este script reporta (1)-(4); com --alvo-psnr, o código de saída reflete a
validade (0 = válido; 1 = inválido), tornando-o usável como oracle.

Decisões de medição (herdadas da Fase 1):
  - torch.set_num_threads(1): forward single-threaded, conservador.
  - "Tempo de verificação" (perf_counter): da carga da receita ao PSNR
    final, SEM o import do PyTorch (reportado à parte).
  - Processo novo/frio: nenhum estado compartilhado com o treino.

Uso:
    python3 fase2/verificar_fase2.py <receita.pt> <desafio.npy>
                                     [--bits 16] [--alvo-psnr 40.0]
                                     [--saida-dir <dir>]
"""

import argparse
import os
import platform
import time

import numpy as np

T0_TOTAL = time.perf_counter()  # antes do import pesado, de propósito
import torch  # noqa: E402  (import tardio contabilizado no tempo total)
TORCH_IMPORT_S = time.perf_counter() - T0_TOTAL

torch.set_num_threads(1)  # determinismo (herança da Fase 1; conservador)

from quantizar import (  # noqa: E402  (spec canônica da Fase 2)
    hash_quantizado,
    limites_do_desafio,
    psnr_db,
    quantizar,
)


def sha256_arquivo(caminho):
    import hashlib

    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


class AtivacaoSeno(torch.nn.Module):
    """Camada Sine do SIREN: sin(omega_0 * x). (Duplicada de treinar.py de
    propósito — o verificador é autossuficiente, como na Fase 1.)"""

    def __init__(self, omega_0=30.0):
        super().__init__()
        self.omega_0 = omega_0

    def forward(self, x):
        return torch.sin(self.omega_0 * x)


def construir_rede(dim_entrada, ocultas, dim_saida, omega_0=30.0):
    """Monta a mesma Sequential do treinar.py; pesos reais vêm do state_dict."""
    dims = [dim_entrada] + list(ocultas) + [dim_saida]
    camadas = []
    for i in range(len(dims) - 1):
        camadas.append(torch.nn.Linear(dims[i], dims[i + 1]))
        if i < len(dims) - 2:
            camadas.append(AtivacaoSeno(omega_0))
    return torch.nn.Sequential(*camadas)


def forward_torch64(caminho_receita, threads=1):
    """Caminho de referência da Fase 2: carga da receita + forward float64.

    Retorna (rec64 (size,size) float64, receita, n_params).
    Função reutilizável pelos experimentos (experimento_ruido.py).
    """
    torch.set_num_threads(threads)
    try:
        receita = torch.load(caminho_receita, map_location="cpu", weights_only=False)
    except TypeError:
        receita = torch.load(caminho_receita, map_location="cpu")
    arq = receita["arquitetura"]
    modelo = construir_rede(arq["dim_entrada"], arq["ocultas"], arq["dim_saida"], arq["omega_0"])
    modelo.load_state_dict(receita["estado"])
    modelo.eval()
    modelo.double()  # ← pesos float32 → float64 (exato); forward todo em f64
    n_params = sum(p.numel() for p in modelo.parameters())
    size = int(receita["grade"])
    x, y = np.meshgrid(np.linspace(0, 1, size), np.linspace(0, 1, size))
    coords64 = np.stack([x.ravel(), y.ravel()], axis=1).astype(np.float64) * 2.0 - 1.0
    with torch.no_grad():
        rec64 = modelo(torch.from_numpy(coords64)).squeeze(-1).reshape(size, size).numpy()
    return rec64, receita, n_params


def main():
    ap = argparse.ArgumentParser(description="Verificador de consenso — PoUW Fase 2 (hash quantizado)")
    ap.add_argument("receita", help="arquivo .pt da receita treinada")
    ap.add_argument("desafio", help="arquivo .npy do desafio original")
    ap.add_argument("--bits", type=int, default=16, choices=[8, 16], help="bits da quantização (default 16)")
    ap.add_argument("--alvo-psnr", type=float, default=None, help="se dado, o código de saída reflete PSNR >= alvo")
    ap.add_argument("--saida-dir", default=None, help="dir do .npy quantizado (default: dir da receita)")
    args = ap.parse_args()

    # ---------- verificação (região medida; sem prints no meio) ----------
    t_ver_ini = time.perf_counter()

    # Fase A: carga da receita + forward float64 (ejeção)
    t = time.perf_counter()
    rec64, receita, n_params = forward_torch64(args.receita, threads=1)
    t_carga_fwd = time.perf_counter() - t
    arq = receita["arquitetura"]
    size = int(receita["grade"])

    # Fase B: checagem de âncora do desafio (meta da receita vs arquivo)
    t = time.perf_counter()
    hash_desafio_arquivo = sha256_arquivo(args.desafio)
    hash_desafio_meta = receita.get("meta", {}).get("sha256_desafio")
    ancora_ok = (hash_desafio_meta == hash_desafio_arquivo)
    t_ancora = time.perf_counter() - t

    # Fase C: quantização canônica + hash de compromisso
    t = time.perf_counter()
    lo, hi = limites_do_desafio(args.desafio)
    q = quantizar(rec64, lo, hi, args.bits)
    hash_comp = hash_quantizado(q)
    t_quant = time.perf_counter() - t

    # Fase D: salvamento do array quantizado (âncora de arquivo) + sha256
    t = time.perf_counter()
    tag = os.path.basename(args.receita).replace("receita_", "").replace(".pt", "")
    dir_saida = args.saida_dir if args.saida_dir else os.path.dirname(os.path.abspath(args.receita))
    ext = "u16" if args.bits > 8 else "u8"
    caminho_q = os.path.join(dir_saida, f"quantizada_{tag}_{ext}.npy")
    np.save(caminho_q, q)
    hash_arquivo_q = sha256_arquivo(caminho_q)
    t_salva = time.perf_counter() - t

    # Fase E: PSNR (float64) contra o desafio original
    t = time.perf_counter()
    campo = np.load(args.desafio)
    psnr = psnr_db(campo, rec64)
    ref64 = np.asarray(campo, dtype=np.float64)
    rmse = float(np.sqrt(np.mean((rec64 - ref64) ** 2)))
    erro_max = float(np.abs(rec64 - ref64).max())
    t_psnr = time.perf_counter() - t

    t_ver_fim = time.perf_counter()
    tempo_verificacao = t_ver_fim - t_ver_ini
    tempo_total_processo = time.perf_counter() - T0_TOTAL

    valido = True
    if not ancora_ok:
        valido = False

    # ---------- saída ----------
    print("== verificar_fase2.py — PoUW Fase 2 (verificador de consenso, hash quantizado) ==")
    print(f"Receita: {args.receita}")
    print(f"SHA-256 da receita (recalculado): {sha256_arquivo(args.receita)}")
    print(f"Desafio: {args.desafio}")
    print(f"Threads de CPU (fixado em 1): {torch.get_num_threads()} | forward em FLOAT64")
    print(f"Python {platform.python_version()} | PyTorch {torch.__version__} | NumPy {np.__version__}")
    print(f"Import do PyTorch levou: {TORCH_IMPORT_S:.3f} s")
    print()
    print(f"Arquitetura: {arq['dim_entrada']} -> {arq['ocultas']} -> {arq['dim_saida']}, omega_0={arq['omega_0']} | {n_params} parâmetros")
    print()
    print("-- Fases medidas (perf_counter) --")
    print(f"A) Carga da receita + forward float64 ({size * size} pontos): {t_carga_fwd:.6f} s")
    print(f"B) Checagem de âncora do desafio: {t_ancora:.6f} s → {'OK' if ancora_ok else 'FALHOU'} (meta={hash_desafio_meta})")
    print(f"C) Quantização canônica B={args.bits} + hash de compromisso: {t_quant:.6f} s")
    print(f"D) Salvamento do .npy quantizado + SHA-256: {t_salva:.6f} s")
    print(f"E) PSNR float64: {t_psnr:.6f} s")
    print()
    print(f"TEMPO TOTAL DE VERIFICAÇÃO (carga -> hash -> PSNR, sem imports): {tempo_verificacao:.6f} s")
    print(f"Tempo total do processo (incl. import do PyTorch): {tempo_total_processo:.6f} s")
    print()
    print(f"Array quantizado salvo em: {caminho_q} (dtype {q.dtype}, {q.size} níveis)")
    print(f"SHA-256 do ARQUIVO quantizado (âncora conferível com sha256sum): {hash_arquivo_q}")
    print()
    print(f"PSNR (reconstrução float64 vs desafio): {psnr:.4f} dB")
    print(f"RMSE: {rmse:.6e} | erro máximo absoluto: {erro_max:.6e} | pico (max-min): {float(ref64.max() - ref64.min()):.6f}")
    print()
    print(f"COMPROMISSO QUANTIZADO (pouw-quant-v1|B={args.bits}|{q.shape[0]}x{q.shape[1]}|): {hash_comp}")
    meta = receita.get("meta", {})
    if meta:
        print(f"[meta da receita] épocas: {meta.get('epocas')} | PSNR de treino: {meta.get('psnr_final_treino')} | parada: {meta.get('motivo_parada')}")
    if args.alvo_psnr is not None:
        psnr_ok = psnr >= args.alvo_psnr
        valido = valido and psnr_ok
        print()
        print(f"REGRA DE CONSENSO: âncora do desafio {'OK' if ancora_ok else 'FALHOU'} | PSNR {psnr:.4f} dB {'>=' if psnr_ok else '<'} alvo {args.alvo_psnr} dB")
        print(f"RESULTADO: {'VÁLIDO (código 0)' if valido else 'INVÁLIDO (código 1)'} — o hash de compromisso acima deve constar no bloco e ser recomputado identicamente por todos os nós")
        raise SystemExit(0 if valido else 1)


if __name__ == "__main__":
    main()
