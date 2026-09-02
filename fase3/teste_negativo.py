#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teste_negativo.py — PoUW Fase 3: prova que o verificador NÃO é "yes-man".

Um verificador que só aceita não prova nada. Este script ADULTERA a cadeia
oficial de 5 formas distintas (cada uma numa CÓPIA temporária; os originais
nunca são tocados), roda verificar_cadeia.py como SUBPROCESSO em cada cópia e
confere que:
  (a) o código de saída é 1 (rejeitou);
  (b) o bloco esperado é apontado como INVÁLIDO;
  (c) as checagens que FALHAM incluem as esperadas (declaradas abaixo).

ADULTERAÇÕES (modo → bloco → checagens esperadas):
  compromisso   : bloco 4 → compromisso do header trocado     → C5 + C8
  nonce         : bloco 4 → nonce incrementado                 → C8
  prev          : bloco 5 → prev apontando para outro hash     → C1 + C2
  receita       : bloco 4 → receita_04.pt sobrescrito c/ 05    → C3 + C4 + C5 + C6 + C7
  comp_desafio  : bloco 2 → comp_desafio do registro trocado   → C2
  desafio       : bloco 2 → campo[0,0] += 0.001 no .npy        → C3
NOTA DE DESIGN (aprendida na 1ª execução, log preservado em
f3_e4_negativo_EXECUCAO1_EXPECTATIVA_ERRADA.txt): C2 compara o desafio
REGENERADO da seed contra o comp_desafio REGISTRADO — adulterar o ARQUIVO
.npy não muda o registro, então quem pega essa fraude é a C3 (sha256 do
arquivo). O par C2+C3 cobre as duas fraudes complementares: registro falso
(C2) e arquivo divergente do registro (C3). Por isso o modo 'desafio'
espera {C3} e o modo 'comp_desafio' (novo) espera {C2} isolada. (A C7 do
modo 'desafio' não dispara por construção: 1 pixel em 4096 com delta 0.001
pouco eleva o RMSE — declarado; quem pega a fraude é a C3.)

Uso (a partir da raiz do repositório):
    python3 fase3/teste_negativo.py [fase3/cadeia_demo]
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # desafio.py (não usado diretamente, mantém consistência)

SPEC = "pouw-cadeia-demo-v1"


def agora_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


RE_LINHA_BLOCO = re.compile(r"^\[bloco (\d+)\] (VÁLIDO|INVÁLIDO) \(([0-9.]+) s\)(.*)$", re.MULTILINE)
RE_CODIGO = re.compile(r"código (\d)")


def adulterar(modo, dir_tmp):
    """Aplica a adulteração na cópia. Retorna (bloco_esperado, checagens_esperadas)."""
    caminho_json = dir_tmp / "cadeia.json"
    with open(caminho_json, "r", encoding="utf-8") as f:
        cadeia = json.load(f)
    blocos = cadeia["blocos"]
    por_indice = {b["bloco"]: b for b in blocos}

    if modo == "compromisso":
        b = por_indice[4]
        # troca o primeiro caractere hex por um diferente
        novo = ("0" if b["compromisso"][0] != "0" else "1") + b["compromisso"][1:]
        b["compromisso"] = novo
        esperado = (4, {"C5", "C8"})
    elif modo == "nonce":
        b = por_indice[4]
        b["nonce"] = int(b["nonce"]) + 1
        esperado = (4, {"C8"})
    elif modo == "prev":
        b = por_indice[5]
        b["prev"] = por_indice[2]["hash_bloco"]  # aponta para o bloco errado
        esperado = (5, {"C1", "C2"})
    elif modo == "receita":
        b = por_indice[4]
        shutil.copy2(dir_tmp / "receita_05.pt", dir_tmp / "receita_04.pt")
        esperado = (4, {"C3", "C4", "C5", "C6", "C7"})
    elif modo == "comp_desafio":
        b = por_indice[2]
        # troca o primeiro caractere hex do comp_desafio REGISTRADO
        novo = ("0" if b["comp_desafio"][0] != "0" else "1") + b["comp_desafio"][1:]
        b["comp_desafio"] = novo
        esperado = (2, {"C2"})
    elif modo == "desafio":
        b = por_indice[2]
        cam = dir_tmp / b["arquivo_desafio"]
        campo = np.load(cam)
        campo[0, 0] = float(campo[0, 0]) + 0.001
        np.save(cam, campo)
        esperado = (2, {"C3"})
    else:
        raise ValueError(f"modo desconhecido: {modo}")

    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(cadeia, f, indent=2, ensure_ascii=False)
    return esperado


def main():
    ap = argparse.ArgumentParser(description="Teste negativo do verificador da cadeia — PoUW Fase 3")
    ap.add_argument("dir_cadeia", nargs="?", default="fase3/cadeia_demo")
    args = ap.parse_args()

    dir_cadeia = Path(args.dir_cadeia)
    if not dir_cadeia.is_absolute():
        dir_cadeia = RAIZ / dir_cadeia
    dir_tmp = RAIZ / "fase3" / ".tmp_negativo"

    print("== teste_negativo.py — PoUW Fase 3 (o verificador REJEITA fraudes?) ==")
    print(f"INICIO {agora_utc()}")
    print(f"Cadeia oficial: {dir_cadeia} (intocada — adulterações em cópias temporárias)")
    print("Cada modo: cópia → adulteração → verificar_cadeia.py (subprocesso frio) → espera código 1 + bloco + checagens")
    t0 = time.perf_counter()

    modos = ["compromisso", "nonce", "prev", "receita", "comp_desafio", "desafio"]
    rejeicoes_ok = 0
    for modo in modos:
        print(f"\n########## MODO: {modo} ##########")
        if dir_tmp.exists():
            shutil.rmtree(dir_tmp)
        shutil.copytree(dir_cadeia, dir_tmp)
        bloco_esperado, checagens_esperadas = adulterar(modo, dir_tmp)

        r = subprocess.run(
            [sys.executable, "fase3/verificar_cadeia.py", "fase3/.tmp_negativo"],
            cwd=str(RAIZ), capture_output=True, text=True,
        )
        # imprime o essencial do subprocesso (o log bruto completo vai ao stdout deste script via tee)
        for linha in r.stdout.splitlines():
            if linha.startswith("[bloco") or linha.startswith("RESULTADO") or linha.startswith("    C"):
                print(f"  | {linha}")
        if r.returncode not in (0, 1):
            print("-- STDERR do subprocesso --")
            print(r.stderr)
        m_cod = RE_CODIGO.search(r.stdout)
        cod = m_cod.group(1) if m_cod else f"?{r.returncode}"
        linhas = RE_LINHA_BLOCO.findall(r.stdout)
        inv_alidos = {int(n): detalhe for n, st, _t, detalhe in linhas if st == "INVÁLIDO"}
        falhas_no_bloco = set()
        if bloco_esperado in inv_alidos:
            detalhe = inv_alidos[bloco_esperado]
            falhas_no_bloco = set(re.findall(r"(C\d)\(", detalhe))

        aceito = (cod == "1")
        bloco_certo = (bloco_esperado in inv_alidos)
        checagens_certas = checagens_esperadas.issubset(falhas_no_bloco)
        passou = aceito and bloco_certo and checagens_certas
        rejeicoes_ok += int(passou)
        print(f"  código de saída: {cod} (esperado 1) | bloco inválido apontado: {sorted(inv_alidos)} (esperado [{bloco_esperado}])")
        print(f"  checagens falhadas no bloco {bloco_esperado}: {sorted(falhas_no_bloco)} ⊇ esperadas {sorted(checagens_esperadas)}")
        print(f"  RESULTADO DO MODO: {'REJEITOU CORRETAMENTE' if passou else 'FALHOU (verificador aceitou ou apontou errado)'}")

    if dir_tmp.exists():
        shutil.rmtree(dir_tmp)

    print(f"\n======== TESTE NEGATIVO: {rejeicoes_ok}/{len(modos)} rejeições corretas ========")
    print(f"Tempo total: {time.perf_counter() - t0:.3f} s (6 subprocessos frios, ~1 s de import cada)")
    print(f"FIM {agora_utc()}")
    raise SystemExit(0 if rejeicoes_ok == len(modos) else 1)


if __name__ == "__main__":
    main()
