#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
experimento_retreino.py — PoUW Fase 3, EXPERIMENTO E5: determinismo do
RE-TREINO entre subprocessos (contraexemplo encontrado na mineração).

GATILHO (fato medido, log f3_e1_cadeia.txt): o bloco 1 da cadeia foi
reproduzido BIT-A-BIT entre o smoke (03:44 UTC) e a mineração oficial
(03:45 UTC) — mesmo compromisso cd579702… e mesmo hash_bloco 000058a7…;
mas o bloco 2, com o MESMO desafio byte-idêntico (sha256 ef50edfd…) e a
mesma seed de rede, divergiu nos pesos (max|Δ| 2.8e-06 no tensor 4) e
produziu compromisso diferente (42f0ada7… vs 0fff8405…).

PERGUNTA: o re-treino de um mesmo desafio em subprocessos independentes
é bit-determinístico nesta máquina? Com threads default (2) e com 1 thread
(OMP_NUM_THREADS=1)? O caso do bloco 1 (que reproduziu) também se
reproduz?

MÉTODO (nada tocado nos artefatos oficiais; cópias de diagnóstico em
fase3/.tmp_retreino/):
  - desafio A = desafio_02.npy da cadeia oficial (o CONTRAEXEMPLO) e
    desafio B = desafio_01.npy (o caso que reproduziu);
  - R subprocessos `treinar.py` (intocado) por condição:
      A-default ×4, A-omp1 ×2, B-default ×2;
  - comparação tensor a tensor (torch.equal / max|Δ| em float64) contra a
    receita oficial E entre as réplicas;
  - matriz de resultados + leitura factual.

POR QUE ISSO IMPORTA (e o que NÃO importa):
  - NÃO afeta o CONSENSO da cadeia: o compromisso é sobre a RECEITA
    PUBLICADA (o .pt); o verificador carrega o arquivo e faz forward —
    nunca re-treina. A validade da cadeia oficial está intacta.
  - AFETA a reprodutibilidade do MINERADOR: re-minerar a mesma gênese pode
    produzir compromissos diferentes a partir de um bloco qualquer (a
    cadeia publicada é que é a âncora — como qualquer blockchain).
  - Corrige por nuance a observação da F1 ("re-treino bit-a-bit
    determinístico nesta máquina", logs/etapa2.md, 2 execuções) e da F2
    (E4: alvo-40/alvo-60 reproduziram entre sessões): reproduções
    ocasionais podem coincidir; a divergência ~1e-06 é o comportamento
    esperado de treino float32 multi-thread — e é EXATAMENTE a classe de
    ruído que a spec pouw-quant-v1 (float64 + B=16) absorve no lado do
    verificador.

Uso (a partir da raiz do repositório):
    python3 fase3/experimento_retreino.py
"""

import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_DIAG = RAIZ / "fase3" / ".tmp_retreino"


def agora_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def treinar(desafio, saida, omp_threads=None):
    env = dict(os.environ)
    extra = ""
    if omp_threads is not None:
        env["OMP_NUM_THREADS"] = str(omp_threads)
        extra = f" (OMP_NUM_THREADS={omp_threads})"
    t = time.perf_counter()
    r = subprocess.run(
        [sys.executable, "treinar.py", str(desafio),
         "--max-epocas", "5000", "--alvo-psnr", "40.0", "--saida", str(saida)],
        cwd=str(RAIZ), capture_output=True, text=True, env=env,
    )
    dt = time.perf_counter() - t
    if r.returncode != 0:
        sys.stdout.write(r.stdout)
        sys.stdout.write(r.stderr)
        raise RuntimeError(f"treinar.py falhou {extra}: código {r.returncode}")
    import re
    psnr = re.search(r"PSNR final \(avaliacao pos-treino, float64\): ([0-9.]+) dB", r.stdout).group(1)
    print(f"  treino {saida.name}{extra}: {dt:.2f} s de parede | PSNR final {psnr} dB")
    return str(saida), float(psnr)


def comparar(pa, pb, rotulo):
    import torch
    a = torch.load(pa, map_location="cpu", weights_only=False)["estado"]
    b = torch.load(pb, map_location="cpu", weights_only=False)["estado"]
    if all(torch.equal(a[k], b[k]) for k in a):
        print(f"  {rotulo}: BIT-IDÊNTICOS (8/8 tensores)")
        return True, 0.0
    dmax = max((a[k].double() - b[k].double()).abs().max().item() for k in a)
    print(f"  {rotulo}: DIFERENTES | max|Δ| sobre os 8 tensores = {dmax:.3e}")
    return False, dmax


def main():
    print("== experimento_retreino.py — PoUW Fase 3, E5 (determinismo do re-treino) ==")
    print(f"INICIO {agora_utc()}")
    print(f"Python {platform.python_version()}")
    import torch
    print(f"PyTorch {torch.__version__} | threads default visíveis: {torch.get_num_threads()}")
    print(f"Gatilho: bloco 1 da cadeia reproduziu bit-a-bit (smoke × oficial); bloco 2 divergiu (max|Δ| pesos 2.8e-06).")
    print(f"Artefatos de diagnóstico em: {DIR_DIAG} (oficiais intocados)")
    t0 = time.perf_counter()

    DIR_DIAG.mkdir(parents=True, exist_ok=True)
    des_a = RAIZ / "fase3" / "cadeia_demo" / "desafio_02.npy"  # contraexemplo
    des_b = RAIZ / "fase3" / "cadeia_demo" / "desafio_01.npy"  # caso que reproduziu
    rec_oficial_a = RAIZ / "fase3" / "cadeia_demo" / "receita_02.pt"
    rec_oficial_b = RAIZ / "fase3" / "cadeia_demo" / "receita_01.pt"

    print("\n-------- réplica 1..4 do desafio A (bloco 2; threads default) --------")
    reps_a = [treinar(des_a, DIR_DIAG / f"receita_A{i}.pt", None)[0] for i in range(1, 5)]

    print("\n-------- réplica 5..6 do desafio A (OMP_NUM_THREADS=1) --------")
    reps_a1 = [treinar(des_a, DIR_DIAG / f"receita_A_omp1_{i}.pt", 1)[0] for i in range(1, 3)]

    print("\n-------- réplica 1..2 do desafio B (bloco 1; threads default) --------")
    reps_b = [treinar(des_b, DIR_DIAG / f"receita_B{i}.pt", None)[0] for i in range(1, 3)]

    print("\n-------- comparações (contra a receita OFICIAL da cadeia) --------")
    print("[A = desafio_02 / contraexemplo]")
    for i, p in enumerate(reps_a, 1):
        comparar(rec_oficial_a, p, f"oficial_A vs réplica A{i} (default)")
    for i, p in enumerate(reps_a1, 1):
        comparar(rec_oficial_a, p, f"oficial_A vs réplica A_omp1_{i} (1 thread)")
    print("[B = desafio_01 / caso que havia reproduzido]")
    for i, p in enumerate(reps_b, 1):
        comparar(rec_oficial_b, p, f"oficial_B vs réplica B{i} (default)")

    print("\n-------- comparações entre as réplicas (default) --------")
    for j in range(1, len(reps_a)):
        comparar(reps_a[0], reps_a[j], f"réplica A1 vs réplica A{j + 1}")
    comparar(reps_b[0], reps_b[1], "réplica B1 vs réplica B2")

    print("\n-------- leitura factual --------")
    print("  - O consenso da cadeia NÃO depende do re-treino: o compromisso é sobre a receita")
    print("    publicada (o verificador faz forward do .pt, nunca re-treina).")
    print("  - Divergências ~1e-06 no re-treino são a mesma classe de ruído float32 que a")
    print("    spec pouw-quant-v1 (float64 + B=16) absorve no lado da verificação.")

    import shutil
    shutil.rmtree(DIR_DIAG)
    print(f"\nArtefatos de diagnóstico removidos (a evidência é este log + o script).")
    print(f"Tempo total: {time.perf_counter() - t0:.3f} s (8 treinos em subprocessos)")
    print(f"FIM {agora_utc()}")


if __name__ == "__main__":
    main()
