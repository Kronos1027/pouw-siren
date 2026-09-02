#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quantizar.py — PoUW Fase 2: especificação CANÔNICA de quantização fixed-point
e hash de compromisso determinístico (requisito de consenso cross-CPU).

MOTIVAÇÃO (medido na Fase 1, limitação 4 do relatório):
  O forward pass em float32 usa operações vetoriais cujo arredondamento difere
  entre CPUs/BLAS nos últimos bits (divergência real medida pelo usuário:
  7.15e-07 de diferença máxima absoluta entre a reconstrução na CPU Xeon do
  repositório e a CPU local dele; PSNR idêntico, hash float32 DIVERGENTE).
  Um hash sobre floats cru não serve como regra de consenso.

ESPECIFICAÇÃO pouw-quant-v1 (deve ser seguida À RISCA por minerador e verificador):
  Entradas:
    R  : reconstrução, ndarray (H, W) convertido para float64
    lo : mínimo do DESAFIO original (float64, lido do .npy — âncora de bytes)
    hi : máximo do DESAFIO original (float64)
    B  : bits de quantização (8 ou 16)
  Passos (todos em float64 escalar, SEM operações vetoriais de redução):
    s   = (2^B − 1) / (hi − lo)          # divisão IEEE-754, determinística
    q_f = (R − lo) · s                   # broadcasting float64
    q   = clip(rint(q_f), 0, 2^B − 1)    # rint = arredondar-meio-para-par
                                        # (np.rint); clip para overshoots
    bytes = q.astype(">u2" se B>8 senão ">u1").tobytes()   # big-endian,
                                        # ordem C (row-major)
    hash  = SHA-256( "pouw-quant-v1|B=<B>|<H>x<W>|" (ASCII) ‖ bytes )
  Propriedade determinística:
    adição/subtração/multiplicação/divisão float64 e rint são operações
    corretamente arredondadas pelo IEEE-754 → bit-idênticas entre CPUs para
    o MESMO R. A ÚNICA fonte de variação entre máquinas é o próprio R
    (forward pass da rede) — que a Fase 2 padroniza em float64
    (verificar_fase2.py) e cujo resíduo residual é absorvido pela margem
    da grade de quantização (medido em experimento_ruido.py).

Uso (CLI):
    python3 fase2/quantizar.py <reconstrucao.npy> <desafio.npy> [--bits 16]
"""

import argparse
import hashlib
import platform
import time

import numpy as np

VERSAO_SPEC = "pouw-quant-v1"


def limites_do_desafio(desafio):
    """lo/hi do desafio (float64). O .npy do desafio é a âncora de bytes:
    os mesmos bytes em qualquer máquina dão os mesmos lo/hi (min/max não
    envolvem aritmética, apenas seleção)."""
    campo = np.load(desafio)
    c64 = np.asarray(campo, dtype=np.float64)
    return float(c64.min()), float(c64.max())


def quantizar(rec, lo, hi, B):
    """Quantização canônica pouw-quant-v1. Retorna ndarray uint16 (B>8) ou
    uint8 (B<=8) com valores em [0, 2^B−1]."""
    if hi <= lo:
        raise ValueError(f"limites degenerados: lo={lo}, hi={hi}")
    if B < 2 or B > 16:
        raise ValueError(f"B deve estar em [2, 16]; recebi B={B}")
    r64 = np.asarray(rec, dtype=np.float64)
    s = (2**B - 1) / (hi - lo)
    q_f = (r64 - lo) * s
    q = np.clip(np.rint(q_f), 0, 2**B - 1)
    if B > 8:
        return q.astype(np.uint16)
    return q.astype(np.uint8)


def desquantizar(q, lo, hi, B):
    """Inverso da quantização (float64). Uso analítico (PSNR da quantização);
    não faz parte da regra de consenso."""
    q = np.asarray(q, dtype=np.float64)
    s = (2**B - 1) / (hi - lo)
    return q / s + lo


def hash_quantizado(q):
    """SHA-256 do compromisso quantizado com separação de domínio
    (versão da spec, B e forma vão na pré-imagem; bytes big-endian)."""
    q = np.asarray(q)
    h, w = q.shape
    B = 16 if q.dtype == np.uint16 else 8
    dtype_be = ">u2" if B > 8 else ">u1"
    preimagem = (
        f"{VERSAO_SPEC}|B={B}|{h}x{w}|".encode("ascii")
        + q.astype(dtype_be).tobytes()
    )
    return hashlib.sha256(preimagem).hexdigest()


def passo(lo, hi, B):
    """Passo da grade em unidades do sinal (float64): (hi−lo)/(2^B−1)."""
    return (hi - lo) / (2**B - 1)


def psnr_db(referencia, reconstrucao):
    """Idêntica à da Fase 1: 20·log10(pico/RMSE), pico = max−min da
    referencia, tudo em float64."""
    ref = np.asarray(referencia, dtype=np.float64)
    rec = np.asarray(reconstrucao, dtype=np.float64)
    rmse = float(np.sqrt(np.mean((rec - ref) ** 2)))
    pico = float(ref.max() - ref.min())
    return 20.0 * np.log10(pico / rmse)


def main():
    ap = argparse.ArgumentParser(description="Quantização canônica pouw-quant-v1 — PoUW Fase 2")
    ap.add_argument("reconstrucao", help="arquivo .npy da reconstrução (qualquer dtype float)")
    ap.add_argument("desafio", help="arquivo .npy do desafio original (fonte de lo/hi)")
    ap.add_argument("--bits", type=int, default=16, choices=[8, 16], help="bits de quantização (default 16)")
    args = ap.parse_args()

    t_ini = time.perf_counter()

    rec = np.load(args.reconstrucao)
    lo, hi = limites_do_desafio(args.desafio)
    B = args.bits
    st = passo(lo, hi, B)

    q = quantizar(rec, lo, hi, B)
    hq = hash_quantizado(q)
    rec_deq = desquantizar(q, lo, hi, B)

    campo = np.load(args.desafio)
    psnr_cru = psnr_db(campo, rec)
    psnr_deq = psnr_db(campo, rec_deq)

    t_fim = time.perf_counter()

    print("== quantizar.py — PoUW Fase 2 (quantização canônica pouw-quant-v1) ==")
    print(f"Python {platform.python_version()} | NumPy {np.__version__}")
    print(f"Reconstrução: {args.reconstrucao} (dtype {rec.dtype}, forma {rec.shape})")
    print(f"Desafio: {args.desafio} → lo={lo:.10f}, hi={hi:.10f} (pico={hi - lo:.10f})")
    print(f"B = {B} bits → {2**B} níveis | passo da grade = {st:.10e} (unidades do sinal)")
    print(f"PSNR (reconstrução crua vs desafio, float64): {psnr_cru:.4f} dB")
    print(f"PSNR (dequantizada vs desafio, float64): {psnr_deq:.4f} dB  ← custo da quantização")
    print(f"Tempo (carga + quantização + 2×PSNR + hash): {t_fim - t_ini:.6f} s")
    print()
    print(f"HASH QUANTIZADO [{VERSAO_SPEC}|B={B}|{q.shape[0]}x{q.shape[1]}| + {q.size * (2 if B > 8 else 1)} bytes big-endian]:")
    print(hq)


if __name__ == "__main__":
    main()
