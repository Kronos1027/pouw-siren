#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
experimento_equivalencia.py — PoUW Fase 5, experimentos E3 (equivalência
v1×v2) e E5 (custo), +Demonstração oficial das 8 execuções frias.

E3 — Para cada uma das 18 receitas oficiais (8 blocos da cadeia F3 +
4 receitas F1 + 6 receitas F2 de dificuldade escalonada):
  v1 (float64 + BLAS + libm, verificar_fase2.forward_torch64):
    forward → quantização pouw-quant-v1 → compromisso v1 → PSNR → gate
  v2 (100% inteiros, siren_int sobre pesos_int .bin):
    forward → quantização pouw-int-v1 → compromisso v2 → gate exato
  Medidas por receita: bins B16 divergentes v1×v2, max|ΔR| em unidades do
  sinal, vereditos dos gates (alvo da própria receita; F2 usa 40–65 dB),
  compromisso v2 (16 hex), tempos v1 e v2.

E5 — Custos agregados: tempo médio/total por lado, razão v2/v1.

DEMONSTRAÇÃO OFICIAL ZERO-FLOAT — as 8 verificações FRIO da cadeia via
subprocesso verificar_int.py com âncoras completas (--sha256-pesos,
--sha256-desafio, --comp-esperado v2, --quantizada publicada v1): prova
que um processo SEM NENHUMA operação de float reproduz o payload publicado
pelo caminho BLAS/libm, bloco a bloco.

Uso (a partir da raiz do repositório; ~12 min):
    python3 -u fase5/experimento_equivalencia.py
"""

import hashlib
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "fase2"))
sys.path.insert(0, str(RAIZ / "fase5"))

import numpy as np
import torch

from siren_int import (  # noqa: E402
    UM, carregar_pesos_int, forward_int, gate_mse_int, hash_quantizado_int,
    limites_e_referencia_int, quantizar_int,
)
from quantizar import hash_quantizado, limites_do_desafio, psnr_db, quantizar  # noqa: E402
from verificar_fase2 import forward_torch64  # noqa: E402

torch.set_num_threads(1)

DIR_PESOS = RAIZ / "fase5" / "pesos_int"
VERIFICADOR = RAIZ / "fase5" / "verificar_int.py"

# (tag, receita .pt, pesos .bin, desafio .npy, alvo do gate)
RECEITAS = [
    (f"cadeia_{i:02d}", RAIZ / f"fase3/cadeia_demo/receita_{i:02d}.pt",
     DIR_PESOS / f"pesos_int_cadeia_{i:02d}.bin",
     RAIZ / f"fase3/cadeia_demo/desafio_{i:02d}.npy", 40)
    for i in range(1, 9)
] + [
    ("f1_8b457d0a", RAIZ / "receita_8b457d0a.pt", DIR_PESOS / "pesos_int_f1_8b457d0a.bin",
     RAIZ / "desafio_8b457d0a.npy", 40),
    ("f1_b0f90ffe", RAIZ / "receita_b0f90ffe.pt", DIR_PESOS / "pesos_int_f1_b0f90ffe.bin",
     RAIZ / "desafio_b0f90ffe.npy", 40),
    ("f1_d037aef4", RAIZ / "receita_d037aef4.pt", DIR_PESOS / "pesos_int_f1_d037aef4.bin",
     RAIZ / "desafio_d037aef4.npy", 40),
    ("f1_extra60db", RAIZ / "receita_extra_60db_b0f90ffe.pt",
     DIR_PESOS / "pesos_int_f1_extra60db.bin", RAIZ / "desafio_b0f90ffe.npy", 40),
] + [
    (f"f2_alvo{a}db", RAIZ / f"fase2/receita_alvo{a}db_b0f90ffe.pt",
     DIR_PESOS / f"pesos_int_f2_alvo{a}db.bin", RAIZ / "desafio_b0f90ffe.npy", a)
    for a in (40, 45, 50, 55, 60, 65)
]


def agora():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def sha256_arq(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def main():
    print("== experimento_equivalencia.py — PoUW Fase 5 (E3 equivalência + E5 custos) ==")
    print(f"INICIO {agora()}")
    print(f"Python {sys.version.split()[0]} | torch {torch.__version__} | numpy {np.__version__}")
    print(f"v1 = float64 + BLAS + libm (torch, 1 thread) | v2 = inteiros Q63 (siren_int)")
    print(f"receitas: {len(RECEITAS)} (8 cadeia + 4 F1 + 6 F2)")
    print()

    linhas = []
    t_v1_total = t_v2_total = 0.0
    payloads_identicos = 0
    gates_concordam = 0

    print(f"{'tag':<14} | {'PSNR v1':>8} | {'gate v1':>8} | {'gate v2':>8} | "
          f"{'bins≠':>6} | {'max|ΔR|':>9} | {'payload':>7} | {'comp v2 (16 hex)':>17} | "
          f"{'t v1 (s)':>8} | {'t v2 (s)':>8}")
    for tag, pt, binp, desafio, alvo in RECEITAS:
        # ---------- lado v1 (float64) ----------
        t0 = time.perf_counter()
        rec64, _receita, _n = forward_torch64(str(pt), threads=1)
        t_v1 = time.perf_counter() - t0
        lo_f, hi_f = limites_do_desafio(str(desafio))
        q_v1 = quantizar(rec64, lo_f, hi_f, 16)
        comp_v1 = hash_quantizado(q_v1)
        campo = np.load(str(desafio))
        psnr_v1 = psnr_db(campo, rec64)
        gate_v1 = psnr_v1 >= alvo

        # ---------- lado v2 (inteiros) ----------
        t0 = time.perf_counter()
        pesos = carregar_pesos_int(str(binp))
        r_int = forward_int(pesos)
        t_v2 = time.perf_counter() - t0
        lo_i, hi_i, ref_i, shape = limites_e_referencia_int(str(desafio))
        q_v2 = quantizar_int(r_int, lo_i, hi_i)
        comp_v2 = hash_quantizado_int(q_v2, shape[0], shape[1])
        gate_v2, _esq, _lim = gate_mse_int(r_int, ref_i, lo_i, hi_i, alvo)

        # ---------- comparações ----------
        q_v1_flat = np.asarray(q_v1).ravel().tolist()
        bins = sum(1 for a, b in zip(q_v1_flat, q_v2) if a != b)
        delta = max(abs(r / UM - f) for r, f in zip(r_int, rec64.ravel().tolist()))
        ident = bins == 0
        conc = gate_v1 == gate_v2

        t_v1_total += t_v1
        t_v2_total += t_v2
        payloads_identicos += ident
        gates_concordam += conc
        linhas.append((tag, psnr_v1, gate_v1, gate_v2, bins, delta, ident,
                       comp_v2, t_v1, t_v2, comp_v1))
        print(f"{tag:<14} | {psnr_v1:8.4f} | {'APROV' if gate_v1 else 'REPRO':>8} | "
              f"{'APROV' if gate_v2 else 'REPRO':>8} | {bins:6d} | {delta:9.2e} | "
              f"{'=' if ident else 'DIFERE':>7} | {comp_v2[:16]}… | "
              f"{t_v1:8.4f} | {t_v2:8.2f}", flush=True)
        print(f"               comp v1: {comp_v1}", flush=True)

    print()
    print("-- RESUMO E3 --")
    print(f"receitas: {len(RECEITAS)} | payloads quantizados v1≡v2 bit-a-bit: "
          f"{payloads_identicos}/{len(RECEITAS)} | gates concordantes: "
          f"{gates_concordam}/{len(RECEITAS)}")
    bins_total = sum(l[4] for l in linhas)
    delta_max_geral = max(l[5] for l in linhas)
    print(f"bins divergentes no total: {bins_total} (de {len(RECEITAS) * 4096}) | "
          f"max|ΔR| global: {delta_max_geral:.3e} (passo B=16 ≈ 1,5e-4…1,6e-4)")
    print()
    print("-- RESUMO E5 (custos) --")
    print(f"forward v1 (float64/BLAS): média {t_v1_total / len(RECEITAS):.4f} s | "
          f"total {t_v1_total:.3f} s")
    print(f"forward v2 (bigint Q63)  : média {t_v2_total / len(RECEITAS):.2f} s | "
          f"total {t_v2_total:.1f} s")
    print(f"razão v2/v1: {t_v2_total / t_v1_total:.0f}× (custo da exatidão por "
          f"construção em Python puro; ver limitações do relatório)")
    print()

    # ---------- demonstração oficial: 8 verificações frias zero-float ----------
    print("-- DEMONSTRAÇÃO OFICIAL: 8 verificações FRIO do verificar_int.py --")
    print("(subprocessos próprios; âncoras completas; auditoria zero-float em cada um)")
    frios_ok = 0
    for i in range(1, 9):
        binp = DIR_PESOS / f"pesos_int_cadeia_{i:02d}.bin"
        desafio = RAIZ / f"fase3/cadeia_demo/desafio_{i:02d}.npy"
        quant = RAIZ / f"fase3/cadeia_demo/quantizada_{i:02d}_u16.npy"
        comp_esperado = next(l[7] for l in linhas if l[0] == f"cadeia_{i:02d}")
        cmd = [sys.executable, "-u", str(VERIFICADOR), str(binp), str(desafio),
               "--comp-esperado", comp_esperado,
               "--sha256-pesos", sha256_arq(binp),
               "--sha256-desafio", sha256_arq(desafio),
               "--quantizada", str(quant)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        saida = (p.stdout + p.stderr).strip()
        # extrai as linhas essenciais para o log principal
        essenciais = [ln for ln in saida.splitlines()
                      if ("AUDITORIA" in ln or "AUSENTES" in ln
                          or "COMPROMISSO pouw-int-v1" in ln
                          or "CONFERE" in ln or "payload" in ln.lower() and "bins" in ln
                          or "RESULTADO" in ln or "TOTAL (carga" in ln)]
        print(f"[bloco {i}] código {p.returncode}")
        for ln in essenciais:
            print(f"    {ln}")
        if p.returncode == 0:
            frios_ok += 1
        else:
            print(saida)   # saída integral em caso de falha
    print(f"verificações frias VÁLIDAS: {frios_ok}/8")
    print()

    tudo_ok = (payloads_identicos == len(RECEITAS) and gates_concordam == len(RECEITAS)
               and frios_ok == 8)
    print("-- VEREDICTO --")
    print(f"E3: {payloads_identicos}/18 payloads idênticos, {gates_concordam}/18 gates "
          f"concordantes; E5: razão {t_v2_total / t_v1_total:.0f}×; "
          f"frios: {frios_ok}/8 VÁLIDOS")
    print(f"RESULTADO: {'EQUIVALÊNCIA CONFIRMADA (código 0)' if tudo_ok else 'VER DIVERGÊNCIAS (código 1)'}")
    print(f"FIM {agora()}")
    raise SystemExit(0 if tudo_ok else 1)


if __name__ == "__main__":
    main()
