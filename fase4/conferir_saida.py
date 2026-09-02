#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conferir_saida.py — PoUW Fase 4 (E1): conferência FORMAL de uma saída do
fase3/verificar_cadeia.py contra a cadeia OFICIAL publicada
(fase3/cadeia_demo/cadeia.json).

Motivação: o verificador imprime, por bloco, o prefixo de 16 caracteres hex do
compromisso RECOMPUTADO na máquina que executa (a igualdade COMPLETA, 64 hex, é
garantida internamente pela checagem C5, que compara o compromisso recomputado
com o registrado e faz o bloco virar INVÁLIDO se divergir em 1 bit), o PSNR
recomputado com 4 decimais e o prefixo do hash_bloco registrado. Este script
extrai esses valores de um output CAPTURADO e os compara com os valores
oficiais do cadeia.json — automatizando a pergunta central da validação
cross-CPU: "os compromissos da SUA máquina bateram com os oficiais?".

Usado na Fase 4 para conferir a saída do dono do repo (Windows) —
fase4/logs/raw/f4_e1_saida_windows.txt — e à disposição de QUALQUER leitor
que queira registrar a própria validação cross-CPU.

Uso (a partir da raiz do repositório):
    python3 fase3/verificar_cadeia.py > minha_saida.txt 2>&1
    python3 fase4/conferir_saida.py minha_saida.txt [--cadeia fase3/cadeia_demo/cadeia.json]

Comparações por bloco (todas devem passar para o código de saída 0):
    1. status        == "VÁLIDO" (certifica C1–C8, incl. C5 bit-a-bit completo)
    2. comp (16 hex) == compromisso oficial [16:]
    3. hash_bloco    == hash_bloco oficial [16:] (o JSON do leitor é o oficial)
    4. PSNR (4 dec)  == psnr_verificacao oficial formatado a 4 decimais
                       (e também == psnr_treino oficial a 4 decimais)
Além disso: nº de blocos = n_blocos da spec e a linha RESULTADO do output.

LIMITAÇÃO declarada: este script confere no NÍVEL IMPRESSO (prefixos 16 hex +
PSNR 4 decimais). A igualdade bit-a-bit completa dos compromissos não é
re-derivada aqui — é certificada pela checagem C5 DENTRO do verificador que
rodou na máquina de origem, cujo veredito por bloco (VÁLIDO) este script lê.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Formato impresso por verificar_cadeia.py (f-string do verbose):
#   [bloco {i}] {status} ({t:.6f} s) | PSNR {psnr:.4f} dB | comp {comp[:16]}… | hash_bloco {hash[:16]}…
# As reticências são o caractere U+2026 (…), como no verificador.
LINHA_BLOCO = re.compile(
    r"^\[bloco (\d+)\] (VÁLIDO|INVÁLIDO) \((\d+\.\d+) s\) \| PSNR (\d+\.\d+) dB "
    r"\| comp ([0-9a-f]{16})… \| hash_bloco ([0-9a-f]{16})…$"
)
LINHA_RESUMO = re.compile(r"^Blocos verificados: (\d+) \| válidos: (\d+)$")
LINHA_RESULTADO = re.compile(r"^RESULTADO: (CADEIA VÁLIDA|CADEIA INVÁLIDA) \(código (\d+)\)$")


def agora_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def main():
    ap = argparse.ArgumentParser(
        description="Conferência de saída do verificar_cadeia.py contra a cadeia oficial (PoUW Fase 4)"
    )
    ap.add_argument("saida", help="arquivo com o output capturado de fase3/verificar_cadeia.py")
    ap.add_argument("--cadeia", default="fase3/cadeia_demo/cadeia.json",
                    help="cadeia.json oficial (padrão: fase3/cadeia_demo/cadeia.json)")
    args = ap.parse_args()

    caminho_saida = Path(args.saida)
    if not caminho_saida.is_absolute():
        caminho_saida = Path.cwd() / caminho_saida
    caminho_cadeia = Path(args.cadeia)
    if not caminho_cadeia.is_absolute():
        caminho_cadeia = RAIZ / caminho_cadeia

    print("== conferir_saida.py — PoUW Fase 4: conferência de output vs cadeia oficial ==")
    print(f"INICIO {agora_utc()}")
    print(f"Arquivo de saída conferido: {caminho_saida}")
    print(f"Cadeia oficial: {caminho_cadeia}")

    texto = caminho_saida.read_text(encoding="utf-8")
    cadeia = json.loads(caminho_cadeia.read_text(encoding="utf-8"))
    n_esperado = cadeia["n_blocos"]
    print(f"Spec: {cadeia['spec']} | blocos oficiais: {n_esperado} | alvo PSNR: {cadeia['alvo_psnr']} dB "
          f"| prefixo: {cadeia['prefixo_bits']} bits | B={cadeia['bits_quant']}")
    print()

    # ---------- extração das linhas do output ----------
    blocos_lidos = {}
    resumo = None
    resultado = None
    n_linhas_bloco = 0
    for linha in texto.splitlines():
        m = LINHA_BLOCO.match(linha.strip())
        if m:
            n_linhas_bloco += 1
            i = int(m.group(1))
            blocos_lidos[i] = {
                "status": m.group(2), "tempo_s": m.group(3), "psnr": m.group(4),
                "comp": m.group(5), "hash_bloco": m.group(6),
            }
            continue
        m = LINHA_RESUMO.match(linha.strip())
        if m:
            resumo = (int(m.group(1)), int(m.group(2)))
            continue
        m = LINHA_RESULTADO.match(linha.strip())
        if m:
            resultado = (m.group(1), int(m.group(2)))

    if n_linhas_bloco == 0:
        print("ERRO: nenhuma linha '[bloco N] …' reconhecida no arquivo de saída.")
        print("O arquivo deve conter o output integral de fase3/verificar_cadeia.py (modo verboso).")
        raise SystemExit(1)

    # ---------- conferência por bloco ----------
    cab = f"{'bloco':>5} | {'status':8} | {'PSNR':9} | {'comp (16 hex)':17} | {'hash_bloco (16 hex)':19} | veredito"
    print(cab)
    print("-" * len(cab))
    todos_ok = True
    for b in cadeia["blocos"]:
        i = b["bloco"]
        lido = blocos_lidos.get(i)
        if lido is None:
            print(f"{i:>5} | {'—':8} | {'—':9} | {'—':17} | {'—':19} | FALTA (não impresso no output)")
            todos_ok = False
            continue

        psnr_oficial_v = f"{b['psnr_verificacao']:.4f}"
        psnr_oficial_t = f"{b['psnr_treino']:.4f}"
        comp_oficial = b["compromisso"][:16]
        hash_oficial = b["hash_bloco"][:16]

        ok_status = lido["status"] == "VÁLIDO"
        ok_comp = lido["comp"] == comp_oficial
        ok_hash = lido["hash_bloco"] == hash_oficial
        ok_psnr = lido["psnr"] == psnr_oficial_v and lido["psnr"] == psnr_oficial_t
        ok = ok_status and ok_comp and ok_hash and ok_psnr
        todos_ok = todos_ok and ok

        detalhes = []
        if not ok_status:
            detalhes.append(f"status={lido['status']} (esperado VÁLIDO — C5/C1–C8 falharam lá)")
        if not ok_comp:
            detalhes.append(f"comp {lido['comp']} != oficial {comp_oficial}")
        if not ok_hash:
            detalhes.append(f"hash {lido['hash_bloco']} != oficial {hash_oficial}")
        if not ok_psnr:
            detalhes.append(f"PSNR {lido['psnr']} != oficial verif {psnr_oficial_v} / treino {psnr_oficial_t}")
        veredito = "CONFERE" if ok else "DIVERGE: " + "; ".join(detalhes)

        print(f"{i:>5} | {lido['status']:8} | {lido['psnr']:9} | {lido['comp'][:16]:17} | "
              f"{lido['hash_bloco'][:16]:19} | {veredito}")

    # blocos impressos no output que não existem na cadeia oficial
    extras = sorted(set(blocos_lidos) - {b["bloco"] for b in cadeia["blocos"]})
    if extras:
        todos_ok = False
        print(f"AVISO: o output contém blocos que não existem na cadeia oficial: {extras}")

    # ---------- conferência do sumário ----------
    print()
    if resumo is not None:
        print(f"SUMÁRIO do output: blocos={resumo[0]}, válidos={resumo[1]} "
              f"(esperado: {n_esperado}, {n_esperado})")
        if resumo != (n_esperado, n_esperado):
            todos_ok = False
    else:
        print("AVISO: linha 'Blocos verificados: N | válidos: M' não encontrada no output.")
        todos_ok = False
    if resultado is not None:
        print(f"RESULTADO do output: {resultado[0]} (código {resultado[1]})")
        if resultado != ("CADEIA VÁLIDA", 0):
            todos_ok = False
    else:
        print("AVISO: linha 'RESULTADO: … (código N)' não encontrada no output.")
        todos_ok = False

    # ---------- veredito ----------
    print()
    print("NOTA: a igualdade COMPLETA (64 hex) de cada compromisso é certificada pela checagem C5 "
          "do verificador\nque rodou na máquina de origem (status VÁLIDO por bloco); este script "
          "confere o nível impresso\n(prefixos 16 hex + PSNR a 4 decimais) contra o cadeia.json oficial.")
    print(f"RESULTADO DA CONFERÊNCIA: {'OK — 100% dos blocos conferem' if todos_ok else 'DIVERGÊNCIA ENCONTRADA'} "
          f"(código {0 if todos_ok else 1})")
    print(f"FIM {agora_utc()}")
    raise SystemExit(0 if todos_ok else 1)


if __name__ == "__main__":
    main()
