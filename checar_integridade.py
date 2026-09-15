#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checar_integridade.py — PoUW-SIREN: checagem de integridade dos artefatos
publicados (Fases 1-6), equivalente MULTIPLATAFORMA do checar_integridade.sh.

Recalcula o SHA-256 de todos os artefatos ancorados do repositorio e compara
com os valores publicados nos arquivos de ancoras, no formato do sha256sum:

  hashes.sha256               (Fase 1)
  fase2/hashes_fase2.sha256   (Fase 2)
  fase3/hashes_fase3.sha256   (Fase 3)
  fase4/hashes_fase4.sha256   (Fase 4)
  fase5/hashes_fase5.sha256   (Fase 5 — 45 ancoras apos a v1.0.1)
  fase6/hashes_fase6.sha256   (Fase 6 — validacao externa Windows)

100% stdlib (hashlib/os/sys) — roda em qualquer Python 3, SEM numpy/torch.
A saida e DELIBERADAMENTE ASCII pura (sem acentos): funciona em qualquer
console (cp1252, cp850, UTF-8) sem configurar PYTHONIOENCODING. Tolerante a
CRLF nos arquivos de ancoras (o valor hash nunca e afetado: os ARQUIVOS
verificados sao lidos em binario).

Nota: este script nao ancora a si mesmo (mesma decisao documentada do
checar_integridade.sh: o verificador nao verifica a si proprio); sua
integridade e coberta pela conferencia do clone via git + pela ancora em
fase6/hashes_fase6.sha256.

Uso (a partir de qualquer diretorio; resolve a raiz sozinho):
    python checar_integridade.py

Codigo de saida: 0 = todas as ancoras conferem; 1 = qualquer divergencia.
"""

import hashlib
import os
import sys

ARQUIVOS_ANCORAS = [
    ("Fase 1", "hashes.sha256"),
    ("Fase 2", "fase2/hashes_fase2.sha256"),
    ("Fase 3", "fase3/hashes_fase3.sha256"),
    ("Fase 4", "fase4/hashes_fase4.sha256"),
    ("Fase 5", "fase5/hashes_fase5.sha256"),
    ("Fase 6", "fase6/hashes_fase6.sha256"),
]


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 16), b""):
            h.update(bloco)
    return h.hexdigest()


def main():
    raiz = os.path.dirname(os.path.abspath(__file__))
    os.chdir(raiz)  # mesmo comportamento do checar_integridade.sh

    print("== PoUW-SIREN - checagem de integridade (SHA-256) ==")
    print("(equivalente Python do checar_integridade.sh; multiplataforma)")
    print()

    total = 0
    ok = 0
    falhas = []

    for rotulo, arq_ancoras in ARQUIVOS_ANCORAS:
        if not os.path.isfile(arq_ancoras):
            print("[%s] ARQUIVO DE ANCORAS AUSENTE: %s" % (rotulo, arq_ancoras))
            falhas.append("%s (arquivo de ancoras ausente)" % arq_ancoras)
            continue
        n_grupo = 0
        ok_grupo = 0
        with open(arq_ancoras, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if (not linha) or linha.startswith("#"):
                    continue  # comentarios/linhas vazias, como o sha256sum -c
                partes = linha.split(None, 1)
                if len(partes) != 2:
                    falhas.append("%s: linha malformada: %r" % (arq_ancoras, linha))
                    continue
                esperado, caminho = partes[0], partes[1].strip()
                if caminho.startswith("*"):  # modo binario do sha256sum
                    caminho = caminho[1:]
                n_grupo += 1
                total += 1
                if not os.path.isfile(caminho):
                    falhas.append("%s: arquivo AUSENTE" % caminho)
                    continue
                obtido = sha256_arquivo(caminho)
                if obtido == esperado.lower():
                    ok_grupo += 1
                    ok += 1
                else:
                    falhas.append("%s:\n    esperado %s\n    obtido   %s"
                                  % (caminho, esperado, obtido))
        print("[%s] %d/%d OK  (%s)" % (rotulo, ok_grupo, n_grupo, arq_ancoras))

    print()
    print("TOTAL: %d/%d ancoras OK" % (ok, total))

    if falhas:
        print()
        print("DIVERGENCIAS (%d):" % len(falhas))
        for f_ in falhas:
            print("  - " + f_)
        print()
        print("Dica (Windows): se MUITOS arquivos divergirem de uma vez, a causa")
        print("mais comum e final de linha CRLF introduzido pelo clone. Corrija com:")
        print("    git config core.autocrlf false")
        print("    git checkout-index --force --all")
        print("e rode este script de novo.")

    print()
    print("RESULTADO: " + ("INTEGRO (codigo 0)" if not falhas
                           else "DIVERGENTE (codigo 1)"))
    raise SystemExit(0 if not falhas else 1)


if __name__ == "__main__":
    main()
