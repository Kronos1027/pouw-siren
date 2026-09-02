#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checagem_torchsave.py — checagem auxiliar (Etapa 2, fora do protocolo das 3 seeds).

Objetivo: determinar se torch.save() produz bytes identicos ao salvar o MESMO
objeto duas vezes (suspeita: o conteiner zip embute timestamp, o que tornaria
o hash do ARQUIVO dependente do momento do salvamento, mesmo com pesos iguais).
"""

import hashlib
import time

import torch


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


ger = torch.Generator().manual_seed(7)
d = {
    "0.weight": torch.randn(128, 128, generator=ger),
    "0.bias": torch.zeros(128),
    "meta": "checagem-torchsave-v1",
}

torch.save(d, "_check1.pt")
time.sleep(1.2)  # garante timestamps diferentes se o zip embutir data/hora
torch.save(d, "_check2.pt")

h1 = sha256_arquivo("_check1.pt")
h2 = sha256_arquivo("_check2.pt")
print("hash SHA-256 de _check1.pt:", h1)
print("hash SHA-256 de _check2.pt:", h2)
print("bytes dos arquivos identicos:", h1 == h2)

r1 = torch.load("_check1.pt", map_location="cpu", weights_only=False)
r2 = torch.load("_check2.pt", map_location="cpu", weights_only=False)
print("conteudo (tensores) identico apos reload:", torch.equal(r1["0.weight"], r2["0.weight"]))
