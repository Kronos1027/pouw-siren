#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar.py — PoUW Fase 1: verificação INDEPENDENTE de uma receita de compressão.

Este script NAO compartilha nenhum estado com treinar.py: é um processo novo que
carrega a receita do disco (arquitetura + pesos), executa o forward pass
("ejeção" do sinal reconstruído), salva a reconstrução em .npy e calcula o
SHA-256 do arquivo gerado — como se rodasse em outra máquina, por outra pessoa.
A montagem da rede DUPLICA de propósito o construtor do treinar.py (o script
precisa ser autossuficiente); os hiperparâmetros de arquitetura vêm da própria
receita salva em disco.

Decisões declaradas:
  - torch.set_num_threads(1): forward single-threaded por DETERMINISMO do hash
    (resultado conservador: a verificação fica mais lenta, não mais rápida).
  - Coordenadas: mesma grade do desafio.py, mapeadas [0,1] -> [-1,1] — bloco de
    código IDÊNTICO ao do treinar.py (os pesos só fazem sentido com o mesmo
    mapeamento).
  - "Tempo de verificação" (perf_counter) = da carga da receita ao PSNR final
    (carga + forward + salvamento + SHA-256 + PSNR), SEM o tempo de import do
    PyTorch — que é reportado à parte, junto com o tempo total do processo.
  - A reconstrução é salva em float32 (saída nativa da rede) via np.save
    (formato sem contêiner zip; bytes determinísticos para um mesmo array).

Uso:
    python3 verificar.py <receita.pt> <desafio.npy>
"""

import argparse
import hashlib
import os
import platform
import time

import numpy as np

T0_TOTAL = time.perf_counter()  # antes do import pesado, de propósito
import torch  # noqa: E402  (import tardio contabilizado no tempo total do processo)
TORCH_IMPORT_S = time.perf_counter() - T0_TOTAL

torch.set_num_threads(1)  # determinismo do forward (ver docstring)


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


class AtivacaoSeno(torch.nn.Module):
    """Camada Sine do SIREN: sin(omega_0 * x). (Duplicada de treinar.py de propósito.)"""

    def __init__(self, omega_0=30.0):
        super().__init__()
        self.omega_0 = omega_0

    def forward(self, x):
        return torch.sin(self.omega_0 * x)


def construir_rede(dim_entrada, ocultas, dim_saida, omega_0=30.0):
    """Monta a mesma Sequential do treinar.py; os pesos reais vêm do state_dict."""
    dims = [dim_entrada] + list(ocultas) + [dim_saida]
    camadas = []
    for i in range(len(dims) - 1):
        camadas.append(torch.nn.Linear(dims[i], dims[i + 1]))
        if i < len(dims) - 2:
            camadas.append(AtivacaoSeno(omega_0))
    return torch.nn.Sequential(*camadas)


def psnr_db(referencia, reconstrucao):
    """Idêntica à do treinar.py: 20*log10(pico/RMSE), pico = max-min, float64."""
    ref = np.asarray(referencia, dtype=np.float64)
    rec = np.asarray(reconstrucao, dtype=np.float64)
    rmse = float(np.sqrt(np.mean((rec - ref) ** 2)))
    pico = float(ref.max() - ref.min())
    return 20.0 * np.log10(pico / rmse)


def main():
    ap = argparse.ArgumentParser(description="Verificação independente — PoUW Fase 1")
    ap.add_argument("receita", help="arquivo .pt da receita treinada")
    ap.add_argument("desafio", help="arquivo .npy do desafio original (para PSNR)")
    args = ap.parse_args()

    # ---------- verificação (região medida; sem prints no meio) ----------
    t_ver_ini = time.perf_counter()

    # Fase A: carga da receita (torch.load + montagem da rede + state_dict)
    t = time.perf_counter()
    try:
        receita = torch.load(args.receita, map_location="cpu", weights_only=False)
    except TypeError:  # torch muito antigo sem weights_only
        receita = torch.load(args.receita, map_location="cpu")
    arq = receita["arquitetura"]
    modelo = construir_rede(arq["dim_entrada"], arq["ocultas"], arq["dim_saida"], arq["omega_0"])
    modelo.load_state_dict(receita["estado"])
    modelo.eval()
    n_params = sum(p.numel() for p in modelo.parameters())
    t_carga = time.perf_counter() - t

    # Fase B: grade + forward pass (ejeção)
    t = time.perf_counter()
    size = int(receita["grade"])
    # [INICIO BLOCO COMPARTILHADO COM treinar.py — copiado igual, propósito]
    x, y = np.meshgrid(np.linspace(0, 1, size), np.linspace(0, 1, size))
    coords = np.stack([x.ravel(), y.ravel()], axis=1).astype(np.float32) * 2.0 - 1.0
    # [FIM BLOCO COMPARTILHADO]
    with torch.no_grad():
        rec = modelo(torch.from_numpy(coords)).squeeze(-1).reshape(size, size).numpy()
    t_forward = time.perf_counter() - t

    # Fase C: salvamento da reconstrução + SHA-256
    t = time.perf_counter()
    tag = os.path.basename(args.receita).replace("receita_", "").replace(".pt", "")
    caminho_rec = f"reconstrucao_{tag}.npy"
    np.save(caminho_rec, rec)  # float32, formato determinístico
    hash_rec = sha256_arquivo(caminho_rec)
    t_salva = time.perf_counter() - t

    # Fase D: PSNR contra o desafio original
    t = time.perf_counter()
    campo = np.load(args.desafio)
    psnr = psnr_db(campo, rec)
    ref64 = np.asarray(campo, dtype=np.float64)
    rec64 = np.asarray(rec, dtype=np.float64)
    rmse = float(np.sqrt(np.mean((rec64 - ref64) ** 2)))
    erro_max = float(np.abs(rec64 - ref64).max())
    t_psnr = time.perf_counter() - t

    t_ver_fim = time.perf_counter()
    tempo_verificacao = t_ver_fim - t_ver_ini
    tempo_total_processo = time.perf_counter() - T0_TOTAL

    # ---------- saída ----------
    print("== verificar.py — PoUW Fase 1 (verificação independente em CPU) ==")
    print(f"Receita: {args.receita}")
    print(f"SHA-256 da receita (recalculado aqui; conferir com o reportado no treino): {sha256_arquivo(args.receita)}")
    print(f"Desafio de referência: {args.desafio}")
    print(f"Threads de CPU (fixado em 1 por determinismo): {torch.get_num_threads()}")
    print(f"Python {platform.python_version()} | PyTorch {torch.__version__} | NumPy {np.__version__}")
    print(f"Import do PyTorch levou: {TORCH_IMPORT_S:.3f} s")
    print()
    print(f"Arquitetura lida da receita: {arq['dim_entrada']} -> {arq['ocultas']} -> {arq['dim_saida']}, omega_0={arq['omega_0']}")
    print(f"Total de parâmetros do modelo: {n_params}")
    print()
    print("-- Fases medidas (perf_counter) --")
    print(f"A) Carga da receita (torch.load + montagem da rede): {t_carga:.6f} s")
    print(f"B) Forward pass / ejeção ({size * size} pontos): {t_forward:.6f} s")
    print(f"C) Salvamento da reconstrução + SHA-256: {t_salva:.6f} s")
    print(f"D) PSNR contra o desafio original: {t_psnr:.6f} s")
    print()
    print(f"TEMPO TOTAL DE VERIFICAÇÃO (carga -> hash -> PSNR, sem imports): {tempo_verificacao:.6f} s")
    print(f"Tempo total do processo (incl. import do PyTorch): {tempo_total_processo:.6f} s")
    print()
    print(f"Reconstrução salva em: {caminho_rec}")
    print(f"SHA-256 da reconstrução: {hash_rec}")
    print(f"PSNR (reconstrução vs desafio): {psnr:.4f} dB")
    print(f"RMSE: {rmse:.6e} | erro máximo absoluto: {erro_max:.6e} | pico (max-min): {float(ref64.max() - ref64.min()):.6f}")
    meta = receita.get("meta", {})
    if meta:
        print(f"[meta da receita] épocas: {meta.get('epocas')} | PSNR de treino: {meta.get('psnr_final_treino')} | parada: {meta.get('motivo_parada')}")


if __name__ == "__main__":
    main()
