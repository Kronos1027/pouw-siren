#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_cadeia.py — PoUW Fase 3: VERIFICADOR da cadeia demo (pouw-cadeia-demo-v1).

Verificador INDEPENDENTE e FRIO: não compartilha nenhum estado com o minerador
(processo novo; lê apenas o que está publicado no diretório da cadeia). Para
cada bloco executa 8 checagens (C1–C8); para a cadeia, a checagem C0
(gênese/spec). Código de saída: 0 = cadeia válida; 1 = inválida (oracle).

CHECAGENS (nível cadeia):
  C0  spec == "pouw-cadeia-demo-v1" E genesis_hash == SHA-256(genesis_pre_imagem)
      E n_blocos == len(blocos)
CHECAGENS (por bloco i; barato → caro):
  C1  encadeamento-prev: prev_1 == genesis_hash; prev_i == hash_bloco_{i-1}
  C2  desafio-determinístico: gerar_desafio(prev_i) regenera o desafio; o
      compromisso QUANTIZADO do campo regenerado (pouw-quant-v1, limites do
      próprio campo) == comp_desafio registrado → o desafio publicado É função
      do bloco anterior (tolerante a resíduo de libm ~1 ulp, ao contrário de
      hash de bytes crus; o hash de bytes é conferido na C3)
  C3  âncora-receita-desafio: SHA-256(desafio_XX.npy) == registrado == meta
      .sha256_desafio da receita (a receita foi treinada PARA esse desafio)
  C4  integridade-receita: SHA-256(receita_XX.pt) == registrado
  C5  compromisso: forward float64 (1 thread) + pouw-quant-v1 B=16 ==
      compromisso do bloco [a checagem central da Fase 2]
  C6  quantizada-publicada: array re-quantizado == arquivo publicado
      (elemento a elemento) E SHA-256 do arquivo == registrado
  C7  trabalho-útil: PSNR(reconstrução float64 vs desafio regenerado) >= alvo
  C8  header+nonce: header re-derivado de (bloco, prev, comp, alvo) ==
      header registrado; SHA-256(header + "|nonce=<n>") == hash_bloco
      registrado E bits zero à frente >= prefixo_bits

DECISÕES DE MEDIÇÃO:
  - torch.set_num_threads(1) (herança F1/F2, conservador); forward float64.
  - "Tempo de verificação" (perf_counter): da carga do cadeia.json ao último
    PSNR, SEM o import do PyTorch (reportado à parte).
  - --apenas-bloco N: verifica somente o bloco N (mesmas checagens; C1 usa o
    hash do bloco N-1 registrado no próprio JSON) — usado pelo
    experimento_lote.py para medir o custo de verificação fria POR BLOCO.

Uso (a partir da raiz do repositório):
    python3 fase3/verificar_cadeia.py [fase3/cadeia_demo] [--apenas-bloco N]
"""

import argparse
import hashlib
import json
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
BITS_QUANT = 16

NOMES_CHECAGENS = {
    "C1": "encadeamento-prev",
    "C2": "desafio-deterministico",
    "C3": "ancora-receita-desafio",
    "C4": "integridade-receita",
    "C5": "compromisso",
    "C6": "quantizada-publicada",
    "C7": "trabalho-util",
    "C8": "header-nonce",
}


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


def _montar_header(bloco, prev, comp, alvo):
    """Re-deriva o header SEM nonce com a MESMA regra de formatação do minerador."""
    return f"{SPEC}|bloco={bloco}|prev={prev}|comp={comp}|alvo={alvo:g}"


def verificar_cadeia_completa(dir_cadeia, forward_torch64, apenas_bloco=None, verbose=True):
    """Verifica a cadeia (ou um bloco, com --apenas-bloco). Retorna dict:

    {cadeia_ok, genesis_ok, blocos: [{bloco, ok, falhas, tempo_s, psnr,
     compromisso, hash_bloco}], tempo_verificacao_s, n_blocos}
    A região medida (tempo_verificacao_s) começa na carga do JSON e termina
    após o último PSNR — sem imports (quem chama controla os imports).
    """
    t_ver_ini = time.perf_counter()
    dir_cadeia = Path(dir_cadeia)
    with open(dir_cadeia / "cadeia.json", "r", encoding="utf-8") as f:
        cadeia = json.load(f)

    # ---------- C0: gênese/spec ----------
    genesis_ok = (
        cadeia.get("spec") == SPEC
        and hashlib.sha256(cadeia.get("genesis_pre_imagem", "").encode("ascii")).hexdigest()
        == cadeia.get("genesis_hash")
        and cadeia.get("n_blocos") == len(cadeia.get("blocos", []))
        and cadeia.get("bits_quant") == BITS_QUANT
    )

    blocos = cadeia["blocos"]
    prefixo_bits = int(cadeia["prefixo_bits"])
    alvo = float(cadeia["alvo_psnr"])
    genesis_hash = cadeia["genesis_hash"]

    indices = list(range(len(blocos)))
    if apenas_bloco is not None:
        achado = [k for k, b in enumerate(blocos) if b["bloco"] == apenas_bloco]
        if not achado:
            raise SystemExit(f"bloco {apenas_bloco} não existe na cadeia (blocos: {[b['bloco'] for b in blocos]})")
        indices = achado

    resultados = []
    for k in indices:
        b = blocos[k]
        i = b["bloco"]
        t_b_ini = time.perf_counter()
        falhas = {}
        detalhes = {}

        # ---------- C1: encadeamento-prev ----------
        if k == 0:
            prev_esperado = genesis_hash
        else:
            prev_esperado = blocos[k - 1]["hash_bloco"]
        c1 = b["prev"] == prev_esperado and b["seed_desafio"] == b["prev"]
        if not c1:
            falhas["C1"] = f"prev registrado {b['prev'][:16]}… != esperado {prev_esperado[:16]}…"

        # ---------- C2: desafio determinístico da seed ----------
        campo_reg, _hash_seed = gerar_desafio(b["prev"])
        lo_d, hi_d = float(campo_reg.min()), float(campo_reg.max())
        comp_desafio_reg = hash_quantizado(quantizar(campo_reg, lo_d, hi_d, BITS_QUANT))
        c2 = comp_desafio_reg == b["comp_desafio"]
        if not c2:
            falhas["C2"] = f"comp_desafio regenerado {comp_desafio_reg[:16]}… != publicado {b['comp_desafio'][:16]}…"

        # ---------- C3: âncora de bytes do desafio + meta da receita ----------
        caminho_desafio = dir_cadeia / b["arquivo_desafio"]
        sha_desafio = sha256_arquivo(caminho_desafio)
        c3 = sha_desafio == b["sha256_desafio_npy"]
        detalhes["sha_desafio"] = sha_desafio

        # ---------- C5 (forward; necessário também para C3-meta/C6/C7) ----------
        caminho_receita = dir_cadeia / b["arquivo_receita"]
        rec64, receita, _n = forward_torch64(str(caminho_receita), threads=1)
        meta = receita.get("meta", {})
        c3b = meta.get("sha256_desafio") == b["sha256_desafio_npy"]
        if not c3:
            falhas["C3"] = f"sha256(desafio.npy) {sha_desafio[:16]}… != registrado {b['sha256_desafio_npy'][:16]}…"
        elif not c3b:
            falhas["C3"] = f"meta.sha256_desafio da receita != registrado"

        # ---------- C4: integridade da receita ----------
        sha_receita = sha256_arquivo(caminho_receita)
        c4 = sha_receita == b["sha256_receita"]
        if not c4:
            falhas["C4"] = f"sha256(receita.pt) {sha_receita[:16]}… != registrado {b['sha256_receita'][:16]}…"

        # ---------- C5: compromisso quantizado (float64 + B=16) ----------
        lo, hi = limites_do_desafio(str(caminho_desafio))
        q = quantizar(rec64, lo, hi, BITS_QUANT)
        comp = hash_quantizado(q)
        c5 = comp == b["compromisso"]
        detalhes["compromisso"] = comp
        if not c5:
            falhas["C5"] = f"compromisso recomputado {comp[:16]}… != do bloco {b['compromisso'][:16]}…"

        # ---------- C6: quantizada publicada (conteúdo + sha256) ----------
        caminho_quant = dir_cadeia / b["arquivo_quantizada"]
        q_pub = np.load(caminho_quant)
        sha_quant = sha256_arquivo(caminho_quant)
        c6 = np.array_equal(q, q_pub) and sha_quant == b["sha256_quantizada"]
        if not c6:
            falhas["C6"] = (f"quantizada publicada diverge (array_igual={np.array_equal(q, q_pub)}, "
                            f"sha256={sha_quant[:16]}… vs {b['sha256_quantizada'][:16]}…)")

        # ---------- C7: trabalho útil (PSNR contra o desafio REGENERADO) ----------
        psnr = psnr_db(campo_reg, rec64)
        c7 = psnr >= alvo
        detalhes["psnr"] = psnr
        if not c7:
            falhas["C7"] = f"PSNR {psnr:.4f} dB < alvo {alvo} dB"

        # ---------- C8: header + nonce + prefixo ----------
        header_rederivado = _montar_header(i, b["prev"], b["compromisso"], alvo)
        c8a = header_rederivado == b["header_sem_nonce"]
        preimagem = (b["header_sem_nonce"] + f"|nonce={b['nonce']}").encode("ascii")
        digest = hashlib.sha256(preimagem).digest()
        c8b = digest.hex() == b["hash_bloco"]
        c8c = bits_zero_prefixo(digest) >= prefixo_bits
        if not (c8a and c8b and c8c):
            falhas["C8"] = (f"header_ok={c8a}, hash_ok={c8b} (recomputado {digest.hex()[:16]}… "
                            f"vs {b['hash_bloco'][:16]}…), bits_zero={bits_zero_prefixo(digest)} < {prefixo_bits}")

        t_b = time.perf_counter() - t_b_ini
        resultados.append({
            "bloco": i, "ok": len(falhas) == 0, "falhas": falhas,
            "tempo_s": t_b, **detalhes, "hash_bloco": b["hash_bloco"],
        })

        if verbose:
            status = "VÁLIDO" if len(falhas) == 0 else "INVÁLIDO"
            print(f"[bloco {i}] {status} ({t_b:.6f} s) | PSNR {psnr:.4f} dB | comp {comp[:16]}… | "
                  f"hash_bloco {b['hash_bloco'][:16]}…"
                  + ("" if len(falhas) == 0 else " | falhas: " + ", ".join(f"{k}({NOMES_CHECAGENS[k]})" for k in falhas)))
            for k, msg in falhas.items():
                print(f"    {k} ({NOMES_CHECAGENS[k]}): {msg}")

    tempo_ver = time.perf_counter() - t_ver_ini
    todos_ok = genesis_ok and all(r["ok"] for r in resultados)
    return {
        "cadeia_ok": todos_ok,
        "genesis_ok": genesis_ok,
        "blocos": resultados,
        "tempo_verificacao_s": tempo_ver,
        "n_blocos_verificados": len(resultados),
        "alvo_psnr": alvo,
        "prefixo_bits": prefixo_bits,
    }


def main():
    ap = argparse.ArgumentParser(description="Verificador da cadeia demo — PoUW Fase 3")
    ap.add_argument("dir_cadeia", nargs="?", default="fase3/cadeia_demo")
    ap.add_argument("--apenas-bloco", type=int, default=None)
    args = ap.parse_args()

    t0_total = time.perf_counter()
    t_imp = time.perf_counter()
    import torch  # noqa: E402
    from verificar_fase2 import forward_torch64  # noqa: E402
    t_import = time.perf_counter() - t_imp
    torch.set_num_threads(1)

    dir_cadeia = Path(args.dir_cadeia)
    if not dir_cadeia.is_absolute():
        dir_cadeia = RAIZ / dir_cadeia

    print("== verificar_cadeia.py — PoUW Fase 3 (verificador frio da cadeia, pouw-cadeia-demo-v1) ==")
    print(f"INICIO {agora_utc()}")
    import platform
    print(f"Python {platform.python_version()} | PyTorch {torch.__version__} | NumPy {np.__version__}")
    print(f"Import do PyTorch + verificar_fase2: {t_import:.3f} s (à parte da verificação)")
    print(f"Diretório da cadeia: {dir_cadeia} | apenas bloco: {args.apenas_bloco or 'todos'}")
    print(f"Checagens: C0 (gênese/spec) + C1–C8 por bloco (ver docstring)")

    res = verificar_cadeia_completa(dir_cadeia, forward_torch64, apenas_bloco=args.apenas_bloco, verbose=True)

    n_ok = sum(1 for r in res["blocos"] if r["ok"])
    print()
    print("-- RESUMO --")
    print(f"Gênese/spec (C0): {'OK' if res['genesis_ok'] else 'FALHOU'}")
    print(f"Blocos verificados: {res['n_blocos_verificados']} | válidos: {n_ok}")
    if res["blocos"]:
        tempos = [r["tempo_s"] for r in res["blocos"]]
        print(f"Tempo por bloco: min {min(tempos):.6f} s | máx {max(tempos):.6f} s | soma {sum(tempos):.6f} s")
    print(f"TEMPO TOTAL DE VERIFICAÇÃO (carga do JSON -> último PSNR, sem imports): {res['tempo_verificacao_s']:.6f} s")
    print(f"Tempo total do processo (incl. import do PyTorch): {time.perf_counter() - t0_total:.6f} s")
    print(f"RESULTADO: {'CADEIA VÁLIDA (código 0)' if res['cadeia_ok'] else 'CADEIA INVÁLIDA (código 1)'}")
    print(f"FIM {agora_utc()}")
    raise SystemExit(0 if res["cadeia_ok"] else 1)


if __name__ == "__main__":
    main()
