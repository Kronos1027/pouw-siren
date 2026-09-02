#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checagem_retreino.py — checagem auxiliar (Etapa 2, fora do protocolo das 3 seeds).

Compara tensor a tensor os pesos de duas execucoes INDEPENDENTES de treinar.py
sobre o mesmo desafio (receita_b0f90ffe.pt vs _retreino_check.pt) para determinar
se o treino e bit-a-bit deterministico nesta maquina/ambiente.
Tambem reporta os hashes dos dois arquivos .pt (que diferem por causa do
timestamp do conteiner zip — ver checagem_torchsave.py).
"""

import hashlib

import torch


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


A = "receita_b0f90ffe.pt"
B = "_retreino_check.pt"

print("hash do arquivo", A, ":", sha256_arquivo(A))
print("hash do arquivo", B, ":", sha256_arquivo(B))

ra = torch.load(A, map_location="cpu", weights_only=False)
rb = torch.load(B, map_location="cpu", weights_only=False)

sa, sb = ra["estado"], rb["estado"]
print("mesmas chaves de estado:", sorted(sa.keys()) == sorted(sb.keys()))

todas_iguais = True
max_diff = 0.0
for k in sorted(sa.keys()):
    ig = bool(torch.equal(sa[k], sb[k]))
    d = float((sa[k].float() - sb[k].float()).abs().max())
    todas_iguais = todas_iguais and ig
    max_diff = max(max_diff, d)
    print(f"  {k}: bit-a-bit identico={ig} | max|diff|={d:.3e}")

print("TODOS os tensores bit-a-bit identicos:", todas_iguais)
print("max diff global entre pesos:", f"{max_diff:.3e}")
print("meta a (epocas, psnr, parada):", ra["meta"]["epocas"], ra["meta"]["psnr_final_treino"], ra["meta"]["motivo_parada"])
print("meta b (epocas, psnr, parada):", rb["meta"]["epocas"], rb["meta"]["psnr_final_treino"], rb["meta"]["motivo_parada"])
