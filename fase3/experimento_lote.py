#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
experimento_lote.py — PoUW Fase 3, EXPERIMENTO E3: verificação em LOTE
(runtime persistente) vs verificação FRIO (processo novo por chamada).

PERGUNTA: qual o custo REAL de verificar uma cadeia inteira de N blocos nas
duas extremidades operacionais? (limitação 7/8 da F1 e 8 da F2: o import do
PyTorch ~1,1 s DOMINA a verificação em processo frio — com runtime persistente
e lote, quanto cai o custo por bloco?)

MÉTODO (tudo medido; nada estimado):
  (1) LOTE PERSISTENTE: 1 processo importa torch 1× e chama
      verificar_cadeia_completa() R=5 vezes seguidas (a mesma cadeia, do
      disco) → mediana do tempo por passada = custo de "sincronizar" a cadeia
      com o runtime quente (o caso de um nó que valida blocos que chegam).
  (2) FRIO-CADEIA: 1 subprocesso verificar_cadeia.py (processo novo; importa
      torch; verifica os N blocos) → tempo interno de verificação + parede.
  (3) FRIO-POR-BLOCO: N subprocessos verificar_cadeia.py --apenas-bloco i
      (o caso mais pessimista: 1 processo novo por bloco) → soma dos tempos
      internos + soma das paredes.
Saída: tabela comparativa (lote vs frio-cadeia vs frio-por-bloco), throughput
(blocos/s) e custo do import amortizado.

Uso (a partir da raiz do repositório):
    python3 fase3/experimento_lote.py [fase3/cadeia_demo] [--repeticoes 5]
"""

import argparse
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "fase2"))
sys.path.insert(0, str(RAIZ / "fase3"))

RE_VERIF = re.compile(r"TEMPO TOTAL DE VERIFICAÇÃO \(carga do JSON -> último PSNR, sem imports\): ([0-9.]+) s")
RE_PAREDE = re.compile(r"Tempo total do processo \(incl\. import do PyTorch\): ([0-9.]+) s")
RE_N_BLOCOS = re.compile(r"n_blocos.: (\d+)")


def agora_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def main():
    ap = argparse.ArgumentParser(description="E3 — verificação em lote vs fria — PoUW Fase 3")
    ap.add_argument("dir_cadeia", nargs="?", default="fase3/cadeia_demo")
    ap.add_argument("--repeticoes", type=int, default=5)
    args = ap.parse_args()

    dir_cadeia = Path(args.dir_cadeia)
    if not dir_cadeia.is_absolute():
        dir_cadeia = RAIZ / dir_cadeia
    R = args.repeticoes

    t0 = time.perf_counter()
    print("== experimento_lote.py — PoUW Fase 3, E3 (lote persistente vs frio) ==")
    print(f"INICIO {agora_utc()}")

    # ---------- import medido 1× (para o lote) ----------
    t_imp = time.perf_counter()
    import torch  # noqa: E402
    import json  # noqa: E402
    from verificar_fase2 import forward_torch64  # noqa: E402
    from verificar_cadeia import verificar_cadeia_completa  # noqa: E402
    t_import = time.perf_counter() - t_imp
    torch.set_num_threads(1)

    with open(dir_cadeia / "cadeia.json", "r", encoding="utf-8") as f:
        cadeia = json.load(f)
    n_blocos = int(cadeia["n_blocos"])

    import platform
    print(f"Python {platform.python_version()} | PyTorch {torch.__version__} | NumPy {__import__('numpy').__version__}")
    print(f"Cadeia: {dir_cadeia} | blocos: {n_blocos} | repetições do lote: {R}")
    print(f"Import do PyTorch + verificar_fase2 + verificar_cadeia: {t_import:.3f} s (1×; amortizado no lote)")
    print()

    # ---------- (1) LOTE PERSISTENTE ----------
    print("-------- (1) LOTE PERSISTENTE (1 processo; R passadas sobre a cadeia inteira) --------")
    tempos_lote = []
    for r in range(R):
        t = time.perf_counter()
        res = verificar_cadeia_completa(dir_cadeia, forward_torch64, verbose=False)
        dt = time.perf_counter() - t
        tempos_lote.append(dt)
        ok = "VÁLIDA" if res["cadeia_ok"] else "INVÁLIDA"
        print(f"  passada {r + 1}/{R}: {dt:.6f} s | cadeia {ok} | {n_blocos} blocos")
    lote_med = statistics.median(tempos_lote)
    print(f"  mediana: {lote_med:.6f} s | por bloco: {lote_med / n_blocos:.6f} s | throughput: {n_blocos / lote_med:.2f} blocos/s")
    print()

    # ---------- (2) FRIO-CADEIA (1 subprocesso) ----------
    print("-------- (2) FRIO-CADEIA (1 subprocesso novo; importa torch; N blocos) --------")
    r = subprocess.run([sys.executable, "fase3/verificar_cadeia.py", str(dir_cadeia)],
                       cwd=str(RAIZ), capture_output=True, text=True)
    if r.returncode not in (0, 1):
        print(r.stderr)
        raise RuntimeError(f"verificar_cadeia.py falhou: código {r.returncode}")
    frio_cadeia_ver = float(RE_VERIF.search(r.stdout).group(1))
    frio_cadeia_parede = float(RE_PAREDE.search(r.stdout).group(1))
    resultado = "VÁLIDA" if r.returncode == 0 else "INVÁLIDA"
    print(f"  verificação interna (sem import): {frio_cadeia_ver:.6f} s | parede do subprocesso: {frio_cadeia_parede:.6f} s | cadeia {resultado}")
    print()

    # ---------- (3) FRIO-POR-BLOCO (N subprocessos) ----------
    print("-------- (3) FRIO-POR-BLOCO (N subprocessos novos, 1 por bloco) --------")
    soma_ver = 0.0
    soma_parede = 0.0
    for b in [blk["bloco"] for blk in cadeia["blocos"]]:
        rb = subprocess.run([sys.executable, "fase3/verificar_cadeia.py", str(dir_cadeia),
                             "--apenas-bloco", str(b)],
                            cwd=str(RAIZ), capture_output=True, text=True)
        if rb.returncode not in (0, 1):
            print(rb.stderr)
            raise RuntimeError(f"verificar_cadeia.py --apenas-bloco {b} falhou: código {rb.returncode}")
        tv = float(RE_VERIF.search(rb.stdout).group(1))
        tp = float(RE_PAREDE.search(rb.stdout).group(1))
        soma_ver += tv
        soma_parede += tp
        print(f"  bloco {b}: verificação interna {tv:.6f} s | parede {tp:.6f} s")
    print(f"  SOMA interna: {soma_ver:.6f} s | SOMA paredes: {soma_parede:.6f} s | por bloco (parede): {soma_parede / n_blocos:.6f} s")
    print()

    # ---------- TABELA FINAL ----------
    print("======== TABELA-RESUMO E3 (tudo medido; N = blocos da cadeia) ========")
    print(f"{'modo':<18} | {'verif. total (s)':>17} | {'parede total (s)':>17} | {'por bloco (s)':>13} | {'blocos/s':>9}")
    print("-" * 90)
    print(f"{'lote persistente':<18} | {lote_med:>17.6f} | {lote_med + t_import:>17.6f} | {lote_med / n_blocos:>13.6f} | {n_blocos / lote_med:>9.2f}")
    print(f"{'frio-cadeia':<18} | {frio_cadeia_ver:>17.6f} | {frio_cadeia_parede:>17.6f} | {frio_cadeia_parede / n_blocos:>13.6f} | {n_blocos / frio_cadeia_parede:>9.2f}")
    print(f"{'frio-por-bloco':<18} | {soma_ver:>17.6f} | {soma_parede:>17.6f} | {soma_parede / n_blocos:>13.6f} | {n_blocos / soma_parede:>9.2f}")
    print()
    print("LEITURA (dado; interpretação no relatório):")
    print(f"  - import do PyTorch medido aqui: {t_import:.3f} s = {t_import / lote_med:.0f}× o tempo de verificar {n_blocos} blocos em lote")
    print(f"  - custo por bloco: lote {lote_med / n_blocos * 1000:.1f} ms vs frio-por-bloco {soma_parede / n_blocos * 1000:.1f} ms de parede "
          f"({soma_parede / lote_med:.1f}× mais caro o frio)")
    print(f"  - tempo de mineração da cadeia (registrado no cadeia.json): "
          f"{cadeia['resumo_mineracao']['parede_mineracao_s']} s → razão mineração/lote = "
          f"{cadeia['resumo_mineracao']['parede_mineracao_s'] / lote_med:.1f}×")
    print()
    print(f"Tempo total do experimento (parede): {time.perf_counter() - t0:.3f} s")
    print(f"FIM {agora_utc()}")


if __name__ == "__main__":
    main()
