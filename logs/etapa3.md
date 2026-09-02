# Etapa 3 — Verificador independente (log de execução)

- Diretório de trabalho: `/home/z/my-project/download/pouw_fase1`
- Script: `verificar.py` — processo NOVO a cada execução; carrega a receita do disco (arquitetura + pesos), não compartilha nada com a etapa 2; forward com **1 thread** (determinismo, escolha conservadora); reconstrução salva em `.npy` (float32) e hashada
- Definição de "tempo de verificação": `perf_counter` da carga da receita ao PSNR final (fases A–D abaixo), SEM o tempo de import do PyTorch (reportado à parte)
- Nota: na saída exibida no terminal da sessão, a última linha (`[meta da receita] ...`) apareceu ocasionalmente truncada como `eta da receita]` — verificado via grep que o arquivo de log cru contém a linha íntegra (é artefato de exibição, não do registro)

## Execuções oficiais (3 receitas)

Comando (seed 001; seeds 002/003 idênticos trocando os arquivos):
```bash
cd /home/z/my-project/download/pouw_fase1 && { date -u +"%Y-%m-%d %H:%M:%S UTC"; time python3 -u verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy; date -u +"%Y-%m-%d %H:%M:%S UTC"; } 2>&1 | tee logs/raw/etapa3_verif_seed001.txt
```

### Output bruto — receita_b0f90ffe.pt (seed 001)
```
2026-09-02 01:47:34 UTC
== verificar.py — PoUW Fase 1 (verificação independente em CPU) ==
Receita: receita_b0f90ffe.pt
SHA-256 da receita (recalculado aqui; conferir com o reportado no treino): 6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81
Desafio de referência: desafio_b0f90ffe.npy
Threads de CPU (fixado em 1 por determinismo): 1
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.106 s

Arquitetura lida da receita: 2 -> [128, 128, 128] -> 1, omega_0=30.0
Total de parâmetros do modelo: 33537

-- Fases medidas (perf_counter) --
A) Carga da receita (torch.load + montagem da rede): 0.003793 s
B) Forward pass / ejeção (4096 pontos): 0.008567 s
C) Salvamento da reconstrução + SHA-256: 0.000331 s
D) PSNR contra o desafio original: 0.000368 s

TEMPO TOTAL DE VERIFICAÇÃO (carga -> hash -> PSNR, sem imports): 0.013060 s
Tempo total do processo (incl. import do PyTorch): 1.119653 s

Reconstrução salva em: reconstrucao_b0f90ffe.npy
SHA-256 da reconstrução: b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38
PSNR (reconstrução vs desafio): 49.6253 dB
RMSE: 2.284110e-02 | erro máximo absoluto: 1.002134e-01 | pico (max-min): 6.918026
[meta da receita] épocas: 100 | PSNR de treino: 49.62530573074805 | parada: alvo_psnr

real    0m1.640s
user    0m1.579s
sys     0m0.124s
2026-09-02 01:47:36 UTC
```

### Output bruto — receita_d037aef4.pt (seed 002)
```
2026-09-02 01:47:58 UTC
== verificar.py — PoUW Fase 1 (verificação independente em CPU) ==
Receita: receita_d037aef4.pt
SHA-256 da receita (recalculado aqui; conferir com o reportado no treino): 29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e
Desafio de referência: desafio_d037aef4.npy
Threads de CPU (fixado em 1 por determinismo): 1
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.115 s

Arquitetura lida da receita: 2 -> [128, 128, 128] -> 1, omega_0=30.0
Total de parâmetros do modelo: 33537

-- Fases medidas (perf_counter) --
A) Carga da receita (torch.load + montagem da rede): 0.003695 s
B) Forward pass / ejeção (4096 pontos): 0.010910 s
C) Salvamento da reconstrução + SHA-256: 0.000379 s
D) PSNR contra o desafio original: 0.000389 s

TEMPO TOTAL DE VERIFICAÇÃO (carga -> hash -> PSNR, sem imports): 0.015376 s
Tempo total do processo (incl. import do PyTorch): 1.130857 s

Reconstrução salva em: reconstrucao_d037aef4.npy
SHA-256 da reconstrução: d1bc83b90115562dedafa38a16d5949274e36fb0af4abab092b9e75b6dc6676f
PSNR (reconstrução vs desafio): 48.3896 dB
RMSE: 2.572376e-02 | erro máximo absoluto: 1.168166e-01 | pico (max-min): 6.757977
[meta da receita] épocas: 100 | PSNR de treino: 48.38964354132196 | parada: alvo_psnr

real    0m1.657s
user    0m1.578s
sys     0m0.135s
2026-09-02 01:47:59 UTC
```

### Output bruto — receita_8b457d0a.pt (seed 003)
```
2026-09-02 01:48:03 UTC
== verificar.py — PoUW Fase 1 (verificação independente em CPU) ==
Receita: receita_8b457d0a.pt
SHA-256 da receita (recalculado aqui; conferir com o reportado no treino): 98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea
Desafio de referência: desafio_8b457d0a.npy
Threads de CPU (fixado em 1 por determinismo): 1
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.116 s

Arquitetura lida da receita: 2 -> [128, 128, 128] -> 1, omega_0=30.0
Total de parâmetros do modelo: 33537

-- Fases medidas (perf_counter) --
A) Carga da receita (torch.load + montagem da rede): 0.003561 s
B) Forward pass / ejeção (4096 pontos): 0.010074 s
C) Salvamento da reconstrução + SHA-256: 0.000332 s
D) PSNR contra o desafio original: 0.000351 s

TEMPO TOTAL DE VERIFICAÇÃO (carga -> hash -> PSNR, sem imports): 0.014319 s
Tempo total do processo (incl. import do PyTorch): 1.130653 s

Reconstrução salva em: reconstrucao_8b457d0a.npy
SHA-256 da reconstrução: ce66e7427a51fa89e803fb8959262d74d0f86c5d91d611475280ef0efa279385
PSNR (reconstrução vs desafio): 49.2587 dB
RMSE: 2.156159e-02 | erro máximo absoluto: 1.040967e-01 | pico (max-min): 6.260589
[meta da receita] épocas: 100 | PSNR de treino: 49.2586868752562 | parada: alvo_psnr

real    0m1.729s
user    0m1.676s
sys     0m0.131s
2026-09-02 01:48:04 UTC
```

## Checagem de determinismo da verificação (mesmo procedimento que o leitor fará)

Comando:
```bash
cd /home/z/my-project/download/pouw_fase1 && { echo "=== HASH DA RECONSTRUCAO ANTES DA RE-VERIFICACAO ==="; sha256sum reconstrucao_b0f90ffe.npy; echo; echo "=== RE-EXECUTANDO verificar.py (mesma receita, processo novo) ==="; date -u +"%Y-%m-%d %H:%M:%S UTC"; time python3 -u verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy; date -u +"%Y-%m-%d %H:%M:%S UTC"; echo; echo "=== HASH DA RECONSTRUCAO DEPOIS ==="; sha256sum reconstrucao_b0f90ffe.npy; } 2>&1 | tee logs/raw/etapa3_determinismo_verificacao.txt
```

Output bruto:
```
=== HASH DA RECONSTRUCAO ANTES DA RE-VERIFICACAO ===
b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38  reconstrucao_b0f90ffe.npy

=== RE-EXECUTANDO verificar.py (mesma receita, processo novo) ===
2026-09-02 01:48:11 UTC
== verificar.py — PoUW Fase 1 (verificação independente em CPU) ==
Receita: receita_b0f90ffe.pt
SHA-256 da receita (recalculado aqui; conferir com o reportado no treino): 6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81
Desafio de referência: desafio_b0f90ffe.npy
Threads de CPU (fixado em 1 por determinismo): 1
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.621 s

Arquitetura lida da receita: 2 -> [128, 128, 128] -> 1, omega_0=30.0
Total de parâmetros do modelo: 33537

-- Fases medidas (perf_counter) --
A) Carga da receita (torch.load + montagem da rede): 0.003638 s
B) Forward pass / ejeção (4096 pontos): 0.010719 s
C) Salvamento da reconstrução + SHA-256: 0.000414 s
D) PSNR contra o desafio original: 0.000384 s

TEMPO TOTAL DE VERIFICAÇÃO (carga -> hash -> PSNR, sem imports): 0.015158 s
Tempo total do processo (incl. import do PyTorch): 1.636792 s

Reconstrução salva em: reconstrucao_b0f90ffe.npy
SHA-256 da reconstrução: b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38
PSNR (reconstrução vs desafio): 49.6253 dB
RMSE: 2.284110e-02 | erro máximo absoluto: 1.002134e-01 | pico (max-min): 6.918026
[meta da receita] épocas: 100 | PSNR de treino: 49.62530573074805 | parada: alvo_psnr

real    0m2.127s
user    0m2.033s
sys     0m0.173s
2026-09-02 01:48:13 UTC

=== HASH DA RECONSTRUCAO DEPOIS ===
b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38  reconstrucao_b0f90ffe.npy
```

Conclusão: verificação reproduzível bit-a-bit nesta máquina (hash da reconstrução idêntico antes/depois, em processos independentes).

## Inventário final de hashes + razões (derivadas por comando)

Comando:
```bash
cd /home/z/my-project/download/pouw_fase1 && { echo "=== INVENTARIO FINAL: SHA-256 DE TODOS OS ARTEFATOS ==="; sha256sum desafio.py treinar.py verificar.py checagem_torchsave.py checagem_retreino.py desafio_b0f90ffe.npy desafio_d037aef4.npy desafio_8b457d0a.npy receita_b0f90ffe.pt receita_d037aef4.pt receita_8b457d0a.pt receita_extra_60db_b0f90ffe.pt reconstrucao_b0f90ffe.npy reconstrucao_d037aef4.npy reconstrucao_8b457d0a.npy; echo; echo "=== RAZOES treino/verificacao (derivadas por comando dos valores medidos) ==="; python3 -c "
t1, v1 = 4.087526, 0.013060
t2, v2 = 3.928582, 0.015376
t3, v3 = 4.010014, 0.014319
print(f'seed001: {t1}/{v1} = {t1/v1:.1f}')
print(f'seed002: {t2}/{v2} = {t2/v2:.1f}')
print(f'seed003: {t3}/{v3} = {t3/v3:.1f}')
"; } 2>&1 | tee logs/raw/inventario_final_e_razoes.txt
```

Output bruto:
```
=== INVENTARIO FINAL: SHA-256 DE TODOS OS ARTEFATOS ===
12d36c1400c3ab6401951869c5cd455df9c02c04ede610c2a8ca480540c72da1  desafio.py
553f7322c80fb836661364931e4674e88e73bfda8246bec9fe3baea63399880b  treinar.py
00ed53ee16e2c9fb1e58afe129d7af5ba3b8ee3150d53e8d41809809f95f4725  verificar.py
3e38fa1af2fb8573b724bc2f006a18ce1ab2aa06712684ff8ccff3cdb3e47fdb  checagem_torchsave.py
e97335e7c9696811d8832576681e4a7ecb30466d341493ad3f496d03d703c744  checagem_retreino.py
f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8  desafio_b0f90ffe.npy
b62112ff4df7db352dda5b052886d7f3f9d10d91dd7c93f8ec0022019d19eb41  desafio_d037aef4.npy
4f4d6d5723049abc2b554f46464141e05805f51354df210e2f6824bb741f4bdc  desafio_8b457d0a.npy
6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81  receita_b0f90ffe.pt
29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e  receita_d037aef4.pt
98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea  receita_8b457d0a.pt
e474d0377947a4e78821af6d250ed58b0e951061875bfbd02840626e1c9558d9  receita_extra_60db_b0f90ffe.pt
b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38  reconstrucao_b0f90ffe.npy
d1bc83b90115562dedafa38a16d5949274e36fb0af4abab092b9e75b6dc6676f  reconstrucao_d037aef4.npy
ce66e7427a51fa89e803fb8959262d74d0f86c5d91d611475280ef0efa279385  reconstrucao_8b457d0a.npy

=== RAZOES treino/verificacao (derivadas por comando dos valores medidos) ===
seed001: 4.087526/0.01306 = 313.0
seed002: 3.928582/0.015376 = 255.5
seed003: 4.010014/0.014319 = 280.0
```

## Resumo numérico da Etapa 3 (valores copiados dos outputs acima)

| Seed | Tempo de verificação (s) | SHA-256 da reconstrução | PSNR verificado (dB) | Hash da receita recalculado confere? |
|---|---|---|---|---|
| teste-seed-001 | 0.013060 | b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38 | 49.6253 | Sim (6b644937...) |
| teste-seed-002 | 0.015376 | d1bc83b90115562dedafa38a16d5949274e36fb0af4abab092b9e75b6dc6676f | 48.3896 | Sim (29682d84...) |
| teste-seed-003 | 0.014319 | ce66e7427a51fa89e803fb8959262d74d0f86c5d91d611475280ef0efa279385 | 49.2587 | Sim (98c123fd...) |
