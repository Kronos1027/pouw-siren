#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
experimento_dificuldade.py — PoUW Fase 2, EXPERIMENTO E4.

PERGUNTA: como o "difficulty" via alvo de PSNR escala o custo do TREINO
(lado caro — o trabalho útil) em relação ao custo da VERIFICAÇÃO (lado
barato — consenso)?

MÉTODO: mesmo desafio (seed 001, b0f90ffe), varredura de alvo de PSNR em
{40, 45, 50, 55, 60, 65} dB, executando para cada alvo:
  1. treinar.py da Fase 1 (INTOCADO — mesmo código, mesmo critério declarado:
     PSNR >= alvo a cada 100 épocas OU 5000 épocas), com --saida em fase2/;
  2. verificar_fase2.py (consenso: forward float64 + hash quantizado B=16),
     com --alvo-psnr igual ao alvo do treino (código de saída = validade).
Coleta: épocas, PSNR de treino e de verificação, tempo de treino
(perf_counter dentro do treinar.py), tempo de verificação (perf_counter
dentro do verificar_fase2.py), razão treino/verificação e o compromisso
quantizado de cada receita.

TREINOS RODADOS AQUI (2026-09-02, 2 threads default do torch) + números
HISTÓRICOS da Fase 1 para cruzamento (rotulados; logs em logs/etapa2.md):
  F1 40 dB: 100 épocas, 4,087526 s  | F1 60 dB (extra): 500 épocas, 9,739328 s
  (o treino é determinístico nesta máquina — re-executar 40/60 aqui produz
   pesos idênticos em valor; os arquivos .pt diferem em bytes pelo timestamp
   do zip, limitação 3 da Fase 1).

Uso (a partir da raiz do repositório):
    python3 fase2/experimento_dificuldade.py
"""

import platform
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESAFIO = "desafio_b0f90ffe.npy"
ALVOS = [40, 45, 50, 55, 60, 65]
MAX_EPOCAS = 5000

RE_TREINO = re.compile(r"Tempo de treino \(perf_counter.*?\): ([0-9.]+) s")
RE_EPOCAS = re.compile(r"Total de epocas executadas: (\d+)")
RE_PSNR_TREINO = re.compile(r"PSNR final \(avaliacao pos-treino, float64\): ([0-9.]+) dB")
RE_HASH_RECEITA = re.compile(r"SHA-256 da receita: ([0-9a-f]{64})")
RE_PARADA = re.compile(r"Parada: (.+)")
RE_VERIF = re.compile(r"TEMPO TOTAL DE VERIFICAÇÃO \(carga -> hash -> PSNR, sem imports\): ([0-9.]+) s")
RE_PSNR_VERIF = re.compile(r"PSNR \(reconstrução float64 vs desafio\): ([0-9.]+) dB")
RE_COMPROMISSO = re.compile(r"COMPROMISSO QUANTIZADO \(pouw-quant-v1\|B=16\|64x64\|\): ([0-9a-f]{64})")
RE_IMPORT = re.compile(r"Import do PyTorch levou: ([0-9.]+) s")


def rodar(cmd, rotulo):
    print(f"\n-------- $ {' '.join(cmd)} --------")
    r = subprocess.run(cmd, cwd=str(RAIZ), capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0 or r.stderr:
        sys.stdout.write("-- STDERR --\n")
        sys.stdout.write(r.stderr)
    print(f"[{rotulo}] código de saída: {r.returncode}")
    return r


def main():
    print("== experimento_dificuldade.py — PoUW Fase 2, E4 (dificuldade via alvo de PSNR) ==")
    print(f"Python {platform.python_version()} | executor: {sys.executable}")
    print(f"RAIZ: {RAIZ} | desafio: {DESAFIO} | alvos: {ALVOS} dB | max-epocas: {MAX_EPOCAS}")
    print("Treino: treinar.py da Fase 1 intocado (2 threads default) | Verificação: verificar_fase2.py (float64, 1 thread, B=16)")
    print("Convenção de tempos idêntica à Fase 1: perf_counter interno, SEM tempo de import.")
    t0 = time.perf_counter()

    linhas = []
    for alvo in ALVOS:
        saida = f"fase2/receita_alvo{alvo}db_b0f90ffe.pt"
        print(f"\n########## ALVO {alvo} dB ##########")
        r1 = rodar([sys.executable, "treinar.py", DESAFIO,
                    "--max-epocas", str(MAX_EPOCAS), "--alvo-psnr", str(alvo),
                    "--saida", saida], f"treino alvo {alvo}")
        if r1.returncode != 0:
            linhas.append((alvo, "FALHOU", None, None, None, None, None, None))
            continue
        def g(rx):
            m = rx.search(r1.stdout)
            return m.group(1) if m else None
        t_treino = float(g(RE_TREINO))
        epocas = int(g(RE_EPOCAS))
        psnr_t = float(g(RE_PSNR_TREINO))
        hash_rec = g(RE_HASH_RECEITA)
        parada = g(RE_PARADA)

        r2 = rodar([sys.executable, "fase2/verificar_fase2.py", saida, DESAFIO,
                    "--alvo-psnr", str(alvo)], f"verificação alvo {alvo}")
        if r2.returncode not in (0, 1):
            linhas.append((alvo, f"verificador ERRO ({r2.returncode})", epocas, psnr_t, t_treino, None, None, None))
            continue
        t_ver = float((RE_VERIF.search(r2.stdout) or [None, None])[1])
        psnr_v = float((RE_PSNR_VERIF.search(r2.stdout) or [None, None])[1])
        comp = (RE_COMPROMISSO.search(r2.stdout) or [None, None])[1]
        valido = (r2.returncode == 0)
        linhas.append((alvo, parada, epocas, psnr_t, t_treino, psnr_v, t_ver, comp))
        print(f"[resumo alvo {alvo}] parada: {parada} | épocas {epocas} | PSNR treino {psnr_t} | PSNR verif {psnr_v} | treino {t_treino:.6f} s | verif {t_ver:.6f} s | razão {t_treino / t_ver:.1f}x | válido p/ consenso: {valido}")

    print("\n======== TABELA-RESUMO E4 (tudo medido AQUI, 2026-09-02; saída crua acima) ========")
    print(f"{'alvo':>4} | {'parada':<28} | {'épocas':>6} | {'PSNR treino':>11} | {'PSNR verif':>10} | {'treino (s)':>10} | {'verif (s)':>9} | {'razão':>7} | compromisso B=16")
    print("-" * 150)
    for alvo, parada, epocas, psnr_t, t_treino, psnr_v, t_ver, comp in linhas:
        if t_ver is None or t_treino is None:
            print(f"{alvo:>4} | {str(parada):<28} | {str(epocas):>6} | {str(psnr_t):>11} | — | — | — | — | —")
            continue
        print(f"{alvo:>4} | {str(parada):<28} | {epocas:>6} | {psnr_t:>11.4f} | {psnr_v:>10.4f} | {t_treino:>10.6f} | {t_ver:>9.6f} | {t_treino / t_ver:>6.1f}x | {comp[:16]}…")

    print()
    print("Cruzamento com números HISTÓRICOS da Fase 1 (NÃO medidos aqui; ver logs/etapa2.md da F1):")
    print("  F1 alvo 40 dB: 100 épocas, treino 4,087526 s, PSNR 49,6253 (receita_b0f90ffe.pt)")
    print("  F1 alvo 60 dB: 500 épocas, treino 9,739328 s, PSNR 60,8704 (receita_extra_60db_b0f90ffe.pt)")
    print()
    print(f"Tempo total do experimento (parede, incl. subprocessos e imports): {time.perf_counter() - t0:.3f} s")


if __name__ == "__main__":
    main()
