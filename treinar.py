#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
treinar.py — PoUW Fase 1: treino de uma SIREN em CPU para comprimir um desafio 2D.

Entrada : arquivo .npy do desafio (gerado por desafio.py)
Saida   : "receita" de compressao (arquitetura + pesos treinados), salva via torch.save

Arquitetura e inicializacao ADAPTADAS do codigo publico de referencia:
  - Paper: Sitzmann et al., "Implicit Neural Representations with Periodic
    Activation Functions" (NeurIPS 2020) — https://arxiv.org/abs/2006.09661
  - Codigo: https://github.com/vsitzmann/siren (modules.py):
      * first_layer_sine_init : W ~ U(-1/n_in, 1/n_in)
      * sine_init (ocultas)   : W ~ U(-sqrt(6/n_in)/omega_0, +sqrt(6/n_in)/omega_0)
      * ativacao: sin(omega_0 * x), omega_0 = 30
      * bias e camada de saida: inicializacao default do PyTorch (o repo oficial
        so reinicializa os pesos das SineLayers)

Decisoes declaradas (tudo o que pode afetar os numeros):
  - Rede: 2 -> 128 -> 128 -> 128 -> 1 (3 camadas ocultas, 128 unidades).
  - Coordenadas de entrada mapeadas de [0,1] para [-1,1] (pratica do repo
    oficial para fitting de sinais em grade).
  - Otimizador: Adam, lr = 1e-4 (default do repo oficial p/ image fitting).
  - "Epoca" = uma atualizacao com o batch completo (4096 pontos p/ grade 64x64).
  - Criterio de parada: PSNR >= alvo (avaliado a cada 100 epocas) OU
    max-epocas concluidas, o que ocorrer primeiro.
  - PSNR = 20*log10(pico/RMSE); pico = max-min do desafio ORIGINAL (float64);
    RMSE calculado em float64.
  - Seed de inicializacao da rede derivada do SHA-256 do arquivo .npy do
    desafio (treino reproduzivel em principio nesta maquina/ambiente).
  - Threads: default do torch (todas as CPUs visiveis). A verificacao
    (verificar.py) fixa 1 thread por determinismo.
  - Tempo de treino (perf_counter): da construcao do modelo ate a avaliacao
    final pos-treino. Imports e carregamento do .npy ficam FORA dessa medida
    (o tempo total do script, incluindo imports, e reportado separadamente).

Uso:
    python3 treinar.py <desafio.npy> [--saida <arquivo.pt>]
                       [--max-epocas 5000] [--alvo-psnr 40.0] [--lr 1e-4]
"""

import argparse
import hashlib
import platform
import time

import numpy as np

T0_TOTAL = time.perf_counter()  # antes do import pesado, de proposito
import torch  # noqa: E402  (import tardio contabilizado no tempo total do script)
TORCH_IMPORT_S = time.perf_counter() - T0_TOTAL


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


class AtivacaoSeno(torch.nn.Module):
    """Camada Sine do SIREN: sin(omega_0 * x)."""

    def __init__(self, omega_0=30.0):
        super().__init__()
        self.omega_0 = omega_0

    def forward(self, x):
        return torch.sin(self.omega_0 * x)


def construir_rede(dim_entrada, ocultas, dim_saida, omega_0=30.0, seed=0):
    """Sequential: Linear, Seno, Linear, Seno, Linear, Seno, Linear (saida linear).

    Inicializacao conforme repo oficial (ver docstring do modulo).
    """
    torch.manual_seed(seed)
    dims = [dim_entrada] + list(ocultas) + [dim_saida]
    camadas = []
    for i in range(len(dims) - 1):
        lin = torch.nn.Linear(dims[i], dims[i + 1])
        n_in = dims[i]
        with torch.no_grad():
            if i == 0:
                # first_layer_sine_init (repo oficial)
                lin.weight.uniform_(-1.0 / n_in, 1.0 / n_in)
            elif i < len(dims) - 2:
                # sine_init (repo oficial)
                lim = float(np.sqrt(6.0 / n_in)) / omega_0
                lin.weight.uniform_(-lim, lim)
            # ultima Linear (saida): init default do PyTorch, como no repo oficial
        camadas.append(lin)
        if i < len(dims) - 2:
            camadas.append(AtivacaoSeno(omega_0))
    return torch.nn.Sequential(*camadas)


def psnr_db(referencia, reconstrucao):
    """PSNR em dB: 20*log10(pico/RMSE), pico = max-min da referencia, tudo em float64."""
    ref = np.asarray(referencia, dtype=np.float64)
    rec = np.asarray(reconstrucao, dtype=np.float64)
    rmse = float(np.sqrt(np.mean((rec - ref) ** 2)))
    pico = float(ref.max() - ref.min())
    return 20.0 * np.log10(pico / rmse)


def main():
    ap = argparse.ArgumentParser(description="Treino SIREN (CPU) — PoUW Fase 1")
    ap.add_argument("desafio", help="arquivo .npy do desafio")
    ap.add_argument("--saida", default=None, help="arquivo de saida da receita (.pt)")
    ap.add_argument("--max-epocas", type=int, default=5000)
    ap.add_argument("--alvo-psnr", type=float, default=40.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    args = ap.parse_args()

    # ---------- dados ----------
    campo = np.load(args.desafio)
    assert campo.ndim == 2 and campo.shape[0] == campo.shape[1], "esperado campo 2D quadrado"
    size = int(campo.shape[0])

    # Grade IDENTICA a do desafio.py (mesma chamada, mesma ordem de eixos).
    # [INICIO BLOCO COMPARTILHADO COM verificar.py — copiado igual, proposito]
    x, y = np.meshgrid(np.linspace(0, 1, size), np.linspace(0, 1, size))
    coords = np.stack([x.ravel(), y.ravel()], axis=1).astype(np.float32) * 2.0 - 1.0
    # [FIM BLOCO COMPARTILHADO]
    alvo = campo.astype(np.float32).ravel()

    t_coords = torch.from_numpy(coords)
    t_alvo = torch.from_numpy(alvo)

    hash_desafio = sha256_arquivo(args.desafio)
    seed_rede = int(hash_desafio[:8], 16)  # derivada do hash do arquivo do desafio

    ocultas = [128, 128, 128]

    if args.saida is None:
        base = args.desafio.rsplit("/", 1)[-1].replace("desafio_", "").replace(".npy", "")
        saida = f"receita_{base}.pt"
    else:
        saida = args.saida

    print("== treinar.py — PoUW Fase 1 (SIREN em CPU) ==")
    print(f"Desafio: {args.desafio}")
    print(f"SHA-256 do arquivo de desafio: {hash_desafio}")
    print(f"Grade: {size}x{size} ({size * size} pontos) | pico (max-min) do campo: {float(campo.max() - campo.min()):.6f}")
    print(f"Seed de inicializacao da rede (derivada do SHA-256 do desafio): {seed_rede}")
    print(f"Arquitetura: 2 -> {ocultas} -> 1, ativacao sin(30*x) (SIREN)")
    print(f"Criterio de parada: PSNR >= {args.alvo_psnr} dB (avaliado a cada 100 epocas) OU {args.max_epocas} epocas")
    print(f"Otimizador: Adam, lr={args.lr} | batch completo ({size * size} amostras/epoca)")
    print(f"Threads de CPU (torch, default): {torch.get_num_threads()}")
    print(f"Python {platform.python_version()} | PyTorch {torch.__version__} | NumPy {np.__version__}")
    print(f"Import do PyTorch levou: {TORCH_IMPORT_S:.3f} s")

    # ---------- treino (regiao medida) ----------
    t_treino_ini = time.perf_counter()
    modelo = construir_rede(2, ocultas, 1, omega_0=30.0, seed=seed_rede)
    n_params = sum(p.numel() for p in modelo.parameters())
    print(f"Total de parametros do modelo: {n_params}")

    otim = torch.optim.Adam(modelo.parameters(), lr=args.lr)
    mse = torch.nn.MSELoss()

    epoca = 0
    psnr_atual = float("-inf")
    motivo = "max_epocas"
    while epoca < args.max_epocas:
        otim.zero_grad()
        saida_fwd = modelo(t_coords).squeeze(-1)
        perda = mse(saida_fwd, t_alvo)
        perda.backward()
        otim.step()
        epoca += 1
        if epoca % 100 == 0:
            with torch.no_grad():
                rec = modelo(t_coords).squeeze(-1).reshape(size, size).numpy()
            psnr_atual = psnr_db(campo, rec)
            t_dec = time.perf_counter() - t_treino_ini
            print(f"[epoca {epoca:>5}] PSNR={psnr_atual:7.2f} dB | perda={perda.item():.6e} | t={t_dec:8.2f} s")
            if psnr_atual >= args.alvo_psnr:
                motivo = "alvo_psnr"
                break
    tempo_treino = time.perf_counter() - t_treino_ini  # inclui a avaliacao final abaixo

    # avaliacao final pos-treino (dentro da regiao medida)
    with torch.no_grad():
        rec_final = modelo(t_coords).squeeze(-1).reshape(size, size).numpy()
    psnr_final = psnr_db(campo, rec_final)
    tempo_treino = time.perf_counter() - t_treino_ini

    # ---------- salvamento ----------
    t_salva_ini = time.perf_counter()
    receita = {
        "formato": "pouw-fase1/receita/v1",
        "arquitetura": {
            "dim_entrada": 2,
            "ocultas": ocultas,
            "dim_saida": 1,
            "omega_0": 30.0,
        },
        "grade": size,
        "estado": modelo.state_dict(),
        "meta": {
            "desafio": args.desafio,
            "sha256_desafio": hash_desafio,
            "epocas": epoca,
            "psnr_final_treino": psnr_final,
            "motivo_parada": motivo,
            "lr": args.lr,
        },
    }
    torch.save(receita, saida)
    hash_receita = sha256_arquivo(saida)
    tempo_salva = time.perf_counter() - t_salva_ini

    tempo_total = time.perf_counter() - T0_TOTAL

    psnr_max_str = f"{psnr_atual:.2f}" if np.isfinite(psnr_atual) else "n/a (nenhuma avaliacao: max-epocas < 100)"

    print()
    if motivo == "alvo_psnr":
        print(f"Parada: PSNR {psnr_atual:.2f} dB >= {args.alvo_psnr} dB na epoca {epoca}")
    else:
        print(f"Parada: {args.max_epocas} epocas concluidas | PSNR maximo medido: {psnr_max_str} dB")
    print(f"PSNR final (avaliacao pos-treino, float64): {psnr_final:.4f} dB")
    print(f"Total de epocas executadas: {epoca}")
    print(f"Tempo de treino (perf_counter; da construcao do modelo a avaliacao final): {tempo_treino:.6f} s")
    print(f"Tempo de salvamento da receita (torch.save + SHA-256): {tempo_salva:.6f} s")
    print(f"Tempo total do script (perf_counter, incl. imports): {tempo_total:.6f} s")
    print(f"Receita salva em: {saida}")
    print(f"SHA-256 da receita: {hash_receita}")


if __name__ == "__main__":
    main()
