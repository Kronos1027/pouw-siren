#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
siren_numpy.py — PoUW Fase 2: forward pass da SIREN implementado EM NUMPY.

Por quê: o forward do verificar.py da Fase 1 usa torch (oneDNN/BLAS do wheel).
Implementar o MESMO cálculo em NumPy (OpenBLAS) e em versões com ordem de
soma FORÇADA em blocos gera caminhos aritméticos REALMENTE diferentes na
mesma máquina — um proxy honesto e controlável da variação de arredondamento
que ocorre entre CPUs/BLAS heterogêneos (a diverência medida pelo usuário na
validação da Fase 1 foi exatamente dessa classe: 7.15e-07 no último bit).

Suposições (válidas para a arquitetura da Fase 1, lidas da receita):
  Sequential = Linear, Sine, Linear, Sine, Linear, Sine, Linear
  → chaves do state_dict: "0.weight/0.bias", "2.…", "4.…", "6.…"
  (camadas Sine não têm parâmetros; omega_0 vem da receita).
  O ÚLTIMO Linear não é seguido de ativação (saída linear).

Este módulo NÃO substitui o verificador oficial da Fase 2 (verificar_fase2.py,
torch float64); ele serve aos experimentos de robustez (experimento_caminhos.py,
experimento_ruido.py).
"""

import numpy as np


def carregar_pesos_numpy(caminho_pt):
    """Carrega a receita .pt (via torch) e devolve (receita, pesos_numpy).

    torch é usado APENAS para deserializar o .pt; todo o forward é NumPy.
    """
    import torch  # import tardio e proposital (apenas para o load)

    try:
        receita = torch.load(caminho_pt, map_location="cpu", weights_only=False)
    except TypeError:  # torch muito antigo sem weights_only
        receita = torch.load(caminho_pt, map_location="cpu")
    pesos = {k: v.detach().cpu().numpy() for k, v in receita["estado"].items()}
    return receita, pesos


def _matmul(x, W, b, blocos=0):
    """x @ W.T + b, com ordem de soma opcionalmente forçada em blocos.

    blocos=0 (default): GEMM direto (ordem interna do BLAS).
    blocos=k: a dimensão de ENTRADA é fatiada em blocos de k colunas; cada
    parcial é um GEMM pequeno e os parciais são somados SEQUENCIALMENTE —
    uma ordem de redução diferente do GEMM único (proxy de mudança de
    largura de vetor SIMD / blocking do BLAS). Determinístico por construção.
    """
    n_in = W.shape[1]
    if blocos <= 0 or blocos >= n_in:
        return x @ W.T + b
    acc = None
    for i in range(0, n_in, blocos):
        j = min(i + blocos, n_in)
        p = x[:, i:j] @ W[:, i:j].T
        acc = p if acc is None else acc + p
    return acc + b


def forward_numpy(coords, pesos, omega_0=30.0, dtype=np.float64, blocos=0):
    """Forward SIREN em NumPy.

    coords : (N, 2) float (será convertido para `dtype`)
    pesos  : dict do state_dict (pesos float32 da receita; convertidos com
             .astype(dtype) — float32→float64 é exato)
    dtype  : np.float32 ou np.float64
    blocos : 0 = GEMM direto; k>0 = soma em blocos de k (ver _matmul)
    Retorna: (N,) ou (N, 1) conforme a última camada — chamador dá reshape.
    """
    x = np.asarray(coords, dtype=dtype)
    lineares = sorted(int(k.split(".")[0]) for k in pesos if k.endswith(".weight"))
    n_lin = len(lineares)
    for idx, li in enumerate(lineares):
        W = pesos[f"{li}.weight"].astype(dtype)
        b = pesos[f"{li}.bias"].astype(dtype)
        x = _matmul(x, W, b, blocos)
        if idx < n_lin - 1:
            x = np.sin(omega_0 * x)
    return x


def grade(size, dtype=np.float64):
    """Grade do desafio.py/treinar.py/verificar.py da Fase 1.

    dtype=np.float32: cópia EXATA do bloco compartilhado da Fase 1
      (stack float64 → cast float32 → ×2 − 1 em float32).
    dtype=np.float64: o mesmo pipeline mantido em float64 (caminho da Fase 2).
    """
    x, y = np.meshgrid(np.linspace(0, 1, size), np.linspace(0, 1, size))
    coords = np.stack([x.ravel(), y.ravel()], axis=1)
    return coords.astype(dtype) * 2.0 - 1.0
