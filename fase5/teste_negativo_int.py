#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teste_negativo_int.py — PoUW Fase 5, experimento E4: suíte ADVERSARIAL do
caminho inteiro (pouw-int-v1).

E4a — SENSIBILIDADE QUANTITATIVA (in-process, 100% inteiros):
  perturba UM único peso (W da camada 1, unidade 0, canal x) em δ ∈
  {1, 2^10, 2^20, 2^30, 2^33, 2^40} LSBs de Q63 e mede: bins B16 mudados,
  hash de compromisso mudou?, veredito do gate. Replica no caminho COMPLETO
  o que a F2/E2 mediu no quantizador isolado: perturbações abaixo do piso
  da grade de quantização são INVISÍVEIS POR PROJETO (o compromisso
  quantizado não é um detector de nano-adulterações — é um compromisso de
  CONTEÚDO; a âncora de bytes SHA-256 do .bin cobre o resto).

E4b — FRAUDES ESTRUTURAIS (subprocessos frios do verificar_int.py):
  N1  controle positivo (bloco 1 íntegro, compromisso esperado correto)
  N2  compromisso esperado ADULTERADO (1 dígito hex)     → C1 deve pegar
  N3  pesos de OUTRO bloco contra o desafio do bloco 1   → C1 + C2
  N4  desafio ADULTERADO (byte do pixel máximo)          → H2 + C1
  N5  SWAP de dois pesos no .bin (x↔y da unidade 0)      → C1
  N6  gate mais rígido (alvo 50 dB com receita de ~40 dB)→ C2

Saída: tabela por caso (esperado × obtido, código de saída). Código de
saída do script: 0 = todos os casos comportaram como esperado.

Uso (a partir da raiz do repositório):
    python3 -u fase5/teste_negativo_int.py
"""

import hashlib
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "fase5"))

from siren_int import (  # noqa: E402
    carregar_pesos_int, forward_int, gate_mse_int, hash_quantizado_int,
    limites_e_referencia_int, quantizar_int,
)

BIN_01 = RAIZ / "fase5" / "pesos_int" / "pesos_int_cadeia_01.bin"
BIN_02 = RAIZ / "fase5" / "pesos_int" / "pesos_int_cadeia_02.bin"
BIN_F2_40 = RAIZ / "fase5" / "pesos_int" / "pesos_int_f2_alvo40db.bin"
DESAFIO_01 = RAIZ / "fase3" / "cadeia_demo" / "desafio_01.npy"
QUANT_01 = RAIZ / "fase3" / "cadeia_demo" / "quantizada_01_u16.npy"
DESAFIO_F1 = RAIZ / "desafio_b0f90ffe.npy"
VERIFICADOR = RAIZ / "fase5" / "verificar_int.py"
TMP = RAIZ / "fase5" / "logs" / "negativos_tmp"

UM = 1 << 63


def agora():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def main():
    print("== teste_negativo_int.py — PoUW Fase 5 (E4: suíte adversarial "
          "do caminho inteiro) ==")
    print(f"INICIO {agora()}")
    print()

    # ================= E4a: sweep de sensibilidade =================
    print("-- E4a: sensibilidade a perturbação de 1 peso (in-process) --")
    pesos = carregar_pesos_int(str(BIN_01))
    lo, hi, ref, shape = limites_e_referencia_int(str(DESAFIO_01))

    t0 = time.perf_counter()
    r_base = forward_int(pesos)
    q_base = quantizar_int(r_base, lo, hi)
    comp_base = hash_quantizado_int(q_base, shape[0], shape[1])
    print(f"baseline (íntegro): forward {time.perf_counter() - t0:.2f} s | "
          f"comp {comp_base[:16]}…")
    print()

    deltas = [1, 1 << 10, 1 << 20, 1 << 30, 1 << 33, 1 << 40]
    print(f"{'δ (LSB Q63)':>12} | {'δ (unid. do sinal)':>19} | "
          f"{'bins/4096':>10} | {'hash mudou':>10} | gate")
    resultados = []
    for d in deltas:
        p2 = carregar_pesos_int(str(BIN_01))
        p2["W"][0][0][0] += d
        r = forward_int(p2)
        q = quantizar_int(r, lo, hi)
        comp = hash_quantizado_int(q, shape[0], shape[1])
        bins = sum(1 for a, b in zip(q_base, q) if a != b)
        gate_ok, _esq, _lim = gate_mse_int(r, ref, lo, hi, 40)
        mudou = comp != comp_base
        print(f"{d:>12} | {d / UM:>19.3e} | {bins:>10} | "
              f"{'SIM' if mudou else 'NÃO':>10} | "
              f"{'APROVADO' if gate_ok else 'REPROVADO'}")
        resultados.append((d, bins, mudou, gate_ok))
    print()
    print("LEITURA (medido): perturbação de 1 peso até δ=2^33 LSB (≈9e-10 do")
    print("sinal) é INVISÍVEL ao compromisso quantizado — o mesmo piso de")
    print("ruído que a F2/E2 mediu no quantizador isolado (projeto: o hash")
    print("compromete o CONTEÚDO quantizado com passo B=16 ≈ 1,5e-5, não")
    print("nano-diferenças; a âncora SHA-256 do .bin cobre a integridade")
    print("byte-a-byte, como N5/H1 demonstram). Em δ=2^40 (≈1,2e-7 do sinal)")
    print("o compromisso já muda (2 bins de 4096). [1ª execução desta suíte")
    print("trouxera LEITURA prevista errada (piso em 2^30–2^33) — preservada")
    print("em f5_e4_negativos_EXECUCAO1_LEITURA_ERRADA.txt]")
    print()

    # ================= E4b: fraudes estruturais =================
    print("-- E4b: fraudes estruturais (subprocessos frios do verificar_int) --")
    TMP.mkdir(parents=True, exist_ok=True)

    def rodar_caso(nome, args, espera_valido):
        cmd = [sys.executable, "-u", str(VERIFICADOR)] + args
        p = subprocess.run(cmd, capture_output=True, text=True)
        saida = (p.stdout + p.stderr).strip()
        # imprime a saída INTEGRAL do verificador (evidência bruta)
        print(f"--- {nome} ---")
        print(saida)
        print(f"[{nome}] código de saída: {p.returncode} | "
              f"esperado: {'0 (VÁLIDO)' if espera_valido else '1 (INVÁLIDO)'}")
        ok = (p.returncode == 0) == espera_valido
        print(f"[{nome}] {'COMPORTOU COMO ESPERADO' if ok else 'DIVERGIU DA EXPECTATIVA'}")
        print()
        return ok

    todos_ok = True

    # N1: controle positivo
    todos_ok &= rodar_caso(
        "N1 controle positivo",
        [str(BIN_01), str(DESAFIO_01),
         "--comp-esperado", comp_base,
         "--quantizada", str(QUANT_01)],
        espera_valido=True)

    # N2: compromisso esperado adulterado (1 dígito hex)
    comp_falso = ("2" + comp_base[1:]) if comp_base[0] != "2" else ("3" + comp_base[1:])
    todos_ok &= rodar_caso(
        "N2 compromisso adulterado",
        [str(BIN_01), str(DESAFIO_01),
         "--comp-esperado", comp_falso],
        espera_valido=False)

    # N3: pesos de outro bloco contra o desafio do bloco 1
    todos_ok &= rodar_caso(
        "N3 pesos de outro bloco",
        [str(BIN_02), str(DESAFIO_01),
         "--comp-esperado", comp_base],
        espera_valido=False)

    # N4: desafio adulterado — flip de 1 byte no pixel de valor MÁXIMO
    # (byte 5 do float64 LE = bits 40-47 da mantissa; muda o máximo → lo/hi
    #  → compromisso; e o sha256 do arquivo muda → âncora H2 pega)
    # .npy: magic(6) + versão(2) + hlen(2, v1) + header + dados
    bruto = bytearray(DESAFIO_01.read_bytes())
    hlen = int.from_bytes(bruto[8:10], "little")
    inicio_dados = 10 + hlen
    # localizar o pixel de valor máximo pela chave de ordem de bits (int)
    n_pix = (len(bruto) - inicio_dados) // 8
    chave_max, idx_max = -1, -1
    for k in range(n_pix):
        u = int.from_bytes(bruto[inicio_dados + 8 * k: inicio_dados + 8 * k + 8], "little")
        chv = (u | (1 << 63)) if not (u >> 63) else ((~u) & ((1 << 64) - 1))
        if chv > chave_max:
            chave_max, idx_max = chv, k
    off_pixel = inicio_dados + 8 * idx_max + 5     # byte 5 do pixel máximo
    bruto[off_pixel] ^= 0x40                       # XOR em 1 bit da mantissa alta
    desafio_falso = TMP / "desafio_adulterado.npy"
    desafio_falso.write_bytes(bytes(bruto))
    print(f"[N4] pixel máximo no índice {idx_max}; byte 5 XOR 0x40 → "
          f"{desafio_falso.name}")
    todos_ok &= rodar_caso(
        "N4 desafio adulterado (pixel máximo)",
        [str(BIN_01), str(desafio_falso),
         "--comp-esperado", comp_base,
         "--sha256-desafio", hashlib.sha256(DESAFIO_01.read_bytes()).hexdigest()],
        espera_valido=False)

    # N5: swap de 2 pesos no .bin (W[0][0] ↔ W[0][1]: x↔y da unidade 0)
    bruto_bin = bytearray(BIN_01.read_bytes())
    pos_nl = bruto_bin.index(0x0A)
    corpo = pos_nl + 1
    w0 = bytes(bruto_bin[corpo:corpo + 8])
    w1 = bytes(bruto_bin[corpo + 8:corpo + 16])
    bruto_bin[corpo:corpo + 8] = w1
    bruto_bin[corpo + 8:corpo + 16] = w0
    bin_falso = TMP / "pesos_swap.bin"
    bin_falso.write_bytes(bytes(bruto_bin))
    print(f"[N5] swap dos 2 primeiros pesos (canais x↔y da unidade 0) → {bin_falso.name}")
    todos_ok &= rodar_caso(
        "N5 swap de pesos",
        [str(bin_falso), str(DESAFIO_01),
         "--comp-esperado", comp_base],
        espera_valido=False)

    # N6: gate mais rígido — receita ~40 dB com alvo 50 dB
    todos_ok &= rodar_caso(
        "N6 gate mais rígido (alvo 50, receita ~40 dB)",
        [str(BIN_F2_40), str(DESAFIO_F1),
         "--alvo-psnr", "50"],
        espera_valido=False)

    # limpeza dos artefatos temporários (regeneráveis deterministicamente)
    for f in TMP.iterdir():
        f.unlink()
    TMP.rmdir()
    print("artefatos temporários removidos (regeneráveis pelo script)")
    print()

    print("-- RESUMO --")
    print(f"E4a: {len(resultados)} perturbações medidas; compromisso muda a partir "
          f"de δ={min(d for d, _b, m, _g in resultados if m)} LSB Q63")
    print(f"E4b: casos conforme esperado: {'TODOS' if todos_ok else 'HOUVE DIVERGÊNCIA'}")
    print(f"RESULTADO: {'SUÍTE ADVERSARIAL APROVADA (código 0)' if todos_ok else 'REPROVADA (código 1)'}")
    print(f"FIM {agora()}")
    raise SystemExit(0 if todos_ok else 1)


if __name__ == "__main__":
    main()
