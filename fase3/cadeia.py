#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cadeia.py — PoUW Fase 3: MINERADOR da cadeia demo (spec pouw-cadeia-demo-v1).

FECHA O ARCO da pesquisa: transforma o "bloco único validável" da Fase 2 em um
ESQUELETO DE CADEIA encadeada (candidato 3 do roadmap do README), medindo
custos por bloco dos dois lados (mineração cara vs verificação barata).

REGRA DA CADEIA (demo, tudo derivado de constantes da spec):
  gênese       : genesis_hash = SHA-256("pouw-cadeia-demo-v1|genesis|v1")
  bloco i      :
    seed_i     = prev_hash_i  (= genesis_hash para i=1; hash do bloco i-1 caso
                 contrário) — o DESAFIO é função PURA da seed:
                 desafio_i, _ = gerar_desafio(prev_hash_i)   [desafio.py F1]
    treino     : treinar.py da Fase 1 (INTOCADO) sobre desafio_i → receita_i
                 [trabalho útil: segundos de CPU]
    compromisso: forward float64 (1 thread) + quantização pouw-quant-v1 B=16
                 → comp_i = hash_quantizado(...)            [spec F2]
    header     : "pouw-cadeia-demo-v1|bloco=<i>|prev=<prev>|comp=<comp>|
                  alvo=<alvo>" + "|nonce=<n>"
    moagem     : nonce até SHA-256(header) ter k bits zero à frente
                 [queima pura — ajuste fino exponencial; custo dominante é o
                 treino, como medido no E5 da F2]
    encadeia   : prev_hash_{i+1} = SHA-256(header_com_nonce)  → SERIAL o
                 trabalho: o desafio i+1 só existe após o bloco i fechar.
  âncoras publicadas por bloco: desafio_XX.npy (33 kB), receita_XX.pt (~138 kB),
  quantizada_XX_u16.npy (8,3 kB) + registro em cadeia.json (hashes SHA-256 de
  todos + compromisso do DESAFIO também quantizado — tolerante a resíduo de
  libm cross-CPU, ao contrário do hash de bytes crus; ver limitações).

DECISÕES DECLARADAS (tudo que afeta os números):
  - B=16 fixo (recomendação da F2); forward de compromisso em float64 com
    1 thread (mesmo caminho do verificador — é isso que garante o match).
  - Treino em subprocesso com threads default do torch (2 nesta VM) — o
    compromisso NÃO depende das threads do treino, só dos pesos finais.
  - Nonces iniciais: default_rng(20260902) — determinístico (demo; minerador
    real escolheria nonces livremente, o que não muda a regra de validade).
  - Tempos: perf_counter por região (desafio, treino [interno do treinar.py],
    forward+quant, moagem) + parede do bloco inteiro e da cadeia.
  - PSNR registrado: reconstrução float64 vs desafio publicado (float64).

Uso (a partir da raiz do repositório):
    python3 fase3/cadeia.py [--blocos 8] [--alvo-psnr 40.0] [--prefixo-bits 16]
                            [--max-epocas 5000] [--saida fase3/cadeia_demo]
"""

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))            # desafio.py (F1, na raiz)
sys.path.insert(0, str(RAIZ / "fase2"))  # quantizar.py (F2)

from desafio import gerar_desafio  # noqa: E402
from quantizar import hash_quantizado, limites_do_desafio, psnr_db, quantizar  # noqa: E402

SPEC = "pouw-cadeia-demo-v1"
GENESIS_PRE = f"{SPEC}|genesis|v1"
BITS_QUANT = 16
SEMENTE_RNG = 20260902

RE_TREINO = re.compile(r"Tempo de treino \(perf_counter.*?\): ([0-9.]+) s")
RE_EPOCAS = re.compile(r"Total de epocas executadas: (\d+)")
RE_PSNR_TREINO = re.compile(r"PSNR final \(avaliacao pos-treino, float64\): ([0-9.]+) dB")
RE_HASH_RECEITA = re.compile(r"SHA-256 da receita: ([0-9a-f]{64})")


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def bits_zero_prefixo(digest: bytes) -> int:
    n = 0
    for b in digest:
        if b == 0:
            n += 8
        else:
            n += 8 - b.bit_length()
            break
    return n


def agora_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def moer_nonce(header_base: str, k: int, nonce0: int):
    """Moagem até bits_zero_prefixo(SHA-256(header_base + '|nonce=<n>')) >= k.

    header_base NÃO contém o nonce. Retorna (nonce, digest_hex, tentativas, tempo).
    """
    t_ini = time.perf_counter()
    nonce = nonce0
    tentativas = 0
    while True:
        d = hashlib.sha256((header_base + f"|nonce={nonce}").encode("ascii")).digest()
        tentativas += 1
        if bits_zero_prefixo(d) >= k:
            break
        nonce += 1
    return nonce, d.hex(), tentativas, time.perf_counter() - t_ini


def minerar_bloco(i, prev_hex, dir_saida, alvo_psnr, prefixo_bits, max_epocas, rng, forward_torch64):
    t_bloco_ini = time.perf_counter()

    # ---------- 1. desafio (função pura da seed = prev_hash) ----------
    t = time.perf_counter()
    campo, hash_seed = gerar_desafio(prev_hex)
    caminho_desafio = dir_saida / f"desafio_{i:02d}.npy"
    np.save(caminho_desafio, campo)
    sha_desafio = sha256_arquivo(caminho_desafio)
    # compromisso do DESAFIO: quantizado nos limites do próprio campo
    # (checável cross-CPU mesmo que libm diverja ~1 ulp; ver docstring/limitações)
    lo_d, hi_d = float(campo.min()), float(campo.max())
    comp_desafio = hash_quantizado(quantizar(campo, lo_d, hi_d, BITS_QUANT))
    t_desafio = time.perf_counter() - t

    # ---------- 2. treino (trabalho útil; treinar.py da F1 intocado) ----------
    caminho_receita = dir_saida / f"receita_{i:02d}.pt"
    r = subprocess.run(
        [sys.executable, "treinar.py", str(caminho_desafio),
         "--max-epocas", str(max_epocas), "--alvo-psnr", f"{alvo_psnr}",
         "--saida", str(caminho_receita)],
        cwd=str(RAIZ), capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.stdout.write(r.stdout)
        sys.stdout.write(r.stderr)
        raise RuntimeError(f"treinar.py FALHOU no bloco {i} (código {r.returncode}); stderr acima")
    m = RE_TREINO.search(r.stdout)
    t_treino = float(m.group(1))
    epocas = int(RE_EPOCAS.search(r.stdout).group(1))
    psnr_treino = float(RE_PSNR_TREINO.search(r.stdout).group(1))
    sha_receita = RE_HASH_RECEITA.search(r.stdout).group(1)

    # ---------- 3. compromisso (forward float64 1 thread + pouw-quant-v1) ----------
    t = time.perf_counter()
    rec64, _receita, _nparams = forward_torch64(str(caminho_receita), threads=1)
    lo, hi = limites_do_desafio(str(caminho_desafio))
    q = quantizar(rec64, lo, hi, BITS_QUANT)
    comp = hash_quantizado(q)
    caminho_quant = dir_saida / f"quantizada_{i:02d}_u16.npy"
    np.save(caminho_quant, q)
    sha_quant = sha256_arquivo(caminho_quant)
    psnr_ver = psnr_db(np.load(caminho_desafio), rec64)
    t_compromisso = time.perf_counter() - t

    # ---------- 4. header + moagem de nonce (ajuste fino exponencial) ----------
    header_base = f"{SPEC}|bloco={i}|prev={prev_hex}|comp={comp}|alvo={alvo_psnr:g}"
    nonce0 = int(rng.integers(0, 2**63))
    nonce, hash_bloco, tentativas, t_moagem = moer_nonce(header_base, prefixo_bits, nonce0)

    t_bloco_total = time.perf_counter() - t_bloco_ini

    registro = {
        "bloco": i,
        "prev": prev_hex,
        "seed_desafio": prev_hex,
        "hash_da_seed_gerar_desafio": hash_seed,
        "arquivo_desafio": caminho_desafio.name,
        "sha256_desafio_npy": sha_desafio,
        "comp_desafio": comp_desafio,
        "arquivo_receita": caminho_receita.name,
        "sha256_receita": sha_receita,
        "compromisso": comp,
        "arquivo_quantizada": caminho_quant.name,
        "sha256_quantizada": sha_quant,
        "alvo_psnr": alvo_psnr,
        "epocas": epocas,
        "psnr_treino": psnr_treino,
        "psnr_verificacao": psnr_ver,
        "header_sem_nonce": header_base,
        "nonce": nonce,
        "nonce_inicial": nonce0,
        "tentativas_nonce": tentativas,
        "hash_bloco": hash_bloco,
        "tempos": {
            "desafio_s": round(t_desafio, 6),
            "treino_s": round(t_treino, 6),
            "forward_quant_s": round(t_compromisso, 6),
            "moagem_s": round(t_moagem, 6),
            "bloco_parede_s": round(t_bloco_total, 6),
        },
    }

    print(f"\n########## BLOCO {i} ##########")
    print(f"seed/prev : {prev_hex[:32]}…")
    print(f"desafio   : {caminho_desafio.name} | sha256 {sha_desafio[:32]}… | comp_desafio {comp_desafio[:16]}…")
    print(f"treino    : {epocas} épocas | PSNR treino {psnr_treino:.4f} dB | tempo {t_treino:.6f} s | receita sha256 {sha_receita[:16]}…")
    print(f"compromisso (float64, 1 thread, B={BITS_QUANT}): {comp}")
    print(f"quantizada: {caminho_quant.name} | sha256 {sha_quant}")
    print(f"header    : {header_base[:80]}…|nonce={nonce}")
    print(f"moagem    : {tentativas:,} tentativas (k={prefixo_bits} bits) em {t_moagem:.6f} s")
    print(f"hash_bloco: {hash_bloco}")
    print(f"PSNR verificação (float64 vs desafio): {psnr_ver:.4f} dB | parede do bloco: {t_bloco_total:.6f} s")
    return registro, hash_bloco


def main():
    ap = argparse.ArgumentParser(description="Minerador da cadeia demo — PoUW Fase 3")
    ap.add_argument("--blocos", type=int, default=8)
    ap.add_argument("--alvo-psnr", type=float, default=40.0)
    ap.add_argument("--prefixo-bits", type=int, default=16)
    ap.add_argument("--max-epocas", type=int, default=5000)
    ap.add_argument("--saida", default="fase3/cadeia_demo")
    args = ap.parse_args()

    t0 = time.perf_counter()
    # import tardio (contabilizado à parte, padrão F2)
    t_imp = time.perf_counter()
    import torch  # noqa: E402
    from verificar_fase2 import forward_torch64  # noqa: E402  (fase2/ no sys.path)
    t_import = time.perf_counter() - t_imp

    dir_saida = RAIZ / args.saida
    dir_saida.mkdir(parents=True, exist_ok=True)

    genesis_hash = hashlib.sha256(GENESIS_PRE.encode("ascii")).hexdigest()
    rng = np.random.default_rng(SEMENTE_RNG)

    print("== cadeia.py — PoUW Fase 3 (minerador da cadeia demo, pouw-cadeia-demo-v1) ==")
    print(f"INICIO {agora_utc()}")
    print(f"Python {platform.python_version()} | PyTorch {torch.__version__} | NumPy {np.__version__}")
    print(f"Import do PyTorch + verificar_fase2: {t_import:.3f} s (à parte das regiões medidas)")
    print(f"Saída: {dir_saida} | blocos: {args.blocos} | alvo PSNR: {args.alvo_psnr} dB | prefixo: {args.prefixo_bits} bits | max-épocas: {args.max_epocas}")
    print(f"Gênese: SHA-256('{GENESIS_PRE}') = {genesis_hash}")
    print("Forward de compromisso: float64, 1 thread (mesmo caminho do verificador) | treino: subprocesso, threads default")
    print(f"Nonces iniciais: default_rng({SEMENTE_RNG}) — determinístico (demo)")

    prev = genesis_hash
    registros = []
    t_min_ini = time.perf_counter()
    for i in range(1, args.blocos + 1):
        registro, hash_bloco = minerar_bloco(
            i, prev, dir_saida, args.alvo_psnr, args.prefixo_bits,
            args.max_epocas, rng, forward_torch64,
        )
        registros.append(registro)
        prev = hash_bloco
    t_min_total = time.perf_counter() - t_min_ini

    soma_treino = sum(r["tempos"]["treino_s"] for r in registros)
    soma_moagem = sum(r["tempos"]["moagem_s"] for r in registros)
    soma_comp = sum(r["tempos"]["forward_quant_s"] for r in registros)
    soma_desafio = sum(r["tempos"]["desafio_s"] for r in registros)

    cadeia = {
        "spec": SPEC,
        "genesis_pre_imagem": GENESIS_PRE,
        "genesis_hash": genesis_hash,
        "alvo_psnr": args.alvo_psnr,
        "prefixo_bits": args.prefixo_bits,
        "bits_quant": BITS_QUANT,
        "max_epocas": args.max_epocas,
        "semente_nonce_rng": SEMENTE_RNG,
        "n_blocos": len(registros),
        "blocos": registros,
        "resumo_mineracao": {
            "soma_treino_s": round(soma_treino, 6),
            "soma_moagem_s": round(soma_moagem, 6),
            "soma_forward_quant_s": round(soma_comp, 6),
            "soma_desafio_s": round(soma_desafio, 6),
            "parede_mineracao_s": round(t_min_total, 6),
        },
    }
    caminho_json = dir_saida / "cadeia.json"
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(cadeia, f, indent=2, ensure_ascii=False)
    sha_json = sha256_arquivo(caminho_json)

    print("\n======== TABELA-RESUMO DA MINERAÇÃO (tudo medido AQUI) ========")
    print(f"{'bloco':>5} | {'épocas':>6} | {'PSNR verif':>10} | {'treino (s)':>10} | {'moagem (s)':>10} | {'tentativas':>12} | compromisso (16) | hash_bloco (16)")
    print("-" * 130)
    for r in registros:
        print(f"{r['bloco']:>5} | {r['epocas']:>6} | {r['psnr_verificacao']:>10.4f} | "
              f"{r['tempos']['treino_s']:>10.6f} | {r['tempos']['moagem_s']:>10.6f} | "
              f"{r['tentativas_nonce']:>12,} | {r['compromisso'][:16]}… | {r['hash_bloco'][:16]}…")
    print()
    print(f"cadeia.json salvo em: {caminho_json} | SHA-256: {sha_json}")
    print(f"SOMA treino (útil): {soma_treino:.6f} s | SOMA moagem (queima): {soma_moagem:.6f} s | "
          f"SOMA forward+quant: {soma_comp:.6f} s | SOMA desafio: {soma_desafio:.6f} s")
    print(f"PAREDE de mineração ({args.blocos} blocos): {t_min_total:.6f} s")
    print(f"Tempo total do script (incl. import): {time.perf_counter() - t0:.6f} s")
    print(f"FIM {agora_utc()}")


if __name__ == "__main__":
    main()
