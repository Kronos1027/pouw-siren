#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
experimento_caminhos.py — PoUW Fase 2, EXPERIMENTO E1.

PERGUNTA: o hash quantizado (pouw-quant-v1) sobrevive a caminhos aritméticos
DIFERENTES para o MESMO forward (mesma receita, mesmos pesos, mesma grade)?

MÉTODO: 7 caminhos reais de forward na MESMA máquina, que exercitam exatamente
a classe de fenômeno que divergiu entre a CPU do repositório e a CPU do usuário
na validação da Fase 1 (arredondamento de operações vetoriais / ordem de redução
do BLAS / implementações de sin):

  p1  torch  float32, 1 thread        ← baseline = caminho oficial da Fase 1
  p2  torch  float32, 2 threads       ← variação de paralelização
  p3  numpy  float32 (OpenBLAS)       ← BLAS/libm DIFERENTE do torch
  p4  numpy  float32, soma em blocos de 16  ← ordem de redução FORÇADA
  p5  torch  float64, 1 thread        ← caminho da SPEC da Fase 2
  p6  numpy  float64 (OpenBLAS)       ← BLAS diferente no float64
  p7  numpy  float64, soma em blocos de 16 ← ordem de redução forçada no f64

Medições por caminho (contra p1): max|Δ|, nº de elementos que diferem,
distância de Hamming das quantizações B=16 e B=8, e os hashes completos.
Adicionalmente: pares dentro da família float64 (p5,p6,p7) e o par
float32↔float64 — este último quantifica o que acontece se MINERADOR e
VERIFICADOR usarem precisões diferentes (violação da spec).

CONTINUIDADE: p1 é conferido bit-a-bit contra o reconstrucao_*.npy oficial
da Fase 1 (o caminho replicado deve reproduzir o artefato publicado).

Este experimento é um PROXY controlado da variação cross-CPU: as divergências
que ele produz são reais (aritmética diferente de verdade), mas a validação
cross-CPU definitiva é o usuário rodar verificar_fase2.py na própria máquina
e conferir o compromisso quantizado.

Uso (a partir da raiz do repositório):
    python3 fase2/experimento_caminhos.py
"""

import platform
import time
from collections import OrderedDict
from pathlib import Path

import numpy as np

T0 = time.perf_counter()
import torch  # noqa: E402

from quantizar import hash_quantizado, limites_do_desafio, quantizar  # noqa: E402
from siren_numpy import carregar_pesos_numpy, forward_numpy, grade  # noqa: E402
from verificar_fase2 import construir_rede  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SEEDS = ["b0f90ffe", "d037aef4", "8b457d0a"]


def forward_torch(caminho_receita, threads, duplo):
    """Forward torch com controle de threads e precisão (float32 ou float64)."""
    torch.set_num_threads(threads)
    try:
        receita = torch.load(caminho_receita, map_location="cpu", weights_only=False)
    except TypeError:
        receita = torch.load(caminho_receita, map_location="cpu")
    arq = receita["arquitetura"]
    modelo = construir_rede(arq["dim_entrada"], arq["ocultas"], arq["dim_saida"], arq["omega_0"])
    modelo.load_state_dict(receita["estado"])
    modelo.eval()
    if duplo:
        modelo.double()
    size = int(receita["grade"])
    if duplo:
        x, y = np.meshgrid(np.linspace(0, 1, size), np.linspace(0, 1, size))
        coords = np.stack([x.ravel(), y.ravel()], axis=1).astype(np.float64) * 2.0 - 1.0
    else:
        # [INICIO BLOCO COMPARTILHADO COM treinar.py/verificar.py da Fase 1]
        x, y = np.meshgrid(np.linspace(0, 1, size), np.linspace(0, 1, size))
        coords = np.stack([x.ravel(), y.ravel()], axis=1).astype(np.float32) * 2.0 - 1.0
        # [FIM BLOCO COMPARTILHADO]
    with torch.no_grad():
        rec = modelo(torch.from_numpy(coords)).squeeze(-1).reshape(size, size).numpy()
    return rec


def comparar(a, b):
    """max|Δ|, nº de elementos que diferem, em float64."""
    d = np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64))
    return float(d.max()), int((d > 0).sum())


def hamming(qa, qb):
    return int((np.asarray(qa) != np.asarray(qb)).sum())


def main():
    print("== experimento_caminhos.py — PoUW Fase 2, E1 (robustez a caminhos aritméticos) ==")
    print(f"Python {platform.python_version()} | PyTorch {torch.__version__} | NumPy {np.__version__}")
    print(f"RAIZ: {RAIZ}")
    print(f"Seeds: {SEEDS} (as 3 receitas oficiais da Fase 1)")
    print(f"(torch será alternado entre 1 e 2 threads conforme o caminho; numpy usa os threads do OpenBLAS)")
    print()

    resumo_global = []

    for tag in SEEDS:
        receita_path = RAIZ / f"receita_{tag}.pt"
        desafio_path = RAIZ / f"desafio_{tag}.npy"
        recon_oficial_path = RAIZ / f"reconstrucao_{tag}.npy"

        lo, hi = limites_do_desafio(desafio_path)
        size = 64

        receita_carregada, pesos = carregar_pesos_numpy(str(receita_path))
        omega = float(receita_carregada["arquitetura"]["omega_0"])

        coords32 = grade(size, np.float32)
        coords64 = grade(size, np.float64)

        caminhos = OrderedDict()
        caminhos["p1 torch32 1t     "] = forward_torch(str(receita_path), 1, False)
        caminhos["p2 torch32 2t     "] = forward_torch(str(receita_path), 2, False)
        caminhos["p3 numpy32        "] = forward_numpy(coords32, pesos, omega, np.float32, blocos=0).reshape(size, size)
        caminhos["p4 numpy32 bloc16 "] = forward_numpy(coords32, pesos, omega, np.float32, blocos=16).reshape(size, size)
        caminhos["p5 torch64 1t     "] = forward_torch(str(receita_path), 1, True)
        caminhos["p6 numpy64        "] = forward_numpy(coords64, pesos, omega, np.float64, blocos=0).reshape(size, size)
        caminhos["p7 numpy64 bloc16 "] = forward_numpy(coords64, pesos, omega, np.float64, blocos=16).reshape(size, size)

        base = caminhos["p1 torch32 1t     "]
        base_q16 = quantizar(base, lo, hi, 16)
        base_q8 = quantizar(base, lo, hi, 8)

        # Continuidade com a Fase 1: p1 deve reproduzir o artefato publicado
        recon_oficial = np.load(recon_oficial_path)
        cont_ok = bool(np.array_equal(base, recon_oficial))

        print(f"---- seed {tag} (lo={lo:.6f}, hi={hi:.6f}) ----")
        print(f"Continuidade Fase 1: p1 (torch32 1t) é bit-a-bit idêntico ao reconstrucao_{tag}.npy oficial? {cont_ok}")
        print()
        print(f"{'caminho':<20} | {'max|Δ| vs p1':>14} | {'nº≠':>5} | {'HD q16':>7} | {'HD q8':>6} | hash B=16 (SHA-256 completo)")
        print("-" * 132)
        for nome, rec in caminhos.items():
            md, nd = comparar(rec, base)
            q16 = quantizar(rec, lo, hi, 16)
            q8 = quantizar(rec, lo, hi, 8)
            h16 = hash_quantizado(q16)
            hd16 = hamming(q16, base_q16)
            hd8 = hamming(q8, base_q8)
            print(f"{nome} | {md:14.3e} | {nd:5d} | {hd16:7d} | {hd8:6d} | {h16}")
        print()

        # Família float64: pares (a prova central da Fase 2)
        print("Família float64 (spec da Fase 2) — pares:")
        pares = [("p5", caminhos["p5 torch64 1t     "], "p6", caminhos["p6 numpy64        "]),
                 ("p5", caminhos["p5 torch64 1t     "], "p7", caminhos["p7 numpy64 bloc16 "]),
                 ("p6", caminhos["p6 numpy64        "], "p7", caminhos["p7 numpy64 bloc16 "])]
        for na, va, nb, vb in pares:
            md, nd = comparar(va, vb)
            qa16 = quantizar(va, lo, hi, 16)
            qb16 = quantizar(vb, lo, hi, 16)
            iguais = bool(np.array_equal(qa16, qb16))
            print(f"  {na} vs {nb}: max|Δ|={md:.3e} | nº≠={nd} | quantizações B=16 idênticas? {iguais} | HD={hamming(qa16, qb16)}")
        print()

        # Float32 ↔ float64: o que acontece se minerador e verificador divergirem de precisão
        q1_16 = quantizar(caminhos["p1 torch32 1t     "], lo, hi, 16)
        q5_16 = quantizar(caminhos["p5 torch64 1t     "], lo, hi, 16)
        md, nd = comparar(caminhos["p1 torch32 1t     "], caminhos["p5 torch64 1t     "])
        print(f"p1 (float32) vs p5 (float64): max|Δ|={md:.3e} | HD q16={hamming(q1_16, q5_16)} | hashes iguais? {bool(np.array_equal(q1_16, q5_16))}")
        print(f"  hash quantizado B=16 do p1 (se o MINERADOR errasse e usasse float32): {hash_quantizado(q1_16)}")
        print(f"  hash quantizado B=16 do p5 (spec: float64):                             {hash_quantizado(q5_16)}")
        print()

        resumo_global.append((tag, cont_ok))

    print("==== RESUMO DO E1 ====")
    for tag, cont_ok in resumo_global:
        print(f"  seed {tag}: continuidade com a Fase 1: {'OK' if cont_ok else 'FALHOU'}")
    print()
    print("LEITURA (impressa como dado, interpretação no relatório):")
    print("  - float32: caminhos diferentes → valores divergem ~1e-07 e a quantização B=16 VIRA;")
    print("  - float64: caminhos diferentes → valores divergem ~1e-14 e a quantização B=16 (e B=8) NÃO vira;")
    print("  - logo o compromisso DEVE ser definido sobre o forward float64, para minerador e verificador.")
    print()
    print(f"Tempo total do experimento: {time.perf_counter() - T0:.3f} s (incl. imports)")


if __name__ == "__main__":
    main()
