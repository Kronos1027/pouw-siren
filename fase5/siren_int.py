#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
siren_int.py — PoUW Fase 5: especificação CANÔNICA do caminho de verificação
100% INTEIRO (pouw-int-v1): forward + quantização + gate de qualidade + hash
usando APENAS inteiros de precisão arbitrária — sem BLAS, sem libm, sem
numpy, sem torch, sem NENHUMA operação de ponto flutuante.

MOTIVAÇÃO (resíduo teórico das fases anteriores):
  A pouw-quant-v1 (Fase 2) padronizou a ARITMÉTICA de quantização (float64
  escalar, IEEE-754 corretamente arredondada) e o forward em float64. O
  compromisso resultante foi bit-a-bit idêntico entre Linux/Xeon/OpenBLAS e
  Windows/do dono (Fase 4, 8/8 blocos) — MAS a garantia é empírica: o
  forward float64 ainda depende (a) da ORDEM DE SOMA interna do GEMM do BLAS
  e (b) do sin() da libm, que a norma não exige corretamente arredondado
  (a checagem C2 da Fase 3 declara tolerância a "~1 ulp de libm"). A margem
  da grade B=16 absorve esse resíduo com ~5 ordens de grandeza (medido em
  F2/E2), porém por MARGEM, não por CONSTRUÇÃO.
  A pouw-int-v1 elimina a CLASSE inteira do risco: nenhuma operação de ponto
  flutuante existe no caminho. Uma máquina sem FPU/BLAS/libm, ou uma
  re-implementação em C com __int128, chega ao MESMO hash bit-a-bit.

ESPECIFICAÇÃO pouw-int-v1 (minerador e verificador devem seguir À RISCA):

  FORMATO DOS NÚMEROS
    Q = 63 bits fracionários (fixed-point Q63, inteiro COM sinal de precisão
    arbitrária; valor real = q / 2^63). Peso, ativação, pré-ativação,
    argumento do seno e reconstrução vivem todos em Q63. Acumuladores de
    camada vivem em Q126 (produto exato Q63×Q63) e são arredondados UMA vez
    por camada.

  ARREDONDAMENTOS (todos pinados, todos half-even = "arredondar-meio-para-par",
    a MESMA regra de np.rint usada pela pouw-quant-v1):
    rhe(x, k)      : round-half-even(x / 2^k) para inteiros
    divround(a, b) : round-half-even(a / b) para inteiros, b > 0
    Divisão por potência de 2 nunca ocorre com sinal ambíguo: sempre via rhe.

  CONSTANTES PINADAS
    PI_DEC (50 dígitos decimais, string ASCII no código): π exato até 1e-50;
    C_MEIO_PI = divround(PI·2^62, 10^49)  (π/2 em Q63, erro ≤ 2^-64).
    Coeficientes de Taylor: 1/n! são racionais EXATOS; em Q63 via
    divround(2^63, n!) com sinais alternados (ver código). Zero aproximação
    não-pinada entra na spec.

  FORWARD (arquitetura SIREN da F1: Lineares com sin(omega_0·x) entre eles;
    ÚLTIMO Linear sem ativação)
    1. Grade de entrada: coords (x, y) = (2j-(S-1))/(S-1) para j=0..S-1
       (racional EXATO — a F1 usa linspace(0,1,S)*2-1, cujo valor real é
       exatamente esse), convertida a Q63 com divround. Canal 0 = x da
       COLUNA, canal 1 = y da LINHA (mesma ordem do meshgrid/ravel da F1).
    2. Por camada ℓ com pesos W (Q63) e viés b (Q63):
         acc_j = (b_j << 63) + soma_i W[j][i]·chan_i     [Q126, EXATA —
                                                          soma em QUALQUER
                                                          ordem dá o MESMO
                                                          inteiro]
         z_j   = rhe(acc_j, 63)                          [Q63, 1 arredondamento]
    3. Ativação (camadas ocultas): a_j = sin_q(omega_0 · z_j)
       (omega_0 inteiro do header; multiplicação exata; sin_q abaixo).
    4. Última camada: R = z (Q63), sem ativação. Orem row-major (i·S + j).

  sin_q(A) — seno em Q63 sem floats:
    k = divround(A, C_MEIO_PI); r = A − k·C_MEIO_PI  (|r| ≤ π/4 + 2^-64;
    |k| ≤ 32 medido nas 18 receitas oficiais — max|omega_0·z| = 49,89)
    u = rhe(r·r, 63)
    sin(r) = r·(c1 + u·(c3 + u·(c5 + … + u·c19)))  [Horner; cada passo
      rhe(p·u, 63); final rhe(r·p, 63)]  — Taylor até r^19/19!
    cos(r) = c0 + u·(c2 + u·(c4 + … + u·c18))       — Taylor até r^18/18!
    sin(A) por k mod 4: 0→sin(r); 1→cos(r); 2→−sin(r); 3→−cos(r)
    Erro total ≤ ~2^-57 (entrada 2^-64·|A| + redução |k|·2^-64 + truncamento
    1,2e-22 + coeficientes 10·2^-64 + Horner 10·2^-64) — 6+ ordens abaixo
    do passo da grade B=16 (~1,0e-4 = 2^-13,3).

  QUANTIZAÇÃO (equivalente inteira exata da pouw-quant-v1):
    lo, hi : valores float64 EXATOS do desafio (mín/máx por SELEÇÃO de bits —
             sem aritmética), convertidos a Q63 (exatos para |valor| ≥ 2^-10;
             erro de representação do float64 original é ZERO porque o .npy é
             a âncora de bytes e a conversão bit→Q63 é exata nessa faixa).
    q_i = clip(divround((R_i − lo)·65535, hi − lo), 0, 65535)
    (a pouw-quant-v1 calcula s=65535/(hi−lo) e (R−lo)·s em float64 com 2
    arredondamentos; a v1-v2 diferença é ≤ ~2 ulps float64 — irrelevante
    para bins, medido em experimento_equivalencia.py)
    HASH: SHA-256("pouw-int-v1|B=16|<H>x<W>|" ‖ q em uint16 big-endian,
    ordem C) — separação de domínio da spec (header DIFERENTE do v1).

  GATE DE QUALIDADE (PSNR ≥ alvo como desigualdade inteira EXATA):
    ref : desafio em Q63 (lo/hi EXATOS por bits; demais amostras quantizadas
          a Q63 com erro ≤ 2^-64 — 11 ordens abaixo da margem típica do
          gate, que é ≥ 2,5× nos blocos oficiais); S = Σ(R_i − ref_i)²;
    alcance = hi − lo. Alvo múltiplo de 5 dB (a F2 usa 40…65 de 5 em 5):
      r = alvo mod 10:
      r = 0: T = 10^(alvo/10) INTEIRO exato → condição S·10^t ≤ N·alcance²
             (t = alvo/10; comparação inteira exata, sem escala)
      r = 5: T = 10^k·√10 (irracional) → T em Q63 por RAIZ QUADRADA INTEIRA
             EXATA: T_q63 = round(√(10^(2k+1)·2^126)) via Newton bigint
             (empate é impossível: exigiria 10^(2k+1)·2^126 = q² + q + 1/4,
             não-inteiro) → condição S·T_q63 ≤ N·alcance²·2^63 (limiar
             arredondado rhe, erro ≤ 2^-64 relativo — 19 ordens abaixo das
             margens medidas). Zero log, zero sqrt de float, zero div.
    Demais alvos são rejeitados (a spec pinaria literais; desnecessário ao
    demo).

  FORMATO DE ARQUIVO DE PESOS (.bin canônico, gerado por exportar_pesos_int.py):
    linha 1 (ASCII, \\n): "pouw-int-v1|Q=63|camadas=2,128,128,128,1|omega_0=30|grade=64"
    corpo: int64 little-endian COM SINAL, um por peso/viés, na ordem: para
    cada camada Linear (na ordem da rede): W achatado row-major (saída×entrada)
    seguido do viés b. Restrição medida: |w| < 1 (max real 0,5016 em 18
    receitas) → Q63 cabe em int64 com folga de 2×.

  LEITOR .npy SEM numpy (desafios e quantizadas publicadas):
    header v1/v2 do formato .npy parseado por ast.literal_eval (apenas
    str/bool/int/tuple — nenhum float é materializado); bytes crus lidos com
    int.from_bytes. descr aceitos: '<f8', '<f4', '<u2', '|u1', '<u1'.
    Mín/máx por chave de ordem de bits (float64 finito: chave = u|2^63 se
    positivo, ~u se negativo) — ordenação EXATA sem comparar floats.
    Inf/NaN rejeitados.

Este módulo importa SOMENTE: hashlib, sys, ast. A função auditar_sem_float()
permite a qualquer verificador provar em runtime que math/numpy/torch etc.
nunca foram carregados no processo.
"""

import ast
import hashlib
import sys

VERSAO_SPEC = "pouw-int-v1"
Q = 63
UM = 1 << Q                 # 1.0 em Q63
B_QUANT = 16
N_NIVEIS = (1 << B_QUANT) - 1   # 65535
MASCARA_U64 = (1 << 64) - 1

# ----------------------------------------------------------------------------
# 1. Arredondamentos pinados (half-even, a mesma regra do np.rint da v1)
# ----------------------------------------------------------------------------


def rhe(x, k):
    """round-half-even(x / 2^k) para inteiros (k > 0). Determinístico,
    correto para negativos (divmod do Python floora; resto em [0, 2^k))."""
    if k <= 0:
        raise ValueError(f"k deve ser > 0; recebi k={k}")
    meio = 1 << (k - 1)
    quoc, resto = divmod(x, 1 << k)
    if resto > meio or (resto == meio and (quoc & 1)):
        quoc += 1
    return quoc


def divround(a, b):
    """round-half-even(a / b) para inteiros, b > 0. Determinístico,
    correto para a negativo."""
    if b <= 0:
        raise ValueError(f"b deve ser > 0; recebi b={b}")
    quoc, resto = divmod(a, b)
    dobro = resto * 2
    if dobro > b or (dobro == b and (quoc & 1)):
        quoc += 1
    return quoc


# ----------------------------------------------------------------------------
# 2. Constantes pinadas
# ----------------------------------------------------------------------------

# π com 50 dígitos decimais (literal PINADO na spec; conferido por Machin
# bigint em smoke_int.py — o literal é verificável sem confiar em ninguém).
PI_DEC = "3.14159265358979323846264338327950288419716939937510"


def _pi_num_den():
    s = PI_DEC.replace(".", "")
    return int(s), 10 ** (len(s) - 1)


_PI_NUM, _PI_DEN = _pi_num_den()
C_MEIO_PI = divround(_PI_NUM << (Q - 1), _PI_DEN)   # π/2 em Q63 (erro ≤ 2^-64)


_FAT_CACHE = {}


def _fat(n):
    """n! exato (inteiros)."""
    if n not in _FAT_CACHE:
        r = 1
        for k in range(2, n + 1):
            r *= k
        _FAT_CACHE[n] = r
    return _FAT_CACHE[n]


def _coef_taylor(expoente):
    """Coeficiente 1/expoente! em Q63 (half-even), com o sinal alternado do
    desenvolvimento de sin (expoente ímpar) ou cos (expoente par)."""
    if expoente % 2:  # ímpar: sin, termo (-1)^n com n=(m-1)/2
        sinal = 1 if ((expoente - 1) // 2) % 2 == 0 else -1
    else:             # par: cos, termo (-1)^n com n=m/2
        sinal = 1 if (expoente // 2) % 2 == 0 else -1
    return sinal * divround(1 << Q, _fat(expoente))


# sin(r) = r·(c1 + u·(c3 + u·(c5 + … + u·c19))),  u = r²  — até r^19/19!
# cos(r) = c0 + u·(c2 + u·(c4 + … + u·c18))               — até r^18/18!
_SIN_C = {m: _coef_taylor(m) for m in (1, 3, 5, 7, 9, 11, 13, 15, 17, 19)}
_COS_C = {m: _coef_taylor(m) for m in (0, 2, 4, 6, 8, 10, 12, 14, 16, 18)}


# ----------------------------------------------------------------------------
# 3. seno inteiro
# ----------------------------------------------------------------------------


def _seno_reduzido(r):
    """sin(r) para |r| ≤ π/4 + 2^-64, em Q63."""
    u = rhe(r * r, Q)
    p = _SIN_C[19]
    for expo in (17, 15, 13, 11, 9, 7, 5, 3):
        p = _SIN_C[expo] + rhe(p * u, Q)
    p = _SIN_C[1] + rhe(p * u, Q)
    return rhe(r * p, Q)


def _cosseno_reduzido(r):
    """cos(r) para |r| ≤ π/4 + 2^-64, em Q63."""
    u = rhe(r * r, Q)
    p = _COS_C[18]
    for expo in (16, 14, 12, 10, 8, 6, 4, 2):
        p = _COS_C[expo] + rhe(p * u, Q)
    p = _COS_C[0] + rhe(p * u, Q)
    return p


def sin_q(a):
    """sin(a) em Q63; a em Q63. Redução por π/2 + Taylor; zero floats."""
    k = divround(a, C_MEIO_PI)
    r = a - k * C_MEIO_PI
    m = k & 3
    if m == 0:
        return _seno_reduzido(r)
    if m == 2:
        return -_seno_reduzido(r)
    c = _cosseno_reduzido(r)
    return c if m == 1 else -c


# ----------------------------------------------------------------------------
# 4. Leitor de .npy por bits (sem numpy, sem materializar floats)
# ----------------------------------------------------------------------------


def ler_npy_bits(caminho):
    """Lê um .npy e retorna (descr, shape, dados_bytes_crus).
    Nenhum valor float é interpretado — apenas bytes."""
    with open(caminho, "rb") as f:
        magic = f.read(6)
        if magic != b"\x93NUMPY":
            raise ValueError(f"{caminho}: magic do .npy ausente")
        versao = f.read(2)
        major = versao[0]
        if major == 1:
            hlen = int.from_bytes(f.read(2), "little")
        elif major == 2:
            hlen = int.from_bytes(f.read(4), "little")
        else:
            raise ValueError(f"{caminho}: versão de formato .npy {major} não suportada")
        header = f.read(hlen)
        dados = f.read()
    d = ast.literal_eval(header.decode("ascii"))
    descr = d["descr"]
    if d["fortran_order"]:
        raise ValueError(f"{caminho}: fortran_order=True não suportado (spec exige ordem C)")
    if not (len(descr) == 3 and descr[0] in "<|" and descr[1] in "fu" and descr[2] in "1248"):
        raise ValueError(f"{caminho}: descr não suportado: {descr!r}")
    return descr, tuple(d["shape"]), dados


def _uwords(dados, itemsize):
    """Bytes crus → lista de inteiros sem sinal (little-endian)."""
    if itemsize == 1:
        return list(dados)
    return [int.from_bytes(dados[i:i + itemsize], "little")
            for i in range(0, len(dados) - itemsize + 1, itemsize)]


# ----------------------------------------------------------------------------
# 5. float64 por bits → Q63 (conversão EXATA, sem aritmética de float)
# ----------------------------------------------------------------------------


def _f64_partes(u):
    """Bits u64 de um float64 FINITO → (sinal, num, exp) com
    valor = (−1)^sinal · num · 2^exp. Rejeita Inf/NaN."""
    sinal = u >> 63
    e = (u >> 52) & 0x7FF
    frac = u & ((1 << 52) - 1)
    if e == 0x7FF:
        raise ValueError("valor Inf/NaN não suportado pela pouw-int-v1")
    if e == 0:
        return sinal, frac, -1074          # subnormal (ou zero se frac=0)
    return sinal, (1 << 52) | frac, e - 1075


def f64_bits_para_q63(u):
    """Bits float64 → Q63 (half-even quando não exato). Sem floats."""
    sinal, num, exp = _f64_partes(u)
    if num == 0:
        return 0
    e = exp + Q
    if e >= 0:
        q = num << e
    else:
        q = rhe(num, -e)
    return -q if sinal else q


def f64_bits_para_q63_exato(u):
    """Como f64_bits_para_q63, mas ERRA se o valor não for exatamente
    representável em Q63 (usado para lo/hi/ref — âncoras de exatidão)."""
    sinal, num, exp = _f64_partes(u)
    if num != 0 and exp + Q < 0:
        raise ValueError(
            f"valor float64 (exp={exp}) não é representável exatamente em Q63")
    return f64_bits_para_q63(u)


def chave_ordem_f64(u):
    """Chave inteira com a MESMA ordem dos float64 finitos (por bits).
    positivo: u | 2^63; negativo: ~u (mascarado). -0.0 < +0.0 por bits
    (valores iguais — irrelevante para min/max de valor)."""
    if u >> 63:
        return (~u) & MASCARA_U64
    return u | (1 << 63)


def limites_e_referencia_int(caminho_npy):
    """Desafio .npy (float64) → (lo_q63, hi_q63, ref_q63[], shape).
    lo/hi por SELEÇÃO (chave de ordem de bits); ref em Q63 exato."""
    descr, shape, dados = ler_npy_bits(caminho_npy)
    if descr != "<f8":
        raise ValueError(f"{caminho_npy}: esperado descr '<f8', recebi {descr!r}")
    if len(shape) != 2:
        raise ValueError(f"{caminho_npy}: esperado array 2D, recebi shape {shape}")
    us = _uwords(dados, 8)
    if len(us) != shape[0] * shape[1]:
        raise ValueError(f"{caminho_npy}: {len(us)} valores != shape {shape}")
    lo_u = min(us, key=chave_ordem_f64)
    hi_u = max(us, key=chave_ordem_f64)
    lo = f64_bits_para_q63_exato(lo_u)
    hi = f64_bits_para_q63_exato(hi_u)
    if hi <= lo:
        raise ValueError(f"{caminho_npy}: limites degenerados (lo={lo}, hi={hi})")
    # referência do gate QUANTIZADA a Q63 (erro ≤ 2^-64 por amostra — 11
    # ordens abaixo da margem típica do gate; ver spec/relatório). Valores
    # próximos de cruzamentos de zero podem ter exp < -63 e não são exatos.
    ref = [f64_bits_para_q63(u) for u in us]
    return lo, hi, ref, shape


def ler_quantizada_u16(caminho_npy):
    """Array .npy uint16 publicado → lista de ints + shape (por bits)."""
    descr, shape, dados = ler_npy_bits(caminho_npy)
    if descr != "<u2":
        raise ValueError(f"{caminho_npy}: esperado descr '<u2', recebi {descr!r}")
    return _uwords(dados, 2), shape


# ----------------------------------------------------------------------------
# 6. Formato de pesos inteiros (.bin canônico)
# ----------------------------------------------------------------------------


def carregar_pesos_int(caminho):
    """Lê o .bin de pesos canônicos → dict {camadas, omega_0, grade, W, b}."""
    with open(caminho, "rb") as f:
        bruto = f.read()
    pos = bruto.find(b"\n")
    if pos < 0:
        raise ValueError(f"{caminho}: header ASCII ausente")
    partes = bruto[:pos].decode("ascii").split("|")
    try:
        if partes[0] != VERSAO_SPEC:
            raise ValueError(f"spec {partes[0]!r} != {VERSAO_SPEC!r}")
        if partes[1] != f"Q={Q}":
            raise ValueError(f"formato Q {partes[1]!r} != Q={Q}")
        camadas = [int(x) for x in partes[2].split("=", 1)[1].split(",")]
        omega = int(partes[3].split("=", 1)[1])
        grade = int(partes[4].split("=", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"{caminho}: header inválido ({bruto[:pos]!r}): {exc}") from exc
    corpo = bruto[pos + 1:]
    n_pesos = sum(o * i + o for o, i in zip(camadas[1:], camadas[:-1]))
    if len(corpo) != n_pesos * 8:
        raise ValueError(f"{caminho}: corpo {len(corpo)} B != esperado {n_pesos * 8} B")
    vals = [int.from_bytes(corpo[i:i + 8], "little", signed=True)
            for i in range(0, n_pesos * 8, 8)]
    W, b, p = [], [], 0
    for o, i in zip(camadas[1:], camadas[:-1]):
        Wl = []
        for _ in range(o):
            Wl.append(vals[p:p + i])
            p += i
        W.append(Wl)
        b.append(vals[p:p + o])
        p += o
    return {"camadas": camadas, "omega_0": omega, "grade": grade, "W": W, "b": b}


# ----------------------------------------------------------------------------
# 7. Forward inteiro
# ----------------------------------------------------------------------------


def _camada(chans, W, b):
    """z_j = b_j + Σ_i W[j][i]·chan_i — acumulação EXATA em Q126
    (inteiros: qualquer ordem de soma dá o MESMO resultado)."""
    n_pontos = len(chans[0])
    saida = []
    for j, bj in enumerate(b):
        linha = W[j]
        acc = [bj << Q] * n_pontos
        for i, w in enumerate(linha):
            ch = chans[i]
            acc = [a + w * c for a, c in zip(acc, ch)]
        saida.append(acc)
    return saida


def forward_int(pesos):
    """Forward SIREN 100% inteiro. Retorna lista R (Q63) row-major,
    len = grade². ver tempos: usar experimento_equivalencia.py."""
    camadas = pesos["camadas"]
    omega = pesos["omega_0"]
    lado = pesos["grade"]
    if camadas[0] != 2:
        raise ValueError(f"esperado dim_entrada=2, recebi {camadas[0]}")
    # coords exatas (2j-(S-1))/(S-1) em Q63 — mesmo valor real do
    # linspace(0,1,S)*2-1 da F1, aqui como racional exato arredondado 1×
    cs = [divround((2 * j - (lado - 1)) << Q, lado - 1) for j in range(lado)]
    ch0, ch1 = [], []
    for i in range(lado):
        ci = cs[i]
        for j in range(lado):
            ch0.append(cs[j])   # x = valor da COLUNA (meshgrid/ravel da F1)
            ch1.append(ci)      # y = valor da LINHA
    chans = [ch0, ch1]
    n_lin = len(camadas) - 1
    R = None
    for idx in range(n_lin):
        accs = _camada(chans, pesos["W"][idx], pesos["b"][idx])
        if idx < n_lin - 1:
            chans = [[sin_q(omega * rhe(z, Q)) for z in acc] for acc in accs]
        else:
            if len(accs) != 1:
                raise ValueError(f"última camada deve ter 1 saída, recebi {len(accs)}")
            R = [rhe(z, Q) for z in accs[0]]
    return R


# ----------------------------------------------------------------------------
# 8. Quantização + hash + gate (tudo inteiro)
# ----------------------------------------------------------------------------


def _isqrt(n):
    """⌊√n⌋ por Newton em inteiros (n ≥ 0). Determinístico, sem floats."""
    if n < 0:
        raise ValueError("isqrt de negativo")
    if n < 2:
        return n
    x = 1 << ((n.bit_length() + 1) // 2)   # estimativa inicial ≥ √n
    while True:
        y = (x + n // x) // 2
        if y >= x:
            return x
        x = y


def _isqrt_rhe(n):
    """round(√n) em inteiros. Empate é IMPOSSÍVEL: exigiria n = q²+q+1/4
    (não inteiro); portanto a comparação r > q decide sozinha."""
    q = _isqrt(n)
    r = n - q * q
    return q + 1 if r > q else q


def _limiar_q63(alvo_db):
    """10^(alvo/10) em Q63 (rhe). alvo múltiplo de 5 dB, alvo ≥ 0.
    r=0: exato (10^k << 63). r=5: raiz inteira exata de 10^(2k+1)·2^126."""
    alvo = int(alvo_db)
    if alvo < 0 or alvo % 5 != 0 or alvo != alvo_db:
        raise ValueError(f"pouw-int-v1 exige alvo múltiplo de 5 dB (≥ 0); recebi {alvo_db}")
    k, r = divmod(alvo, 10)
    if r == 0:
        return (10 ** k) << Q
    return _isqrt_rhe((10 ** (2 * k + 1)) << (2 * Q))


def quantizar_int(r_q63, lo_q63, hi_q63):
    """q_i = clip(divround((R_i − lo)·65535, hi − lo), 0, 65535)."""
    if hi_q63 <= lo_q63:
        raise ValueError(f"limites degenerados: lo={lo_q63}, hi={hi_q63}")
    alcance = hi_q63 - lo_q63
    qs = []
    for r in r_q63:
        q = divround((r - lo_q63) * N_NIVEIS, alcance)
        if q < 0:
            q = 0
        elif q > N_NIVEIS:
            q = N_NIVEIS
        qs.append(q)
    return qs


def hash_quantizado_int(qs, h, w):
    """SHA-256 com separação de domínio pouw-int-v1 (uint16 big-endian)."""
    ba = bytearray()
    for q in qs:
        ba += q.to_bytes(2, "big")
    pre = f"{VERSAO_SPEC}|B={B_QUANT}|{h}x{w}|".encode("ascii") + bytes(ba)
    return hashlib.sha256(pre).hexdigest()


def gate_mse_int(r_q63, ref_q63, lo_q63, hi_q63, alvo_psnr_db):
    """PSNR ≥ alvo como desigualdade INTEIRA (ver spec no docstring).
    Retorna (aprovado, lado_esquerdo, limite) — para r=0 a comparação é
    S·10^t ≤ N·alcance² (exata, sem escala); para r=5 é
    S·T_q63 ≤ N·alcance²·2^63 (limiar rhe, erro ≤ 2^-64 relativo)."""
    alvo = int(alvo_psnr_db)
    if alvo < 0 or alvo % 5 != 0 or alvo != alvo_psnr_db:
        raise ValueError(f"pouw-int-v1 exige alvo múltiplo de 5 dB (≥ 0); recebi {alvo_psnr_db}")
    n = len(r_q63)
    alcance = hi_q63 - lo_q63
    s = 0
    for r, f in zip(r_q63, ref_q63):
        d = r - f
        s += d * d
    k, resto = divmod(alvo, 10)
    if resto == 0:
        esq = s * (10 ** k)
        lim = n * alcance * alcance
    else:
        t_q = _limiar_q63(alvo)
        esq = s * t_q
        lim = (n * alcance * alcance) << Q
    return esq <= lim, esq, lim


def compromisso_completo(pesos, caminho_desafio, alvo_psnr_db):
    """Caminho completo v2: forward + limites + quantização + hash + gate.
    Retorna dict com tudo (ints/strings). Usado por verificar_int.py e
    experimentos."""
    r = forward_int(pesos)
    lo, hi, ref, shape = limites_e_referencia_int(caminho_desafio)
    qs = quantizar_int(r, lo, hi)
    comp = hash_quantizado_int(qs, shape[0], shape[1])
    aprovado, esq, lim = gate_mse_int(r, ref, lo, hi, alvo_psnr_db)
    return {
        "reconstrucao_q63": r,
        "lo_q63": lo, "hi_q63": hi,
        "quantizada": qs,
        "compromisso": comp,
        "gate_aprovado": aprovado,
        "gate_S_vezes_10t": esq,
        "gate_limite": lim,
        "shape": shape,
    }


# ----------------------------------------------------------------------------
# 9. Auditoria de ausência de floats
# ----------------------------------------------------------------------------

_MODULOS_PROIBIDOS = ("math", "cmath", "numpy", "torch", "scipy", "decimal",
                      "fractions", "statistics", "random")


def auditar_sem_float():
    """Lista de módulos de ponto flote/aleatoriedade presentes no processo.
    Vazia = o processo nunca carregou nenhum módulo capaz de aritmética de
    ponto flutuante (verificar_int.py roda em processo próprio e frio)."""
    return [m for m in _MODULOS_PROIBIDOS if m in sys.modules]
