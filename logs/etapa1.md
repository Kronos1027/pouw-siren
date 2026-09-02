# Etapa 1 — Gerador de desafio determinístico (log de execução)

- Diretório de trabalho: `/home/z/my-project/download/pouw_fase1`
- Script: `desafio.py` (código fornecido no prompt, com 2 correções mínimas — ver seção "Divergências e correções")
- Log bruto completo: `logs/raw/etapa1_*.txt`
- Protocolo: todos os números abaixo vêm dos outputs colados; nada foi estimado.

## Divergências e correções (reportadas conforme protocolo anti-fabricação)

O código do prompt, transcrito verbatim, falhou 2 vezes. Erros completos abaixo.

### Tentativa 1 — erro `np.PI`

Comando:
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; time python3 -u desafio.py teste-seed-001; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa1_desafio_seed001_tentativa1_FALHA.txt
```

Output bruto:
```
2026-09-02 01:39:24 UTC
Traceback (most recent call last):
  File "/home/z/my-project/download/pouw_fase1/desafio.py", line 15, in <module>
    campo, hash_seed = gerar_desafio(seed)
                       ^^^^^^^^^^^^^^^^^^^
  File "/home/z/my-project/download/pouw_fase1/desafio.py", line 9, in gerar_desafio
    campo = sum(np.sin(f * x * np.PI) * np.cos(f * y * np.PI) for f in freqs)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/z/my-project/download/pouw_fase1/desafio.py", line 9, in <genexpr>
    campo = sum(np.sin(f * x * np.PI) * np.cos(f * y * np.PI) for f in freqs)
                               ^^^^^
  File "/home/z/.venv/lib/python3.12/site-packages/numpy/__init__.py", line 414, in __getattr__
    raise AttributeError("module {!r} has no attribute "
AttributeError: module 'numpy' has no attribute 'PI'. Did you mean: 'pi'?

real	0m0.247s
user	0m0.278s
sys	0m0.021s
2026-09-02 01:39:25 UTC
```

Correção aplicada (linha 9): `np.PI` → `np.pi` (2 ocorrências). A fórmula pretendida `sin(f·x·π)·cos(f·y·π)` permanece idêntica.

### Tentativa 2 — erro `h.hexdigest()` sobre `bytes`

Comando (idêntico ao acima, seed 001; as seeds 002 e 003 falharam do mesmo modo — outputs em `logs/raw/etapa1_desafio_seed00{2,3}_tentativa2_FALHA.txt`):
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; time python3 -u desafio.py teste-seed-001; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa1_desafio_seed001_tentativa2_FALHA.txt
```

Output bruto:
```
2026-09-02 01:39:38 UTC
Traceback (most recent call last):
  File "/home/z/my-project/download/pouw_fase1/desafio.py", line 15, in <module>
    campo, hash_seed = gerar_desafio(seed)
                       ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/z/my-project/download/pouw_fase1/desafio.py", line 10, in gerar_desafio
    return campo, h.hexdigest()
                  ^^^^^^^^^^^
AttributeError: 'bytes' object has no attribute 'hexdigest'

real	0m0.230s
user	0m0.275s
sys	0m0.019s
2026-09-02 01:39:38 UTC
```

Motivo: `h = hashlib.sha256(seed.encode()).digest()` já retorna `bytes`; `bytes` não possui `.hexdigest()`.
Correção aplicada (linha 10): `return campo, h.hex()` — `sha256(x).digest().hex()` devolve exatamente a mesma string que `sha256(x).hexdigest()`, e a linha do RNG (`int.from_bytes(h[:8], "big")`) continua válida sem alteração.

## Tentativa 3 — execução oficial (3 seeds, código corrigido)

Comando (seed 001; seeds 002 e 003 idênticos trocando o argumento):
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; time python3 -u desafio.py teste-seed-001; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa1_desafio_seed001.txt
```

### Output bruto — teste-seed-001
```
2026-09-02 01:40:08 UTC
Seed: teste-seed-001
Hash da seed: b0f90ffe7b211056a12d016de15d344e29806c432d7533529fe2a45932161155
Desafio salvo em: desafio_b0f90ffe.npy
Shape: (64, 64), min=-3.2951, max=3.6230

real	0m0.399s
user	0m0.435s
sys	0m0.046s
2026-09-02 01:40:08 UTC
```

### Output bruto — teste-seed-002
```
2026-09-02 01:40:09 UTC
Seed: teste-seed-002
Hash da seed: d037aef40ded7b449e3b951277c865cdac6a3c8a63c05b637655b49636382208
Desafio salvo em: desafio_d037aef4.npy
Shape: (64, 64), min=-3.4455, max=3.3124

real	0m0.227s
user	0m0.280s
sys	0m0.017s
2026-09-02 01:40:10 UTC
```

### Output bruto — teste-seed-003
```
2026-09-02 01:40:09 UTC
Seed: teste-seed-003
Hash da seed: 8b457d0a924fd7915c39ddea62fbf6a8ae777f4e7a919d7ead1372e8416a4ca6
Desafio salvo em: desafio_8b457d0a.npy
Shape: (64, 64), min=-2.9020, max=3.3586

real	0m0.353s
user	0m0.382s
sys	0m0.044s
2026-09-02 01:40:09 UTC
```

## Checagem de determinismo + hashes SHA-256 dos artefatos

Comando:
```bash
cd /home/z/my-project/download/pouw_fase1 && { echo "=== HASH ANTES DA RE-EXECUCAO (checagem de determinismo) ==="; sha256sum desafio_b0f90ffe.npy; echo; echo "=== RE-EXECUTANDO desafio.py teste-seed-001 ==="; python3 -u desafio.py teste-seed-001; echo; echo "=== HASH DEPOIS ==="; sha256sum desafio_b0f90ffe.npy; echo; echo "=== SHA-256 DOS 3 ARTEFATOS DA ETAPA 1 ==="; sha256sum desafio_b0f90ffe.npy desafio_d037aef4.npy desafio_8b457d0a.npy; } 2>&1 | tee logs/raw/etapa1_determinismo_e_hashes.txt
```

Output bruto:
```
=== HASH ANTES DA RE-EXECUCAO (checagem de determinismo) ===
f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8  desafio_b0f90ffe.npy

=== RE-EXECUTANDO desafio.py teste-seed-001 ===
Seed: teste-seed-001
Hash da seed: b0f90ffe7b211056a12d016de15d344e29806c432d7533529fe2a45932161155
Desafio salvo em: desafio_b0f90ffe.npy
Shape: (64, 64), min=-3.2951, max=3.6230

=== HASH DEPOIS ===
f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8  desafio_b0f90ffe.npy

=== SHA-256 DOS 3 ARTEFATOS DA ETAPA 1 ===
f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8  desafio_b0f90ffe.npy
b62112ff4df7db352dda5b052886d7f3f9d10d91dd7c93f8ec0022019d19eb41  desafio_d037aef4.npy
4f4d6d5723049abc2b554f46464141e05805f51354df210e2f6824bb741f4bdc  desafio_8b457d0a.npy
```

Conclusão da checagem: o hash do arquivo antes e depois da re-execução é **idêntico** — o gerador é determinístico nesta máquina/ambiente (numpy 2.1.3).

## Resumo dos artefatos da Etapa 1

| Seed | Hash da seed (SHA-256 da string) | Arquivo | SHA-256 do arquivo |
|---|---|---|---|
| teste-seed-001 | b0f90ffe7b211056a12d016de15d344e29806c432d7533529fe2a45932161155 | desafio_b0f90ffe.npy | f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8 |
| teste-seed-002 | d037aef40ded7b449e3b951277c865cdac6a3c8a63c05b637655b49636382208 | desafio_d037aef4.npy | b62112ff4df7db352dda5b052886d7f3f9d10d91dd7c93f8ec0022019d19eb41 |
| teste-seed-003 | 8b457d0a924fd7915c39ddea62fbf6a8ae777f4e7a919d7ead1372e8416a4ca6 | desafio_8b457d0a.npy | 4f4d6d5723049abc2b554f46464141e05805f51354df210e2f6824bb741f4bdc |
