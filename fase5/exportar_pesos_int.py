#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exportar_pesos_int.py — PoUW Fase 5: exporta os pesos float32 da receita .pt
para o FORMATO CANÔNICO DE PESOS INTEIROS da pouw-int-v1 (arquivo .bin:
header ASCII + int64 little-endian com sinal em Q63).

O exportador roda NO LADO DO MINERADOR: precisa de torch APENAS para
desserializar o .pt (o verificador frio nunca precisa de torch — lê o .bin).
A conversão float32→Q63 é feita POR BITS, sem nenhuma aritmética de ponto
flutuante: cada float32 é um racional diádico exato (mantissa·2^exp); os
bits são decompostos e valor·2^63 é arredondado half-even quando não é
inteiro. Portanto o .bin é FUNÇÃO DETERMINÍSTICA dos bytes do .pt:
re-exportar produz bytes idênticos (verificado no smoke e no E3).

Restrições declaradas (spec):
  - |peso| < 1 (para caber em int64 Q63; máximo REAL medido nas 18 receitas
    oficiais: 0,501647 — folga de 2×);
  - omega_0 inteiro (medido: 30);
  - máquina little-endian para ler os bytes nativos do tensor (x86/ARM LE;
    o .bin de SAÍDA é explicitamente little-endian e portável).

Uso:
    python3 fase5/exportar_pesos_int.py <receita.pt> <saida.bin>
"""

import argparse
import hashlib
import platform
import sys
import time

import torch

from siren_int import Q, VERSAO_SPEC, rhe


def _f32_bits_para_q63(u):
    """Bits float32 → Q63 (half-even). SEM aritmética de float."""
    sinal = u >> 31
    e = (u >> 23) & 0xFF
    frac = u & 0x7FFFFF
    if e == 0xFF:
        raise ValueError("peso Inf/NaN não suportado pela pouw-int-v1")
    if e == 0:
        if frac == 0:
            return 0
        q = rhe(frac, 149 - Q)            # subnormal: frac·2^(-149+Q)... ver abaixo
    else:
        num = (1 << 23) | frac
        exp_efetivo = e - 127 - 23 + Q    # valor·2^63 = num·2^exp_efetivo
        if exp_efetivo >= 0:
            q = num << exp_efetivo
        else:
            q = rhe(num, -exp_efetivo)
    return -q if sinal else q


def tensor_para_q63_lista(t):
    """Tensor float32 (CPU) → lista de inteiros Q63, ordem row-major."""
    if t.dtype != torch.float32:
        raise ValueError(f"esperado tensor float32, recebi {t.dtype}")
    if sys.byteorder != "little":
        raise ValueError("exportador declarado para máquina little-endian")
    bruto = t.detach().cpu().contiguous().numpy().tobytes()
    if len(bruto) % 4:
        raise ValueError("tamanho de tensor não múltiplo de 4 bytes")
    return [_f32_bits_para_q63(int.from_bytes(bruto[i:i + 4], "little"))
            for i in range(0, len(bruto), 4)]


def exportar(caminho_pt, caminho_saida):
    """Exporta a receita .pt → .bin canônico. Retorna (sha256, header, n_pesos)."""
    try:
        receita = torch.load(caminho_pt, map_location="cpu", weights_only=False)
    except TypeError:
        receita = torch.load(caminho_pt, map_location="cpu")
    arq = receita["arquitetura"]
    camadas = [int(arq["dim_entrada"])] + [int(x) for x in arq["ocultas"]] + [int(arq["dim_saida"])]
    omega = float(arq["omega_0"])
    if not omega.is_integer():
        raise ValueError(f"omega_0={omega} não é inteiro (exigência da pouw-int-v1)")
    grade = int(receita["grade"])
    estado = receita["estado"]
    lineares = sorted({int(k.split(".")[0]) for k in estado if k.endswith(".weight")})

    Ws, bs = [], []
    for li in lineares:
        Ws.append(tensor_para_q63_lista(estado[f"{li}.weight"]))
        bs.append(tensor_para_q63_lista(estado[f"{li}.bias"]))

    n_pesos = 0
    for idx, (o, i) in enumerate(zip(camadas[1:], camadas[:-1])):
        if len(Ws[idx]) != o * i or len(bs[idx]) != o:
            raise ValueError(
                f"camada {idx}: pesos {len(Ws[idx])} (esperado {o * i}) ou "
                f"vieses {len(bs[idx])} (esperado {o}) divergem da arquitetura")
        n_pesos += o * i + o

    header = (f"{VERSAO_SPEC}|Q={Q}|camadas={','.join(str(c) for c in camadas)}"
              f"|omega_0={int(omega)}|grade={grade}\n")
    with open(caminho_saida, "wb") as f:
        f.write(header.encode("ascii"))
        for W, b in zip(Ws, bs):
            for v in W:
                f.write(v.to_bytes(8, "little", signed=True))   # estoura se |v| >= 2^63
            for v in b:
                f.write(v.to_bytes(8, "little", signed=True))

    h = hashlib.sha256()
    with open(caminho_saida, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest(), header.strip(), n_pesos


def main():
    ap = argparse.ArgumentParser(
        description="Exportador de pesos inteiros Q63 — PoUW Fase 5 (pouw-int-v1)")
    ap.add_argument("receita", help="arquivo .pt da receita treinada")
    ap.add_argument("saida", help="arquivo .bin de saída (pesos inteiros canônicos)")
    args = ap.parse_args()

    t_ini = time.perf_counter()
    sha, header, n_pesos = exportar(args.receita, args.saida)
    t_fim = time.perf_counter()

    print("== exportar_pesos_int.py — PoUW Fase 5 (pesos inteiros canônicos Q63) ==")
    print(f"Python {platform.python_version()} | PyTorch {torch.__version__}")
    print(f"Receita: {args.receita}")
    print(f"Saída  : {args.saida}")
    print(f"Header : {header}")
    print(f"Pesos+vieses exportados: {n_pesos}")
    print(f"Tempo (carga + conversão por bits + gravação): {t_fim - t_ini:.6f} s")
    print(f"SHA-256 do .bin (âncora conferível com sha256sum): {sha}")


if __name__ == "__main__":
    main()
