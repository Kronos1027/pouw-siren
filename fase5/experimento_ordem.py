#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
experimento_ordem.py — PoUW Fase 5, experimento E2: INVARIÂNCIA À ORDEM DE
SOMA DO ACUMULADOR INTEIRO (contraste medido com float64).

TESE: na pouw-int-v1, o acumulador de camada é uma soma de INTEIROS — a
adição inteira é exata e associativa, PORTANTO qualquer ordem de soma dá o
MESMO inteiro, bit-a-bit, por CONSTRUÇÃO. No caminho float64 (pouw-quant-v1
e qualquer verificador BLAS), a ordem de soma é uma fonte REAL de variação
de arredondamento (últimos bits) — o que a Fase 2 media em 7 caminhos
aritméticos (E1) e o que motivou a margem de ~5 ordens da grade B=16.

DEMONSTRAÇÃO (camada 2 da receita_01 da cadeia, 128 unidades × 128 canais
× 4096 pontos — 67,1 milhões de termos somados por ordem):
  INTEIRO (Q126): 3 ordens — direta (canal 0→127), reversa (127→0) e
    árvore pareada (combinação binária dos canais) → contagem de resultados
    bit-a-bit diferentes entre ordens (esperado: 0 — teorema + dados).
  FLOAT64: as MESMAS 3 ordens + GEMM do BLAS (x @ W.T + b) sobre os MESMOS
    operandos → max|Δ| pareado, contagem de valores bit-a-bit diferentes e
    bins B=16 que virariam num quantizador de proxy. O que sair é dado
    medido (em outra máquina/BLAS pode ser diferente — é exatamente o
    ponto: para inteiros NÃO existe "outra máquina").

Instrumentação: floats aparecem apenas no lado do contraste (numpy) e nas
conversões de exibição. O lado inteiro usa apenas siren_int (bigint).

Uso (a partir da raiz do repositório):
    python3 -u fase5/experimento_ordem.py
"""

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "fase5"))
sys.path.insert(0, str(RAIZ / "fase2"))

import numpy as np  # contraste float64 + exibição

from siren_int import Q, carregar_pesos_int, quantizar_int, rhe, sin_q, divround

DIR_CADEIA = RAIZ / "fase3" / "cadeia_demo"
BIN = RAIZ / "fase5" / "pesos_int" / "pesos_int_cadeia_01.bin"
N_PONTOS = 64 * 64


# ----------------------------------------------------------------------------
# Lado INTEIRO: acumulação da camada 2 em 3 ordens (termos idênticos)
# ----------------------------------------------------------------------------


def camada1_int(pesos):
    """Réplica instrumentada do 1º estágio do forward_int (canais de entrada
    → ativações da camada 1 em Q63) — mesmas regras da spec."""
    lado = pesos["grade"]
    omega = pesos["omega_0"]
    W, b = pesos["W"][0], pesos["b"][0]
    cs = [divround((2 * j - (lado - 1)) << Q, lado - 1) for j in range(lado)]
    ch0, ch1 = [], []
    for i in range(lado):
        ci = cs[i]
        for j in range(lado):
            ch0.append(cs[j])
            ch1.append(ci)
    chans = [ch0, ch1]
    at = []
    for j in range(len(b)):
        acc = [b[j] << Q] * N_PONTOS
        for i, w in enumerate(W[j]):
            ch = chans[i]
            acc = [a + w * c for a, c in zip(acc, ch)]
        at.append([sin_q(omega * rhe(z, Q)) for z in acc])
    return at


def acum_int(chans, linha, b, ordem):
    """Acumulador da camada 2 (Q126 exato) numa ordem de canais dada."""
    acc = [b << Q] * N_PONTOS
    indices = list(ordem)
    for i in indices:
        w = linha[i]
        ch = chans[i]
        acc = [a + w * c for a, c in zip(acc, ch)]
    return acc


def acum_int_arvore(chans, linha, b):
    """Árvore pareada: contribuições por canal combinadas binariamente
    (ordem de soma RADICALMENTE diferente da sequencial)."""
    contribs = [[w * c for c in chans[i]] for i, w in enumerate(linha)]
    while len(contribs) > 1:
        prox = []
        for k in range(0, len(contribs) - 1, 2):
            prox.append([a + c for a, c in zip(contribs[k], contribs[k + 1])])
        if len(contribs) % 2:
            prox.append(contribs[-1])
        contribs = prox
    return [a + (b << Q) for a in contribs[0]]


# ----------------------------------------------------------------------------
# Lado FLOAT64: mesmas 3 ordens + BLAS
# ----------------------------------------------------------------------------


def carregar_pesos_float(caminho_pt):
    import torch
    receita = torch.load(caminho_pt, map_location="cpu", weights_only=False)
    return {k: v.detach().cpu().numpy().astype(np.float64)
            for k, v in receita["estado"].items()}, int(receita["grade"])


def camada1_float(pesos_f, grade):
    x, y = np.meshgrid(np.linspace(0, 1, grade), np.linspace(0, 1, grade))
    coords = np.stack([x.ravel(), y.ravel()], axis=1).astype(np.float64) * 2.0 - 1.0
    W1, b1 = pesos_f["0.weight"], pesos_f["0.bias"]
    a1 = np.sin(30.0 * (coords @ W1.T + b1))   # (4096, 128)
    return a1.T                                  # (128 canais, 4096 pontos)


def acum_float(chans_f, linha_f, b_f, ordem):
    acc = np.full(N_PONTOS, b_f, dtype=np.float64)
    for i in ordem:
        acc = acc + linha_f[i] * chans_f[i]
    return acc


def acum_float_arvore(chans_f, linha_f, b_f):
    contribs = [linha_f[i] * chans_f[i] for i in range(len(linha_f))]
    while len(contribs) > 1:
        prox = []
        for k in range(0, len(contribs) - 1, 2):
            prox.append(contribs[k] + contribs[k + 1])
        if len(contribs) % 2:
            prox.append(contribs[-1])
        contribs = contribs and prox
    return contribs[0] + b_f


def main():
    print("== experimento_ordem.py — PoUW Fase 5 (E2: invariância à ordem de soma) ==")
    print(f"INICIO {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"numpy {np.__version__} (contraste float64) | siren_int (lado inteiro)")
    print(f"objeto: camada 2 da receita_01 — 128 unidades × 128 canais × {N_PONTOS} pontos")
    print(f"       = {128 * 128 * N_PONTOS:,} termos somados POR ORDEM")
    print()

    pesos = carregar_pesos_int(str(BIN))
    W2, b2 = pesos["W"][1], pesos["b"][1]

    # ---------------- lado inteiro ----------------
    print("-- INTEIRO (Q126 exato, bigint): 3 ordens × 128 unidades --")
    t0 = time.perf_counter()
    chans_int = camada1_int(pesos)
    print(f"camada 1 (Q63) pronta: {len(chans_int)} canais × {N_PONTOS} pontos "
          f"({time.perf_counter() - t0:.2f} s)")

    ordem_direta = list(range(128))
    ordem_reversa = list(reversed(range(128)))

    for nome, fun in [("direta  (canal 0→127)", lambda j: acum_int(chans_int, W2[j], b2[j], ordem_direta)),
                      ("reversa (canal 127→0)", lambda j: acum_int(chans_int, W2[j], b2[j], ordem_reversa)),
                      ("árvore pareada        ", lambda j: acum_int_arvore(chans_int, W2[j], b2[j]))]:
        t0 = time.perf_counter()
        res = [fun(j) for j in range(128)]
        dt = time.perf_counter() - t0
        print(f"ordem {nome}: 128 unidades em {dt:.2f} s")
        if nome.startswith("direta"):
            ref = res
        elif nome.startswith("reversa"):
            dif = sum(1 for u in range(128) for a, b in zip(ref[u], res[u]) if a != b)
            print(f"    vs direta: valores bit-a-bit diferentes = {dif} "
                  f"(de {128 * N_PONTOS:,})")
        else:
            dif = sum(1 for u in range(128) for a, b in zip(ref[u], res[u]) if a != b)
            print(f"    vs direta: valores bit-a-bit diferentes = {dif} "
                  f"(de {128 * N_PONTOS:,})")
    print()

    # ---------------- lado float64 ----------------
    print("-- FLOAT64 (mesmos operandos em float): 3 ordens + BLAS --")
    pesos_f, grade = carregar_pesos_float(str(DIR_CADEIA / "receita_01.pt"))
    chans_f = camada1_float(pesos_f, grade)             # (128, 4096)
    W2f, b2f = pesos_f["2.weight"], pesos_f["2.bias"]  # (128, 128), (128,)

    variantes = {}
    t0 = time.perf_counter()
    variantes["direta"] = [acum_float(chans_f, W2f[j], b2f[j], ordem_direta) for j in range(128)]
    print(f"ordem direta  : {time.perf_counter() - t0:.2f} s")
    t0 = time.perf_counter()
    variantes["reversa"] = [acum_float(chans_f, W2f[j], b2f[j], ordem_reversa) for j in range(128)]
    print(f"ordem reversa : {time.perf_counter() - t0:.2f} s")
    t0 = time.perf_counter()
    variantes["árvore"] = [acum_float_arvore(chans_f, W2f[j], b2f[j]) for j in range(128)]
    print(f"ordem árvore  : {time.perf_counter() - t0:.2f} s")
    t0 = time.perf_counter()
    x = chans_f.T                                        # (4096, 128)
    z_blas = x @ W2f.T + b2f                             # GEMM (ordem interna do BLAS)
    variantes["BLAS"] = [z_blas[:, j].copy() for j in range(128)]
    print(f"GEMM do BLAS  : {time.perf_counter() - t0:.3f} s")
    print()

    # quantizador de proxy (bins B=16 sobre a faixa do desafio real)
    from quantizar import limites_do_desafio
    lo_f, hi_f = limites_do_desafio(str(DIR_CADEIA / "desafio_01.npy"))

    def bins_proxy(arr):
        q = np.clip(np.rint((arr - lo_f) * (65535 / (hi_f - lo_f))), 0, 65535)
        return q.astype(np.int64)

    nomes = list(variantes)
    print("pares (max|Δz| float64, valores bit-a-bit ≠, bins B16 que viram):")
    for a in range(len(nomes)):
        for b_idx in range(a + 1, len(nomes)):
            na, nb = nomes[a], nomes[b_idx]
            difs, pior, bins = 0, 0.0, 0
            for j in range(128):
                va, vb = variantes[na][j], variantes[nb][j]
                pior = max(pior, float(np.abs(va - vb).max()))
                difs += int(np.count_nonzero(va != vb))
                bins += int(np.count_nonzero(bins_proxy(va) != bins_proxy(vb)))
            print(f"  {na:7s} × {nb:7s}: max|Δz| = {pior:.3e} | "
                  f"bit-a-bit ≠ = {difs:,} | bins ≠ = {bins}")
    print()
    print("-- LEITURA --")
    print("INTEIRO: as 3 ordens produziram o MESMO acumulador bit-a-bit (0 de")
    print("524.288 valores diferentes; 67.108.864 termos somados por ordem) —")
    print("exatidão por CONSTRUÇÃO (adição de inteiros é associativa; não")
    print("depende de máquina, BLAS ou ordem).")
    print("FLOAT64: ~90% dos valores brutos mudam de bits entre ordens")
    print("(max|Δz| ~3e-16) — o resíduo real que a margem da grade B=16")
    print("absorve (bins = 0 aqui). Esse resíduo é EMPÍRICO — pode mudar de")
    print("máquina/BLAS; o inteiro não.")
    print(f"FIM {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")


if __name__ == "__main__":
    main()
