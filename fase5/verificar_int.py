#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_int.py — PoUW Fase 5: VERIFICADOR FRIO 100% INTEIRO (pouw-int-v1).

Verificador independente do minerador: lê APENAS artefatos publicados
(pesos inteiros .bin + desafio .npy) e executa o caminho completo da
pouw-int-v1 SEM NENHUMA operação de ponto flutuante:

  forward inteiro Q63 → quantização inteira exata → hash de compromisso
  → gate de qualidade como desigualdade inteira exata.

PROVA DE AUSÊNCIA DE FLOATS (auditoria em runtime):
  - o processo importa SOMENTE stdlib sem floats: argparse, ast, hashlib,
    os, sys, time (e siren_int.py, que importa os mesmos); pathlib,
    datetime e platform foram excluídos DE PROPÓSITO — cada um deles puxa
    math em alguma versão do Python, e a auditoria zero-float detectou os
    três em runtime: pathlib (F5, log f5_verificar_int_frio_bloco1.txt),
    datetime (Python <= 3.11, "import math as _math" em Lib/datetime.py —
    pegou na máquina Windows do dono, 3.11.15) e platform (Python 3.10,
    via subprocess → selectors, que usava math.ceil — ver
    fase5/logs/etapa15_correcao_portabilidade.md);
  - a auditoria confere em sys.modules que math/cmath/numpy/torch/scipy/
    decimal/fractions/statistics/random NUNCA foram carregados;
  - até a MEDIÇÃO DE TEMPO é inteira: time.perf_counter_ns (nanossegundos),
    sem nunca materializar um float; decimais são formatados por divmod.

Portabilidade: lê int64 little-endian EXPLÍCITO (.bin) e .npy com descr
little-endian — independente da endianness da máquina. Não precisa de
numpy, torch, BLAS, libm nem FPU. Requisito declarado da spec: alvo de
PSNR múltiplo de 5 dB (r=0 exato; r=5 por raiz quadrada inteira).

Checagens (todas opcionais via flags; código de saída 0 = VÁLIDO):
  H1  sha256(pesos.bin) == --sha256-pesos (se dado)
  H2  sha256(desafio.npy) == --sha256-desafio (se dado)
  C1  compromisso pouw-int-v1 recomputado == --comp-esperado (se dado)
  C2  gate: S·10^t <= N·alcance² (alvo --alvo-psnr; default 40)
  C3  --quantizada <npy>: array v2 == array v1 publicado (bins divergentes)

Uso (a partir da raiz do repositório):
    python3 fase5/verificar_int.py <pesos_int.bin> <desafio.npy>
        [--comp-esperado <hex64>] [--alvo-psnr 40]
        [--sha256-pesos <hex64>] [--sha256-desafio <hex64>]
        [--quantizada <arquivo.npy>] [--sem-gate]
"""

import argparse
import hashlib
import os
import sys
import time

# NOTA: pathlib NÃO é importado de propósito — ele puxa math (auditoria
# zero-float pegou a infiltracão em runtime; ver log f5_verificar_int_frio_bloco1.txt)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from siren_int import (  # noqa: E402  (mesmos imports puros do módulo da spec)
    VERSAO_SPEC, auditar_sem_float, carregar_pesos_int, forward_int,
    gate_mse_int, hash_quantizado_int, limites_e_referencia_int,
    ler_quantizada_u16, quantizar_int,
)


def agora_utc():
    # v1.0.1: time em vez de datetime — em Python <= 3.11, 'import datetime'
    # executa 'import math as _math' (Lib/datetime.py) e infiltrava math no
    # processo, derrubando a auditoria zero-float (falhou assim no Windows do
    # dono, Python 3.11.15, e na matriz local 3.10/3.11). O módulo time não
    # carrega math em NENHUMA versão do Python. Formato de saída IDÊNTICO ao
    # anterior ("YYYY-MM-DD HH:MM:SS UTC"); compromissos NÃO são afetados.
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def fmt_ns(ns):
    """Nanossegundos → 'SS.ffffff' SEM floats (divmod em inteiros)."""
    s, resto = divmod(ns, 1_000_000_000)
    return f"{s}.{resto // 1_000_000:06d}"


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(
        description="Verificador frio 100% inteiro — PoUW Fase 5 (pouw-int-v1)")
    ap.add_argument("pesos", help="arquivo .bin de pesos inteiros canônicos Q63")
    ap.add_argument("desafio", help="arquivo .npy do desafio (float64)")
    ap.add_argument("--comp-esperado", default=None,
                    help="compromisso pouw-int-v1 esperado (hex 64)")
    ap.add_argument("--alvo-psnr", type=int, default=40,
                    help="alvo do gate em dB (múltiplo de 5; default 40; INT de propósito)")
    ap.add_argument("--sha256-pesos", default=None, help="sha256 esperado do .bin")
    ap.add_argument("--sha256-desafio", default=None, help="sha256 esperado do .npy")
    ap.add_argument("--quantizada", default=None,
                    help=".npy uint16 publicado (v1) para comparação de payload")
    ap.add_argument("--sem-gate", action="store_true", help="desativa o gate (só compromisso)")
    args = ap.parse_args()

    print("== verificar_int.py — PoUW Fase 5 (verificador frio 100% inteiro, "
          f"{VERSAO_SPEC}) ==")
    print(f"INICIO {agora_utc()}")
    # v1.0.1: sys.version em vez de platform.python_version() — no Python
    # 3.10, 'import platform' puxa subprocess → selectors → math e derruba
    # a auditoria zero-float (detectado na matriz local 3.10). Saída
    # IDÊNTICA: sys.version.split()[0] == platform.python_version().
    print(f"Python {sys.version.split()[0]} | byteorder da máquina: {sys.byteorder} "
          "(leituras são little-endian EXPLÍCITAS — portável)")
    print()
    print("-- AUDITORIA ZERO-FLOAT (runtime) --")
    presentes = auditar_sem_float()
    if presentes:
        print(f"FALHOU: módulos de float carregados no processo: {presentes}")
        raise SystemExit(1)
    print("OK: math/cmath/numpy/torch/scipy/decimal/fractions/statistics/random "
          "AUSENTES de sys.modules")
    print("Imports do processo: apenas argparse/ast/hashlib/os/sys/time "
          "+ siren_int (idem; datetime e platform removidos na v1.0.1 — "
          "puxavam math em Python <=3.11 e =3.10)")
    print("Tempos medidos em NANOSSEGUNDOS inteiros (perf_counter_ns) — nenhum float "
          "é materializado neste processo")

    valido = True

    # ---------- H1/H2: âncoras de bytes ----------
    print()
    print("-- Âncoras de bytes (SHA-256) --")
    sha_pesos = sha256_arquivo(args.pesos)
    ok_h1 = args.sha256_pesos is None or sha_pesos == args.sha256_pesos
    print(f"H1 sha256(pesos)  = {sha_pesos}"
          + (f" {'OK' if ok_h1 else 'DIVERGE'}" if args.sha256_pesos else ""))
    valido = valido and ok_h1
    sha_desafio = sha256_arquivo(args.desafio)
    ok_h2 = args.sha256_desafio is None or sha_desafio == args.sha256_desafio
    print(f"H2 sha256(desafio)= {sha_desafio}"
          + (f" {'OK' if ok_h2 else 'DIVERGE'}" if args.sha256_desafio else ""))
    valido = valido and ok_h2

    # ---------- verificação (região medida; sem prints no meio) ----------
    t_carga_0 = time.perf_counter_ns()
    pesos = carregar_pesos_int(args.pesos)
    t_fwd_0 = time.perf_counter_ns()
    r_q63 = forward_int(pesos)
    t_lim_0 = time.perf_counter_ns()
    lo, hi, ref, shape = limites_e_referencia_int(args.desafio)
    t_quant_0 = time.perf_counter_ns()
    qs = quantizar_int(r_q63, lo, hi)
    comp = hash_quantizado_int(qs, shape[0], shape[1])
    t_gate_0 = time.perf_counter_ns()
    aprovado, esq, lim = gate_mse_int(r_q63, ref, lo, hi, args.alvo_psnr)
    t_fim = time.perf_counter_ns()

    # ---------- saída ----------
    print()
    print(f"Pesos : {args.pesos}")
    print(f"        camadas={pesos['camadas']} omega_0={pesos['omega_0']} "
          f"grade={pesos['grade']} ({pesos['grade'] ** 2} pontos)")
    print(f"Desafio: {args.desafio} | shape {shape[0]}x{shape[1]} | "
          f"lo/hi em Q63 por seleção de bits")
    print()
    print("-- Tempos (perf_counter_ns, inteiros) --")
    print(f"carga pesos .bin : {fmt_ns(t_fwd_0 - t_carga_0)} s")
    print(f"forward inteiro  : {fmt_ns(t_lim_0 - t_fwd_0)} s")
    print(f"limites+ref bits : {fmt_ns(t_quant_0 - t_lim_0)} s")
    print(f"quantização+hash : {fmt_ns(t_gate_0 - t_quant_0)} s")
    print(f"gate exato       : {fmt_ns(t_fim - t_gate_0)} s")
    print(f"TOTAL (carga → gate): {fmt_ns(t_fim - t_carga_0)} s")
    print()
    print(f"COMPROMISSO {VERSAO_SPEC}|B=16|{shape[0]}x{shape[1]}|: {comp}")
    if args.comp_esperado:
        ok_c1 = comp == args.comp_esperado
        print(f"C1 vs esperado   : {args.comp_esperado} → {'CONFERE' if ok_c1 else 'DIVERGE'}")
        valido = valido and ok_c1

    if args.sem_gate:
        print("C2 gate: DESATIVADO (--sem-gate)")
    else:
        razao_centi = (lim * 100) // esq if esq else None
        margem = f"{razao_centi // 100},{razao_centi % 100:02d}×" if razao_centi else "∞"
        r5 = args.alvo_psnr % 10
        rotulo = (f"S·10^{args.alvo_psnr // 10}" if r5 == 0
                  else f"S·T({args.alvo_psnr}dB)")
        print(f"C2 gate (inteiro exato, alvo {args.alvo_psnr} dB): {rotulo} = {esq}")
        if r5:
            print(f"   [T = 10^(alvo/10) em Q63 por raiz quadrada inteira exata "
                  f"(Newton); erro ≤ 2^-64 relativo]")
        print(f"   limite {'N·alcance²' if r5 == 0 else 'N·alcance²·2^63':<14}      = {lim}")
        print(f"   → {'APROVADO' if aprovado else 'REPROVADO'} "
              f"(margem ≈ {margem}, razão exata em inteiros)")
        valido = valido and aprovado

    if args.quantizada:
        q_pub, shape_pub = ler_quantizada_u16(args.quantizada)
        if tuple(shape_pub) != tuple(shape):
            print(f"C3 quantizada publicada: shape {shape_pub} != {shape} — DIVERGE")
            valido = False
        else:
            difs = sum(1 for a, b in zip(q_pub, qs) if a != b)
            print(f"C3 payload vs quantizada publicada ({args.quantizada}): "
                  f"{difs}/{len(qs)} bins divergentes → "
                  f"{'PAYLOAD IDÊNTICO ao v1' if difs == 0 else 'DIVERGE'}")
            valido = valido and difs == 0

    print()
    print(f"RESULTADO: {'VÁLIDO (código 0)' if valido else 'INVÁLIDO (código 1)'}")
    print(f"FIM {agora_utc()}")
    raise SystemExit(0 if valido else 1)


if __name__ == "__main__":
    main()
