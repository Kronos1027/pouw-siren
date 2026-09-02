#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
experimento_prefixo.py — PoUW Fase 2, EXPERIMENTO E5.

PERGUNTA: qual o custo real de calibrar dificuldade EXPONENCIAL sobre o
compromisso quantizado (o análogo exato do "leading zeros" do Bitcoin)?

MÉTODO: moagem de nonce sobre a pré-imagem
    SHA-256( "pouw-bloco-demo-v1|" ‖ compromisso_hex ‖ "|" ‖ nonce )
até o digest ter k bits zero à frente. k ∈ {8, 12, 16, 20} com 3 ensaios
independentes cada, e k=24 com 1 ensaio (nonce inicial de cada ensaio sai de
default_rng(20260902) — determinístico e documentado). O compromisso usado é
o REAL: recomputado aqui da receita oficial da seed 001 via forward float64
(mesmo pipeline do verificar_fase2.py).

CALIBRAÇÃO DE TAXA: 100.000 hashes cronometrados → taxa efetiva.
EXTRAPOLAÇÃO: k ∈ {28, 32, 36, 40} derivado ARITMETICAMENTE da taxa medida
(2^k / taxa) — rotulado como extrapolado, NÃO medido.

FRAMING HONESTO: moar nonce é queima de hash pura (a crítica clássica ao
PoW). Num PoUW-SIREN ela só faz sentido como AJUSTE FINO de dificuldade
(barato, exponencial, independente do trabalho útil) sobre um bloco cujo
custo dominante é o treino; o compromisso em si não é "moível" sem retreinar.
O debate de design (quanto prefixo vs. quanto PSNR) fica para a Fase 3.

Uso (a partir da raiz do repositório):
    python3 fase2/experimento_prefixo.py receita_b0f90ffe.pt desafio_b0f90ffe.npy
"""

import hashlib
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.perf_counter()

RAIZ = Path(__file__).resolve().parent.parent
K_MEDIDOS = [8, 12, 16, 20]
K_EXTRAPOLADOS = [28, 32, 36, 40]
N_ENSAIOS = 3
N_ENSAIOS_K24 = 1
SEMENTE_RNG = 20260902
N_CALIB = 100_000
PREFIXO_BLOCO = "pouw-bloco-demo-v1"


def bits_zero_prefixo(digest: bytes) -> int:
    """Número de bits zero à frente do digest (byte a byte)."""
    n = 0
    for b in digest:
        if b == 0:
            n += 8
        else:
            n += 8 - b.bit_length()
            break
    return n


def moer(comp_hex: str, k: int, nonce0: int):
    """Moagem de nonce até bits_zero_prefixo >= k. Retorna (tentativas, tempo, nonce, digest_hex)."""
    prefixo = f"{PREFIXO_BLOCO}|{comp_hex}|".encode("ascii")
    t_ini = time.perf_counter()
    nonce = nonce0
    tentativas = 0
    while True:
        d = hashlib.sha256(prefixo + str(nonce).encode("ascii")).digest()
        tentativas += 1
        if bits_zero_prefixo(d) >= k:
            break
        nonce += 1
    return tentativas, time.perf_counter() - t_ini, nonce, d.hex()


def main():
    print("== experimento_prefixo.py — PoUW Fase 2, E5 (dificuldade exponencial por prefixo) ==")
    print(f"Python {platform.python_version()}")
    print(f"Pré-imagem do nonce: SHA-256('{PREFIXO_BLOCO}|<compromisso_hex>|<nonce>')")
    print(f"k medidos: {K_MEDIDOS} ({N_ENSAIOS} ensaios cada) + k=24 ({N_ENSAIOS_K24} ensaio) | RNG dos nonces iniciais: default_rng({SEMENTE_RNG})")
    print(f"k extrapolados (NÃO medidos): {K_EXTRAPOLADOS}")
    print()

    # Compromisso real da seed 001 (recomputado, mesmo pipeline do verificar_fase2.py)
    receita = sys.argv[1] if len(sys.argv) > 1 else str(RAIZ / "receita_b0f90ffe.pt")
    desafio = sys.argv[2] if len(sys.argv) > 2 else str(RAIZ / "desafio_b0f90ffe.npy")
    import torch  # import tardio (só para recomputar o compromisso)

    from quantizar import hash_quantizado, limites_do_desafio, quantizar
    from verificar_fase2 import forward_torch64

    torch.set_num_threads(1)
    rec64, _, _ = forward_torch64(receita, threads=1)
    lo, hi = limites_do_desafio(desafio)
    comp = hash_quantizado(quantizar(rec64, lo, hi, 16))
    print(f"Compromisso quantizado da seed 001 (recomputado aqui, B=16): {comp}")
    print()

    # Calibração de taxa
    prefixo = f"{PREFIXO_BLOCO}|{comp}|".encode("ascii")
    t_ini = time.perf_counter()
    for i in range(N_CALIB):
        hashlib.sha256(prefixo + str(i).encode("ascii")).digest()
    t_cal = time.perf_counter() - t_ini
    taxa = N_CALIB / t_cal
    print(f"Calibração de taxa: {N_CALIB} hashes em {t_cal:.4f} s → {taxa / 1e6:.3f} M hashes/s (1 thread, Python puro)")
    print()

    rng = np.random.default_rng(SEMENTE_RNG)

    resultados = {}
    for k in K_MEDIDOS + [24]:
        n_ensaios = N_ENSAIOS_K24 if k == 24 else N_ENSAIOS
        ensaios = []
        for e in range(n_ensaios):
            nonce0 = int(rng.integers(0, 2**63))
            tent, t, nonce, dhex = moer(comp, k, nonce0)
            ensaios.append((tent, t, nonce, dhex))
            print(f"  k={k:2d} | ensaio {e + 1}/{n_ensaios} | tentativas={tent:>10,} | tempo={t:8.3f} s | nonce={nonce} | digest={dhex[:16]}…")
        tentativas = [a[0] for a in ensaios]
        tempos = [a[1] for a in ensaios]
        mediano = ensaios[min(range(len(ensaios)), key=lambda i: abs(tentativas[i] - statistics.median(tentativas)))]
        resultados[k] = (tentativas, tempos, mediano)
        print()

    print("======== TABELA-RESUMO E5 (medido; 2^k é a esperança teórica) ========")
    print(f"{'k':>3} | {'2^k (esperado)':>15} | {'tentativas mediana':>18} | {'mín–máx':>15} | {'tempo mediano (s)':>17} | digest mediano (16 hex)")
    print("-" * 110)
    for k in K_MEDIDOS + [24]:
        tentativas, tempos, mediano = resultados[k]
        print(f"{k:>3} | {2**k:>15,} | {int(statistics.median(tentativas)):>18,} | {min(tentativas):>7,}–{max(tentativas):<7,} | {statistics.median(tempos):>17.3f} | {mediano[3][:16]}…")
    print()

    print("======== EXTRAPOLAÇÃO (derivada aritmeticamente da taxa medida; NÃO executada) ========")
    print(f"{'k':>3} | {'2^k':>13} | tempo esperado à taxa medida ({taxa / 1e6:.3f} M hashes/s)")
    print("-" * 60)
    for k in K_EXTRAPOLADOS:
        t_esp = 2**k / taxa
        if t_esp < 3600:
            unidade = f"{t_esp:,.0f} s"
        elif t_esp < 86400:
            unidade = f"{t_esp / 3600:,.1f} h"
        elif t_esp < 86400 * 365:
            unidade = f"{t_esp / 86400:,.1f} dias"
        else:
            unidade = f"{t_esp / (86400 * 365):,.1f} anos"
        print(f"{k:>3} | {2**k:>13,} | {unidade}")
    print()

    print("FRAMING (dado + advertência de design):")
    print("  - Moer nonce é queima de hash PURA (a crítica clássica ao PoW): cada hash é descartável.")
    print("  - O compromisso em si não é 'moível' sem RETREINAR (o custo dominante permanece útil);")
    print("    o prefixo serve como ajuste fino exponencial por cima — análogo ao difficulty adjustment.")
    print(f"  - Taxa medida: 1 thread, Python puro ({taxa / 1e6:.3f} M hashes/s); uma implementação em C")
    print("    ou GPU moeria ordens de grandeza mais rápido — o k deve ser calibrado contra isso.")
    print()
    print(f"Tempo total do experimento: {time.perf_counter() - T0:.3f} s (incl. import do torch e recomputação do compromisso)")


if __name__ == "__main__":
    main()
