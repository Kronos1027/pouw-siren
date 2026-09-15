#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smoke_int.py — PoUW Fase 5: bateria de smoke tests da pouw-int-v1
(siren_int.py) ANTES de qualquer execução oficial.

IMPORTANTE (protocolo): este script USA numpy/torch como INSTRUMENTO DE
MEDIDA (referência para comparar a saída do caminho inteiro). O caminho da
spec (siren_int.py) permanece 100% inteiro — a prova de ausência de floats
em processo próprio/frio é feita por verificar_int.py.

Bateria:
  S1  unitário: rhe/divround (half-even, negativos, empates) vs np.rint
  S2  literal de π PINADO conferido por fórmula de Machin em bigint
      (ninguém precisa confiar no literal — ele é verificável)
  S3  sin_q exato nos múltiplos inteiros de π/2 (k·C → 0/±1 EXATOS)
  S4  sin_q vs numpy.sin em grades diádicas exatas (3 granularidades,
      ~100k pontos; mesmo valor real dos dois lados)
  S5  quantizador inteiro: paridade de empates com np.rint (sintético) e
      equivalência com a pouw-quant-v1 no dado REAL do bloco 1
  S6  forward inteiro do bloco 1 vs forward float64 (verificar_fase2):
      max|Δ|, bins divergentes, compromissos v1×v2, gate, tempos
  S7  re-export determinístico do .bin (bytes idênticos)

Uso (a partir da raiz do repositório):
    python3 -u fase5/smoke_int.py
"""

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))            # desafio.py (F1)
sys.path.insert(0, str(RAIZ / "fase2"))  # quantizar.py, verificar_fase2.py (F2)
sys.path.insert(0, str(RAIZ / "fase5"))  # siren_int.py (F5)

import numpy as np  # instrumento de medida (referência)

from siren_int import (  # caminho da spec — zero floats
    C_MEIO_PI, PI_DEC, Q, UM, divround, forward_int, f64_bits_para_q63,
    hash_quantizado_int, limites_e_referencia_int, quantizar_int, rhe, sin_q,
)

FALHAS = []


def checar(nome, cond, detalhe=""):
    status = "OK" if cond else "FALHOU"
    print(f"  [{status}] {nome}" + (f" — {detalhe}" if detalhe else ""))
    if not cond:
        FALHAS.append(nome)
    return cond


# ----------------------------------------------------------------------------
print("== smoke_int.py — PoUW Fase 5 (bateria de smoke da pouw-int-v1) ==")
print(f"INICIO {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
print(f"Instrumento de medida: numpy {np.__version__} (fora do caminho da spec)")
print()

# ---------------- S1: arredondamentos pinados ----------------
print("-- S1: rhe/divround (half-even, negativos, empates) --")
casos_rhe = [(3, 1, 2), (1, 1, 0), (5, 1, 2), (-3, 1, -2), (-1, 1, 0), (-5, 1, -2),
             (7, 2, 2), (6, 2, 2), (-7, 2, -2)]
ok = all(rhe(x, k) == esp for x, k, esp in casos_rhe)
refs = [np.rint(x / 2 ** k) for x, k, _ in casos_rhe]
checar("rhe == np.rint nos 9 casos (incl. empates negativos)",
       ok and all(int(r) == esp for r, (_, _, esp) in zip(refs, casos_rhe)),
       f"rhe(3,1)={rhe(3, 1)} rhe(-3,1)={rhe(-3, 1)} rhe(-1,1)={rhe(-1, 1)}")
casos_div = [(3, 2, 2), (1, 2, 0), (5, 2, 2), (-3, 2, -2), (-1, 2, 0), (-5, 2, -2)]
ok = all(divround(a, b) == esp for a, b, esp in casos_div)
checar("divround == round-half-even da divisão inteira (6 casos)", ok,
       f"divround(-3,2)={divround(-3, 2)} divround(-1,2)={divround(-1, 2)}")
print()

# ---------------- S2: literal de π por Machin (bigint) ----------------
print("-- S2: literal de π pinado, conferido por Machin em inteiros --")


def _arctan_inv(x, escala):
    """arctan(1/x)·escala por série em inteiros (Machin)."""
    total, n, p, sinal = 0, 0, x, 1
    while True:
        termo = escala // ((2 * n + 1) * p)
        if termo == 0:
            return total
        total += sinal * termo
        sinal, n, p = -sinal, n + 1, p * x * x


ESCALA = 10 ** 60
pi_machin = 16 * _arctan_inv(5, ESCALA) - 4 * _arctan_inv(239, ESCALA)
digitos_machin = str(pi_machin)                      # π·10^60 truncado
digitos_literal = PI_DEC.replace(".", "")            # "3" + 50 decimais = 51 chars
# NOTA: a 1ª execução comparou machin[:50] (50 chars) com o literal de 51
# chars — off-by-one NO TESTE, não no literal; corrigido abaixo.
checar(f"primeiros {len(digitos_literal)} dígitos do literal == Machin bigint",
       digitos_machin[:len(digitos_literal)] == digitos_literal,
       f"machin[:56]={digitos_machin[:56]}…")
print()

# ---------------- S3: sin_q exato em k·π/2 ----------------
print("-- S3: sin_q nos múltiplos de π/2 (k·C_MEIO_PI) --")
ok = True
for k in range(-40, 41):
    a = k * C_MEIO_PI
    obtido = sin_q(a)
    if k % 2 == 0:
        esperado = 0
    else:
        esperado = UM if k % 4 == 1 else -UM
    if obtido != esperado:
        ok = False
        print(f"    k={k}: obtido {obtido}, esperado {esperado}")
checar("sin_q(k·C) == 0/±1 EXATOS para k em [-40, 40]", ok)
print()

# ---------------- S4: sin_q vs numpy.sin em grades exatas ----------------
print("-- S4: sin_q vs numpy.sin (grades diádicas exatas, mesmo valor real) --")


def grade_erro(expoente, m_max, passo):
    """a_q = m·2^expoente; val = m·2^(expoente-63) exato em float64."""
    pior = 0.0
    pior_val = 0.0
    for m in range(-m_max, m_max + 1, passo):
        if m == 0:
            continue
        a_q = m << expoente
        val = float(m) * (2.0 ** (expoente - 63))   # exato (m < 2^52)
        ref = float(np.sin(val))
        obt = sin_q(a_q) / UM
        e = abs(obt - ref)
        if e > pior:
            pior, pior_val = e, val
    return pior, pior_val


t_ini = time.perf_counter()
pior_grosso, val_grosso = grade_erro(20, 1 << 49, 1 << 34)   # |a| ≤ 64, grosso
pior_fino, val_fino = grade_erro(44, 1 << 19, 17)            # |a| ≤ 1,95, fino
pior_zero, _ = grade_erro(0, 1 << 11, 3)                     # |a| ≤ 2^-52
t_sen = time.perf_counter() - t_ini
n_pts = 2 * ((1 << 49) // (1 << 34)) + 2 * ((1 << 19) // 17) + 2 * ((1 << 11) // 3)
print(f"    pontos testados: ~{n_pts} | tempo: {t_sen:.3f} s")
print(f"    pior |a|≤64  : {pior_grosso:.3e} (em a={val_grosso:.6f})")
print(f"    pior |a|≤1,95: {pior_fino:.3e} (em a={val_fino:.6f})")
print(f"    perto de 0   : {pior_zero:.3e}")
checar("sin_q ≤ 1 ulp prático em faixa reduzida (|a|≤2: < 4e-16)", pior_fino < 4e-16)
checar("sin_q com redução correta em |a|≤64 (< 1e-14)", pior_grosso < 1e-14)
print()

# ---------------- S5: quantizador inteiro ----------------
print("-- S5: quantizador inteiro (empates + equivalência no dado real) --")
# S5a: empates sintéticos — mesma regra half-even da v1 (np.rint)
lo_s, hi_s = 0, 2 * 65535
ok = True
for r_val, esperado in [(1, 0), (3, 2), (5, 2), (7, 4), (2, 1), (-1, 0)]:
    obt = divround((r_val - lo_s) * 65535, hi_s - lo_s)
    ref = int(np.rint((r_val - lo_s) * (65535 / (hi_s - lo_s))))
    if obt != esperado or ref != esperado:
        ok = False
        print(f"    R={r_val}: obtido {obt}, np.rint {ref}, esperado {esperado}")
checar("empates .5 idênticos ao np.rint da pouw-quant-v1", ok)

# S5b: equivalência no dado real do bloco 1 (isolando o quantizador):
# mesma reconstrução float64 do caminho v1, quantizada pelas DUAS specs
sys.path.insert(0, str(RAIZ / "fase2"))
from verificar_fase2 import forward_torch64  # noqa: E402
from quantizar import hash_quantizado, limites_do_desafio, quantizar  # noqa: E402

import torch  # instrumento (desserialização .pt + forward de referência)
torch.set_num_threads(1)

DIR_CADEIA = RAIZ / "fase3" / "cadeia_demo"
rec64, receita, _n = forward_torch64(str(DIR_CADEIA / "receita_01.pt"), threads=1)
lo_f, hi_f = limites_do_desafio(str(DIR_CADEIA / "desafio_01.npy"))

# bits float64 da reconstrução → Q63 (o que o caminho inteiro produziria
# se fosse EXATAMENTE igual ao float64 — isola a diferença dos quantizadores)
r_bits = np.ascontiguousarray(rec64, dtype=np.float64).tobytes()
r_q63 = [f64_bits_para_q63(int.from_bytes(r_bits[i:i + 8], "little"))
         for i in range(0, len(r_bits), 8)]

lo_i, hi_i, ref_i, shape_i = limites_e_referencia_int(str(DIR_CADEIA / "desafio_01.npy"))
q_v1 = quantizar(rec64, lo_f, hi_f, 16)
q_v1_flat = np.asarray(q_v1).ravel().tolist()   # flat row-major p/ comparação
q_v2 = quantizar_int(r_q63, lo_i, hi_i)
bins_dif = sum(1 for a, b in zip(q_v1_flat, q_v2) if a != b)
checar("lo/hi inteiros == limites float64 (seleção por bits)", (lo_i / UM == lo_f) and (hi_i / UM == hi_f),
       f"lo {lo_i / UM:.12f} == {lo_f:.12f} | hi {hi_i / UM:.12f} == {hi_f:.12f}")
checar("quantizador v2 == v1 no dado real (0 bins divergentes)", bins_dif == 0,
       f"bins divergentes: {bins_dif}/{len(q_v1_flat)}")
print()

# ---------------- S6: forward inteiro do bloco 1 vs float64 ----------------
print("-- S6: forward inteiro do bloco 1 (end-to-end) --")
from exportar_pesos_int import exportar  # noqa: E402

DIR_PESOS = RAIZ / "fase5" / "pesos_int"
DIR_PESOS.mkdir(exist_ok=True)
bin_01 = DIR_PESOS / "pesos_int_cadeia_01.bin"

t_ini = time.perf_counter()
sha_bin, header_bin, n_pesos = exportar(str(DIR_CADEIA / "receita_01.pt"), str(bin_01))
t_exp = time.perf_counter() - t_ini
print(f"    exportação: {n_pesos} pesos → {bin_01.name} ({t_exp:.3f} s)")
print(f"    header: {header_bin}")

from siren_int import carregar_pesos_int  # noqa: E402
pesos = carregar_pesos_int(str(bin_01))

t_ini = time.perf_counter()
r_int = forward_int(pesos)
t_fwd_int = time.perf_counter() - t_ini

# v1 (float64) já computado acima (rec64); comparações em float — instrumento
delta_max = max(abs(r / UM - f) for r, f in zip(r_int, rec64.ravel().tolist()))
q_v2_fwd = quantizar_int(r_int, lo_i, hi_i)
bins_fwd = sum(1 for a, b in zip(q_v1_flat, q_v2_fwd) if a != b)
comp_v2 = hash_quantizado_int(q_v2_fwd, shape_i[0], shape_i[1])
comp_v1 = hash_quantizado(q_v1)

with open(DIR_CADEIA / "cadeia.json", "r", encoding="utf-8") as f:
    import json
    comp_publicado = json.load(f)["blocos"][0]["compromisso"]

print(f"    tempo forward v1 (torch float64, 1 thread): ", end="")
t_ini = time.perf_counter()
_ = forward_torch64(str(DIR_CADEIA / "receita_01.pt"), threads=1)
t_fwd_v1 = time.perf_counter() - t_ini
print(f"{t_fwd_v1:.6f} s")
print(f"    tempo forward v2 (inteiros Q63, Python puro): {t_fwd_int:.6f} s "
      f"({t_fwd_int / t_fwd_v1:.0f}× o v1)")
print(f"    max|ΔR| (v2 vs v1, em unidades do sinal): {delta_max:.3e} "
      f"({delta_max / ((hi_i - lo_i) / UM / 65535):.2f} passo-de-grade B16)")
print(f"    bins divergentes v1×v2 (mesma reconstrução de referência): {bins_fwd}/{len(q_v1_flat)}")
print(f"    compromisso v1 (pouw-quant-v1): {comp_v1[:32]}…")
print(f"    compromisso v2 (pouw-int-v1) : {comp_v2[:32]}…")
print("    (hashes divergem POR PROJETO: header de domínio distinto — o mesmo")
print("     array quantizado comprometido; a checagem certa é a do payload)")
comp_v2_sobre_array_v1 = hash_quantizado_int(q_v1_flat, shape_i[0], shape_i[1])
checar("compromisso v1 == publicado no cadeia.json (válida a própria referência)",
       comp_v1 == comp_publicado, comp_v1[:32] + "…")
checar("payload 8192 B idêntico: hash v2 sobre o array v1 == hash v2",
       bins_fwd == 0 and comp_v2_sobre_array_v1 == comp_v2,
       f"bins={bins_fwd}/4096 | hash_v2(array_v1)={comp_v2_sobre_array_v1[:16]}…")

# gate
from siren_int import gate_mse_int  # noqa: E402
s_v, esq, lim = gate_mse_int(r_int, ref_i, lo_i, hi_i, 40.0)
from quantizar import psnr_db  # noqa: E402
campo = np.load(str(DIR_CADEIA / "desafio_01.npy"))
psnr_v1 = psnr_db(campo, rec64)
print(f"    gate v2 (inteiro, exato): S·10^4 = {esq} ≤ limite = {lim} → "
       f"{'APROVADO' if s_v else 'REPROVADO'}")
print(f"    gate v1 (float64): PSNR = {psnr_v1:.4f} dB ≥ 40 → {'APROVADO' if psnr_v1 >= 40 else 'REPROVADO'}")
checar("vereditos do gate concordam (v1 float × v2 inteiro)",
       s_v == (psnr_v1 >= 40.0))
print()

# ---------------- S7: re-export determinístico ----------------
print("-- S7: re-export determinístico do .bin --")
sha_bin_2, _, _ = exportar(str(DIR_CADEIA / "receita_01.pt"), str(DIR_PESOS / "pesos_int_cadeia_01.tmp.bin"))
checar("re-export produz bytes idênticos", sha_bin_2 == sha_bin, sha_bin[:32] + "…")
(DIR_PESOS / "pesos_int_cadeia_01.tmp.bin").unlink()
print()

# ---------------- resumo ----------------
print("-- RESUMO DO SMOKE --")
if FALHAS:
    print(f"FALHAS: {len(FALHAS)} → {', '.join(FALHAS)}")
    print("RESULTADO: SMOKE REPROVADO (código 1)")
    raise SystemExit(1)
print("Todas as checagens OK")
print("RESULTADO: SMOKE APROVADO (código 0)")
print(f"FIM {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
