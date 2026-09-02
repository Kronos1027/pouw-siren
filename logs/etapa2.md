# Etapa 2 — Treino SIREN em CPU (log de execução)

- Diretório de trabalho: `/home/z/my-project/download/pouw_fase1`
- Script: `treinar.py` (implementação própria, arquitetura/inicialização adaptadas do repo público de referência https://github.com/vsitzmann/siren — Sitzmann et al., NeurIPS 2020, arXiv:2006.09661)
- Decisões declaradas: ver docstring de `treinar.py` (rede 2→128→128→128→1, sin(30x), Adam lr=1e-4, batch completo, PSNR alvo 40 dB avaliado a cada 100 épocas OU 5000 épocas, coords [0,1]→[-1,1], seed da rede derivada do SHA-256 do desafio, threads=default)
- Definição de "tempo de treino": `perf_counter` da construção do modelo até a avaliação final (imports e carga do .npy fora da medida; tempo total do script reportado à parte)

## Smoke test (documentado; fora do protocolo das 3 seeds)

Comando:
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; time python3 -u treinar.py desafio_b0f90ffe.npy --max-epocas 300 --saida _fumaca_teste.pt; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa2_smoke_test.txt
```

Output bruto:
```
2026-09-02 01:42:16 UTC
== treinar.py — PoUW Fase 1 (SIREN em CPU) ==
Desafio: desafio_b0f90ffe.npy
SHA-256 do arquivo de desafio: f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8
Grade: 64x64 (4096 pontos) | pico (max-min) do campo: 6.918026
Seed de inicializacao da rede (derivada do SHA-256 do desafio): 4057987820
Arquitetura: 2 -> [128, 128, 128] -> 1, ativacao sin(30*x) (SIREN)
Criterio de parada: PSNR >= 40.0 dB (avaliado a cada 100 epocas) OU 300 epocas
Otimizador: Adam, lr=0.0001 | batch completo (4096 amostras/epoca)
Threads de CPU (torch, default): 2
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.150 s
Total de parametros do modelo: 33537
[epoca   100] PSNR=  49.63 dB | perda=5.314047e-04 | t=    4.31 s

Parada: PSNR 49.63 dB >= 40.0 dB na epoca 100
PSNR final (avaliacao pos-treino, float64): 49.6253 dB
Total de epocas executadas: 100
Tempo de treino (perf_counter; da construcao do modelo a avaliacao final): 4.314289 s
Tempo de salvamento da receita (torch.save + SHA-256): 0.004638 s
Tempo total do script (perf_counter, incl. imports): 5.471496 s
Receita salva em: _fumaca_teste.pt
SHA-256 da receita: 332bbb5fec6a77d6e75e34736d5582adf067a99b85642321d63171fdab4fa4e8

real	0m6.358s
user	0m6.341s
sys	0m0.965s
2026-09-02 01:42:23 UTC
```
Obs.: o artefato `_fumaca_teste.pt` foi removido após a checagem (comando `rm -f _fumaca_teste.pt`, documentado no início do log da execução oficial da seed 001).

## Execuções oficiais (3 seeds, critério declarado: PSNR >= 40 dB OU 5000 épocas)

Comando (seed 001; seeds 002/003 idênticos trocando o .npy de entrada):
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; time python3 -u treinar.py desafio_b0f90ffe.npy --max-epocas 5000 --alvo-psnr 40; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa2_treino_seed001.txt
```

### Output bruto — teste-seed-001 (desafio_b0f90ffe.npy)
```
2026-09-02 01:42:52 UTC
== treinar.py — PoUW Fase 1 (SIREN em CPU) ==
Desafio: desafio_b0f90ffe.npy
SHA-256 do arquivo de desafio: f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8
Grade: 64x64 (4096 pontos) | pico (max-min) do campo: 6.918026
Seed de inicializacao da rede (derivada do SHA-256 do desafio): 4057987820
Arquitetura: 2 -> [128, 128, 128] -> 1, ativacao sin(30*x) (SIREN)
Criterio de parada: PSNR >= 40.0 dB (avaliado a cada 100 epocas) OU 5000 epocas
Otimizador: Adam, lr=0.0001 | batch completo (4096 amostras/epoca)
Threads de CPU (torch, default): 2
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.112 s
Total de parametros do modelo: 33537
[epoca   100] PSNR=  49.63 dB | perda=5.314047e-04 | t=    4.08 s

Parada: PSNR 49.63 dB >= 40.0 dB na epoca 100
PSNR final (avaliacao pos-treino, float64): 49.6253 dB
Total de epocas executadas: 100
Tempo de treino (perf_counter; da construcao do modelo a avaliacao final): 4.087526 s
Tempo de salvamento da receita (torch.save + SHA-256): 0.004087 s
Tempo total do script (perf_counter, incl. imports): 5.206024 s
Receita salva em: receita_b0f90ffe.pt
SHA-256 da receita: 6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81

real	0m5.976s
user	0m6.046s
sys	0m0.969s
2026-09-02 01:42:58 UTC
```

### Output bruto — teste-seed-002 (desafio_d037aef4.npy)
```
2026-09-02 01:43:22 UTC
== treinar.py — PoUW Fase 1 (SIREN em CPU) ==
Desafio: desafio_d037aef4.npy
SHA-256 do arquivo de desafio: b62112ff4df7db352dda5b052886d7f3f9d10d91dd7c93f8ec0022019d19eb41
Grade: 64x64 (4096 pontos) | pico (max-min) do campo: 6.757977
Seed de inicializacao da rede (derivada do SHA-256 do desafio): 3055620863
Arquitetura: 2 -> [128, 128, 128] -> 1, ativacao sin(30*x) (SIREN)
Criterio de parada: PSNR >= 40.0 dB (avaliado a cada 100 epocas) OU 5000 epocas
Otimizador: Adam, lr=0.0001 | batch completo (4096 amostras/epoca)
Threads de CPU (torch, default): 2
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.115 s
Total de parametros do modelo: 33537
[epoca   100] PSNR=  48.39 dB | perda=6.742500e-04 | t=    3.93 s

Parada: PSNR 48.39 dB >= 40.0 dB na epoca 100
PSNR final (avaliacao pos-treino, float64): 48.3896 dB
Total de epocas executadas: 100
Tempo de treino (perf_counter; da construcao do modelo a avaliacao final): 3.928582 s
Tempo de salvamento da receita (torch.save + SHA-256): 0.003957 s
Tempo total do script (perf_counter, incl. imports): 5.049725 s
Receita salva em: receita_d037aef4.pt
SHA-256 da receita: 29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e

real	0m5.822s
user	0m6.150s
sys	0m0.588s
2026-09-02 01:43:28 UTC
```

### Output bruto — teste-seed-003 (desafio_8b457d0a.npy)
```
2026-09-02 01:43:33 UTC
== treinar.py — PoUW Fase 1 (SIREN em CPU) ==
Desafio: desafio_8b457d0a.npy
SHA-256 do arquivo de desafio: 4f4d6d5723049abc2b554f46464141e05805f51354df210e2f6824bb741f4bdc
Grade: 64x64 (4096 pontos) | pico (max-min) do campo: 6.260589
Seed de inicializacao da rede (derivada do SHA-256 do desafio): 1330474327
Arquitetura: 2 -> [128, 128, 128] -> 1, ativacao sin(30*x) (SIREN)
Criterio de parada: PSNR >= 40.0 dB (avaliado a cada 100 epocas) OU 5000 epocas
Otimizador: Adam, lr=0.0001 | batch completo (4096 amostras/epoca)
Threads de CPU (torch, default): 2
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.101 s
Total de parametros do modelo: 33537
[epoca   100] PSNR=  49.26 dB | perda=4.731250e-04 | t=    4.01 s

Parada: PSNR 49.26 dB >= 40.0 dB na epoca 100
PSNR final (avaliacao pos-treino, float64): 49.2587 dB
Total de epocas executadas: 100
Tempo de treino (perf_counter; da construcao do modelo a avaliacao final): 4.010014 s
Tempo de salvamento da receita (torch.save + SHA-256): 0.004211 s
Tempo total do script (perf_counter, incl. imports): 5.117255 s
Receita salva em: receita_8b457d0a.pt
SHA-256 da receita: 98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea

real	0m5.875s
user	0m5.751s
sys	0m1.163s
2026-09-02 01:43:38 UTC
```

## Execução EXTRA (fora do protocolo das 3 seeds): escalonamento de dificuldade (alvo 60 dB)

Comando:
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; echo "EXECUCAO EXTRA (fora do protocolo das 3 seeds): alvo de qualidade elevado para 60 dB"; time python3 -u treinar.py desafio_b0f90ffe.npy --max-epocas 5000 --alvo-psnr 60 --saida receita_extra_60db_b0f90ffe.pt; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa2_extra_alvo60db.txt
```

Output bruto:
```
2026-09-02 01:44:07 UTC
EXECUCAO EXTRA (fora do protocolo das 3 seeds): alvo de qualidade elevado para 60 dB
== treinar.py — PoUW Fase 1 (SIREN em CPU) ==
Desafio: desafio_b0f90ffe.npy
SHA-256 do arquivo de desafio: f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8
Grade: 64x64 (4096 pontos) | pico (max-min) do campo: 6.918026
Seed de inicializacao da rede (derivada do SHA-256 do desafio): 4057987820
Arquitetura: 2 -> [128, 128, 128] -> 1, ativacao sin(30*x) (SIREN)
Criterio de parada: PSNR >= 60.0 dB (avaliado a cada 100 epocas) OU 5000 epocas
Otimizador: Adam, lr=0.0001 | batch completo (4096 amostras/epoca)
Threads de CPU (torch, default): 2
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.081 s
Total de parametros do modelo: 33537
[epoca   100] PSNR=  49.63 dB | perda=5.314047e-04 | t=    3.69 s
[epoca   200] PSNR=  54.57 dB | perda=1.685940e-04 | t=    5.27 s
[epoca   300] PSNR=  57.37 dB | perda=8.815475e-05 | t=    6.77 s
[epoca   400] PSNR=  59.34 dB | perda=5.591847e-05 | t=    8.24 s
[epoca   500] PSNR=  60.87 dB | perda=3.929142e-05 | t=    9.74 s

Parada: PSNR 60.87 dB >= 60.0 dB na epoca 500
PSNR final (avaliacao pos-treino, float64): 60.8704 dB
Total de epocas executadas: 500
Tempo de treino (perf_counter; da construcao do modelo a avaliacao final): 9.739328 s
Tempo de salvamento da receita (torch.save + SHA-256): 0.002587 s
Tempo total do script (perf_counter, incl. imports): 10.825039 s
Receita salva em: receita_extra_60db_b0f90ffe.pt
SHA-256 da receita: e474d0377947a4e78821af6d250ed58b0e951061875bfbd02840626e1c9558d9

real	0m11.610s
user	0m12.572s
sys	0m2.884s
2026-09-02 01:44:18 UTC
```
Motivo da execução extra: caracterizar como o tempo de treino escala com o alvo de qualidade (análogo ao "difficulty" do PoW). Mesmo desafio da seed 001: 40 dB → 100 épocas / 4.09 s; 60 dB → 500 épocas / 9.74 s.

## Checagem auxiliar 1 — determinismo de torch.save (fora do protocolo das 3 seeds)

Comando:
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; python3 -u checagem_torchsave.py; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa2_checagem_torchsave.txt
```

Output bruto:
```
2026-09-02 01:44:32 UTC
hash SHA-256 de _check1.pt: 1d61e031d843e5643c609946568da5022b2d6e5405d8b0bc85bbe2b7402be8a4
hash SHA-256 de _check2.pt: 3b711c30b2e3360b927ea0463916c13564136f425defa7d3f3cc808d6deb9f57
bytes dos arquivos identicos: False
conteudo (tensores) identico apos reload: True
2026-09-02 01:44:35 UTC
```
Conclusão: `torch.save` NÃO produz bytes reproduzíveis (o contêiner zip embute timestamp), embora o conteúdo recarregado seja idêntico. Isso explica por que o hash da receita do smoke test (`332bbb5f...`) diferiu do hash da execução oficial (`6b644937...`) com pesos idênticos.

## Checagem auxiliar 2 — determinismo do TREINO (fora do protocolo das 3 seeds)

Comando (re-treino da seed 001 em arquivo separado):
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; echo "RE-TREINO da seed 001 (mesmo comando, saida em _retreino_check.pt) para checagem de determinismo do treino"; time python3 -u treinar.py desafio_b0f90ffe.npy --max-epocas 5000 --alvo-psnr 40 --saida _retreino_check.pt; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa2_retreino_determinismo.txt
```

Output bruto (treino):
```
2026-09-02 01:44:45 UTC
RE-TREINO da seed 001 (mesmo comando, saida em _retreino_check.pt) para checagem de determinismo do treino
== treinar.py — PoUW Fase 1 (SIREN em CPU) ==
Desafio: desafio_b0f90ffe.npy
SHA-256 do arquivo de desafio: f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8
Grade: 64x64 (4096 pontos) | pico (max-min) do campo: 6.918026
Seed de inicializacao da rede (derivada do SHA-256 do desafio): 4057987820
Arquitetura: 2 -> [128, 128, 128] -> 1, ativacao sin(30*x) (SIREN)
Criterio de parada: PSNR >= 40.0 dB (avaliado a cada 100 epocas) OU 5000 epocas
Otimizador: Adam, lr=0.0001 | batch completo (4096 amostras/epoca)
Threads de CPU (torch, default): 2
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.137 s
Total de parametros do modelo: 33537
[epoca   100] PSNR=  49.63 dB | perda=5.314047e-04 | t=    3.80 s

Parada: PSNR 49.63 dB >= 40.0 dB na epoca 100
PSNR final (avaliacao pos-treino, float64): 49.6253 dB
Total de epocas executadas: 100
Tempo de treino (perf_counter; da construcao do modelo a avaliacao final): 3.800254 s
Tempo de salvamento da receita (torch.save + SHA-256): 0.003952 s
Tempo total do script (perf_counter, incl. imports): 4.943725 s
Receita salva em: _retreino_check.pt
SHA-256 da receita: fb23e5dd3f36778fd651c39dd83b50d614b2ada12d169e00cefa4e4564a3fd58

real	0m5.715s
user	0m5.741s
sys	0m0.888s
2026-09-02 01:44:50 UTC
```

Comando (comparação tensor a tensor):
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; python3 -u checagem_retreino.py; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa2_checagem_retreino.txt
```

Output bruto (comparação):
```
2026-09-02 01:45:05 UTC
hash do arquivo receita_b0f90ffe.pt : 6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81
hash do arquivo _retreino_check.pt : fb23e5dd3f36778fd651c39dd83b50d614b2ada12d169e00cefa4e4564a3fd58
mesmas chaves de estado: True
  0.bias: bit-a-bit identico=True | max|diff|=0.000e+00
  0.weight: bit-a-bit identico=True | max|diff|=0.000e+00
  2.bias: bit-a-bit identico=True | max|diff|=0.000e+00
  2.weight: bit-a-bit identico=True | max|diff|=0.000e+00
  4.bias: bit-a-bit identico=True | max|diff|=0.000e+00
  4.weight: bit-a-bit identico=True | max|diff|=0.000e+00
  6.bias: bit-a-bit identico=True | max|diff|=0.000e+00
  6.weight: bit-a-bit identico=True | max|diff|=0.000e+00
TODOS os tensores bit-a-bit identicos: True
max diff global entre pesos: 0.000e+00
meta a (epocas, psnr, parada): 100 49.62530573074805 alvo_psnr
meta b (epocas, psnr, parada): 100 49.62530573074805 alvo_psnr
2026-09-02 01:45:07 UTC
```
Conclusão: o treino é bit-a-bit determinístico nesta máquina (todos os tensores idênticos, max diff = 0). Os hashes dos arquivos .pt diferem apenas por causa do timestamp do contêiner zip (checagem auxiliar 1). Artefatos temporários (`_retreino_check.pt`, `_check1.pt`, `_check2.pt`) removidos após a checagem.

## Hashes e tamanhos dos artefatos da Etapa 2

Comando:
```bash
cd /home/z/my-project/download/pouw_fase1 && rm -f _retreino_check.pt _check1.pt _check2.pt && echo "artefatos temporarios removidos: _retreino_check.pt _check1.pt _check2.pt" && { echo "=== SHA-256 DAS RECEITAS (3 oficiais + 1 extra 60dB) ==="; sha256sum receita_b0f90ffe.pt receita_d037aef4.pt receita_8b457d0a.pt receita_extra_60db_b0f90ffe.pt; echo; echo "=== TAMANHOS DOS ARTEFATOS (bytes) ==="; stat -c "%s %n" desafio_b0f90ffe.npy desafio_d037aef4.npy desafio_8b457d0a.npy receita_b0f90ffe.pt receita_d037aef4.pt receita_8b457d0a.pt; } 2>&1 | tee logs/raw/etapa2_hashes_receitas.txt
```

Output bruto:
```
artefatos temporarios removidos: _retreino_check.pt _check1.pt _check2.pt
=== SHA-256 DAS RECEITAS (3 oficiais + 1 extra 60dB) ===
6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81  receita_b0f90ffe.pt
29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e  receita_d037aef4.pt
98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea  receita_8b457d0a.pt
e474d0377947a4e78821af6d250ed58b0e951061875bfbd02840626e1c9558d9  receita_extra_60db_b0f90ffe.pt

=== TAMANHOS DOS ARTEFATOS (bytes) ===
32896 desafio_b0f90ffe.npy
32896 desafio_d037aef4.npy
32896 desafio_8b457d0a.npy
138379 receita_b0f90ffe.pt
138379 receita_d037aef4.pt
138379 receita_8b457d0a.pt
```

## Resumo numérico da Etapa 2 (valores copiados dos outputs acima)

| Seed | Receita | Tempo de treino (s) | PSNR final (dB) | Épocas | SHA-256 da receita |
|---|---|---|---|---|---|
| teste-seed-001 | receita_b0f90ffe.pt | 4.087526 | 49.6253 | 100 | 6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81 |
| teste-seed-002 | receita_d037aef4.pt | 3.928582 | 48.3896 | 100 | 29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e |
| teste-seed-003 | receita_8b457d0a.pt | 4.010014 | 49.2587 | 100 | 98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea |
| (extra, 60 dB) | receita_extra_60db_b0f90ffe.pt | 9.739328 | 60.8704 | 500 | e474d0377947a4e78821af6d250ed58b0e951061875bfbd02840626e1c9558d9 |
