# PoUW via Compressão Neural — Relatório da Fase 1 (CPU-only)

**Data de execução:** 2026-09-02 (timestamps UTC em cada log)
**Local:** `/home/z/my-project/download/pouw_fase1/` (todos os artefatos permanecem salvos lá)
**Protocolo anti-fabricação:** nenhum número deste relatório foi estimado; todos vêm de comandos executados cujos outputs brutos estão colados em `logs/etapa1.md`, `logs/etapa2.md`, `logs/etapa3.md` e em `logs/raw/*.txt`. Tempos internos vêm de `time.perf_counter()`; tempos de parede, do `time` do bash. Todo artefato tem SHA-256 reportado.

---

## 1. Objetivo

Medir a razão `tempo_de_treino / tempo_de_verificação` para a compressão de um sinal 2D sintético (64×64) com uma SIREN pequena, inteiramente em CPU, documentando tudo de forma reproduzível e verificável de forma independente.

## 2. Especificações da máquina onde rodou (output colado)

`lscpu` (colado integralmente; também em `logs/raw/lscpu.txt`):

```
Architecture:                       x86_64
CPU op-mode(s):                     32-bit, 64-bit
Address sizes:                      52 bits physical, 57 bits virtual
Byte Order:                         Little Endian
CPU(s):                             2
On-line CPU(s) list:                0,1
Vendor ID:                          GenuineIntel
Model name:                         Intel(R) Xeon(R) Processor
CPU family:                         6
Model:                              173
Thread(s) per core:                 1
Core(s) per socket:                 2
Socket(s):                          1
Stepping:                           1
BogoMIPS:                           6400.00
Flags:                              fpu vme pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss ht syscall nx pdpe1gb rdtscp lm constant_tsc rep_good nopl xtopology nonstop_tsc cpuid tsc_known_freq pni pclmulqdq ssse3 fma cx16 pdcm pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm 3dnowprefetch cpuid_fault invpcid_single ssbd ibrs ibpb stibp ibrs_enhanced fsgsbase tsc_adjust bmi1 smep bmi2 erms invpcid avx512f avx512dq rdseed adx smap avx512ifma clflushopt clwb avx512cd sha_ni avx512bw avx512vl xsaveopt xsavec xgetbv xsaves avx_vnni avx512_bf16 wbnoinvd avx512vbmi umip pku waitpkg avx512_vbmi2 avx512_vnni avx512_bitalg avx512_vpopcntdq la57 rdpid cldemote movdir64b fsrm md_clear serialize tsxldtrk amx_bf16 avx512_fp16 amx_tile amx_int8 arch_capabilities
Hypervisor vendor:                  KVM
Virtualization type:                full
L1d cache:                          48 KiB (1 instance)
L1i cache:                          64 KiB (1 instance)
L2 cache:                           2 MiB (1 instance)
L3 cache:                           504 MiB (1 instance)
NUMA node(s):                       1
NUMA node0 CPU(s):                  0,1
Vulnerability Itlb multihit:        Not affected
Vulnerability L1tf:                 Not affected
Vulnerability Mds:                  Not affected
Vulnerability Meltdown:             Not affected
Vulnerability Mmio stale data:      Not affected
Vulnerability Retbleed:             Not affected
Vulnerability Spec rstack overflow: Not affected
Vulnerability Spec store bypass:    Mitigation; Speculative Store Bypass disabled via prctl and seccomp
Vulnerability Spectre v1:           Mitigation; usercopy/swapgs barriers and __user pointer sanitization
Vulnerability Spectre v2:           Vulnerable: eIBRS with unprivileged eBPF
Vulnerability Srbds:                Not affected
Vulnerability Tsx async abort:      Not affected
```

`free -h` (em `logs/raw/free.txt`):

```
               total        used        free        shared  buff/cache   available
Mem:           4.1Gi       439Mi       3.6Gi        44Ki       157Mi       3.6Gi
Swap:             0B          0B          0B
```

Resumo: **Intel Xeon, 2 vCPUs (KVM), 4,1 GiB RAM, sem GPU** (`cuda_disponivel: False`).
Software: **Python 3.12.14, NumPy 2.1.3, PyTorch 2.14.0+cpu** (instalado na sessão via `python3 -m pip install torch --index-url https://download.pytorch.org/whl/cpu`; log em `logs/raw/pip_install_torch.txt`). `nproc` = 2; threads default do torch = 2.

## 3. Decisões declaradas (tudo que afeta os números)

- **Desafio:** campo 64×64, soma de 4 modos `sin(f·x·π)·cos(f·y·π)` com `f ~ U(2,10)` gerados por RNG PCG64 semeada pelos 8 primeiros bytes do SHA-256 da string-seed (código do prompt, com 2 correções mínimas — ver Limitações, itens 1 e 2).
- **Rede (SIREN):** `2 → 128 → 128 → 128 → 1`, ativação `sin(30·x)`; inicialização conforme repo oficial `github.com/vsitzmann/siren` (primeira camada `U(-1/n_in, 1/n_in)`, ocultas `U(±√(6/n_in)/30)`, saída/bias default do PyTorch); 33.537 parâmetros; coordenadas mapeadas `[0,1] → [-1,1]`.
- **Treino:** Adam, lr = 1e-4 (default do repo oficial), batch completo (4096 amostras/época). Seed de inicialização derivada do SHA-256 do arquivo do desafio.
- **Critério de parada:** PSNR ≥ 40 dB (avaliado a cada 100 épocas) OU 5000 épocas.
- **PSNR:** `20·log10(pico/RMSE)`, `pico = max−min` do desafio original (float64), RMSE em float64.
- **"Tempo de treino":** `perf_counter` da construção do modelo até a avaliação final (exclui imports e carga do .npy; tempo total do script reportado à parte em cada log).
- **"Tempo de verificação":** `perf_counter` da carga da receita ao PSNR final, em processo novo, com **1 thread** fixada (determinismo; escolha conservadora que só pode tornar a verificação mais lenta). Exclui o import do PyTorch (~1,1 s), reportado à parte.
- Verificação 100% independente: `verificar.py` duplica o construtor da rede e lê arquitetura/pesos do `.pt` salvo em disco.

## 4. Tabela-resumo (as 3 seeds do protocolo)

| Seed | Hash desafio | Tempo treino (s) | Tempo verificação (s) | Razão treino/verificação | PSNR | SHA-256 da receita |
|---|---|---|---|---|---|---|
| teste-seed-001 | b0f90ffe7b211056a12d016de15d344e29806c432d7533529fe2a45932161155 | 4.087526 | 0.013060 | 313.0 | 49.6253 | 6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81 |
| teste-seed-002 | d037aef40ded7b449e3b951277c865cdac6a3c8a63c05b637655b49636382208 | 3.928582 | 0.015376 | 255.5 | 48.3896 | 29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e |
| teste-seed-003 | 8b457d0a924fd7915c39ddea62fbf6a8ae777f4e7a919d7ead1372e8416a4ca6 | 4.010014 | 0.014319 | 280.0 | 49.2587 | 98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea |

Notas sobre a tabela: "Hash desafio" é o SHA-256 da string-seed (impresso pelo `desafio.py`); o SHA-256 do **arquivo** `.npy` de cada desafio está no inventário (seção 6). Tempos copiados verbatim das linhas `Tempo de treino ...: X s` e `TEMPO TOTAL DE VERIFICAÇÃO ...: X s` dos outputs brutos (`logs/etapa2.md`, `logs/etapa3.md`). PSNR é o medido pelo verificador independente (o de treino conferiu até a precisão impressa). Razões derivadas por comando explícito (output em `logs/raw/inventario_final_e_razoes.txt`): 313.0 / 255.5 / 280.0. Todas as 3 seeds pararam no critério de alvo (PSNR ≥ 40 dB) na época 100.

## 5. Observações complementares (execuções extras, rotuladas; fora da tabela)

- **Escalonamento de dificuldade (seed 001, alvo 60 dB):** 500 épocas, tempo de treino 9.739328 s, PSNR 60.8704 dB, receita `receita_extra_60db_b0f90ffe.pt` (SHA-256 `e474d0377947a4e78821af6d250ed58b0e951061875bfbd02840626e1c9558d9`). Mesmo desafio: 40 dB → 100 épocas/4,09 s; 60 dB → 500 épocas/9,74 s. Output completo em `logs/etapa2.md`.
- **Determinismo do gerador:** re-execução de `desafio.py teste-seed-001` produziu arquivo com hash idêntico (`f1dffaec...`, antes e depois). Output em `logs/etapa1.md`.
- **Determinismo do treino:** re-treino da seed 001 produziu pesos bit-a-bit idênticos (8/8 tensores, max diff = 0.000e+00). Output em `logs/etapa2.md`.
- **Determinismo da verificação:** re-execução de `verificar.py` sobre a mesma receita, em processo novo, reproduziu a reconstrução com hash idêntico (`b2fe66eb...`, antes e depois). Output em `logs/etapa3.md`.

## 6. Inventário de artefatos (SHA-256 colado de `logs/raw/inventario_final_e_razoes.txt`; tamanhos medidos via `stat` em `logs/raw/tamanhos_finais.txt`)

| Arquivo | Papel | Tamanho (bytes) | SHA-256 |
|---|---|---|---|
| desafio.py | gerador (código do prompt, 2 correções) | 817 | 12d36c1400c3ab6401951869c5cd455df9c02c04ede610c2a8ca480540c72da1 |
| treinar.py | treino SIREN (CPU) | 9821 | 553f7322c80fb836661364931e4674e88e73bfda8246bec9fe3baea63399880b |
| verificar.py | verificador independente | 7457 | 00ed53ee16e2c9fb1e58afe129d7af5ba3b8ee3150d53e8d41809809f95f4725 |
| checagem_torchsave.py | checagem auxiliar | 1361 | 3e38fa1af2fb8573b724bc2f006a18ce1ab2aa06712684ff8ccff3cdb3e47fdb |
| checagem_retreino.py | checagem auxiliar | 1782 | e97335e7c9696811d8832576681e4a7ecb30466d341493ad3f496d03d703c744 |
| desafio_b0f90ffe.npy | desafio seed 001 | 32896 | f1dffaec613a609ed110fed9ce131c101f0989781d33004813f8c34ac2720bd8 |
| desafio_d037aef4.npy | desafio seed 002 | 32896 | b62112ff4df7db352dda5b052886d7f3f9d10d91dd7c93f8ec0022019d19eb41 |
| desafio_8b457d0a.npy | desafio seed 003 | 32896 | 4f4d6d5723049abc2b554f46464141e05805f51354df210e2f6824bb741f4bdc |
| receita_b0f90ffe.pt | receita seed 001 | 138379 | 6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81 |
| receita_d037aef4.pt | receita seed 002 | 138379 | 29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e |
| receita_8b457d0a.pt | receita seed 003 | 138379 | 98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea |
| receita_extra_60db_b0f90ffe.pt | receita extra (60 dB) | 138661 | e474d0377947a4e78821af6d250ed58b0e951061875bfbd02840626e1c9558d9 |
| reconstrucao_b0f90ffe.npy | ejeção seed 001 | 16512 | b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38 |
| reconstrucao_d037aef4.npy | ejeção seed 002 | 16512 | d1bc83b90115562dedafa38a16d5949274e36fb0af4abab092b9e75b6dc6676f |
| reconstrucao_8b457d0a.npy | ejeção seed 003 | 16512 | ce66e7427a51fa89e803fb8959262d74d0f86c5d91d611475280ef0efa279385 |

Logs (não hashados individualmente; conteúdo integral em texto): `logs/etapa1.md`, `logs/etapa2.md`, `logs/etapa3.md`, `logs/raw/*.txt`.

## 7. Comandos exatos usados, na ordem (prontos para copiar e rodar)

Executados a partir de `/home/z/my-project/download/pouw_fase1`. Os comandos abaixo são os núcleos exatos; nas execuções reais cada um foi embrulhado em `{ date -u ...; time <comando>; date -u ...; } 2>&1 | tee logs/raw/<arquivo>.txt` para capturar timestamp e output bruto (a forma embrulhada integral está em `logs/etapaN.md`).

```bash
# (0) Ambiente (torch CPU não estava instalado; instalado na sessão)
python3 -m pip install torch --index-url https://download.pytorch.org/whl/cpu

# (1) Etapa 1 — gerar os 3 desafios
python3 -u desafio.py teste-seed-001
python3 -u desafio.py teste-seed-002
python3 -u desafio.py teste-seed-003
sha256sum desafio_*.npy

# (2) Etapa 2 — treinar (critério: PSNR >= 40 dB OU 5000 épocas)
time python3 -u treinar.py desafio_b0f90ffe.npy --max-epocas 5000 --alvo-psnr 40
time python3 -u treinar.py desafio_d037aef4.npy --max-epocas 5000 --alvo-psnr 40
time python3 -u treinar.py desafio_8b457d0a.npy --max-epocas 5000 --alvo-psnr 40
sha256sum receita_*.pt

# (3) Etapa 3 — verificar de forma independente (processo novo, 1 thread)
time python3 -u verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy
time python3 -u verificar.py receita_d037aef4.pt desafio_d037aef4.npy
time python3 -u verificar.py receita_8b457d0a.pt desafio_8b457d0a.npy
sha256sum reconstrucao_*.npy
```

Extras documentados (mesma forma, com `--saida` explícito): smoke test (`--max-epocas 300`), alvo 60 dB (`--alvo-psnr 60`), re-treino de determinismo, checagens `checagem_torchsave.py` / `checagem_retreino.py`, re-execuções de determinismo do desafio e da verificação — todos com comando e output integral em `logs/`.

## 8. Como conferir de forma independente (o plano anunciado do leitor)

```bash
cd pouw_fase1
sha256sum receita_b0f90ffe.pt        # deve devolver 6b64493713accd20...f033b81
python3 -u verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy
# deve imprimir: SHA-256 da reconstrução: b2fe66eb1eb7f1744...c96202f38
#                PSNR (reconstrução vs desafio): 49.6253 dB
sha256sum reconstrucao_b0f90ffe.npy  # deve devolver b2fe66eb1eb7f1744...c96202f38
```

Na **mesma** máquina/ambiente (CPU, PyTorch, NumPy), os hashes devem bater bit-a-bit — foi assim que a checagem de determinismo passou aqui. Em **outra** máquina, o PSNR deve permanecer essencialmente idêntico, mas o hash da reconstrução pode divergir nos últimos bits (ver Limitações, item 4) — nesse caso compare o PSNR e o hash da **receita** (arquivo em si, que não muda ao ser copiado).

## 9. Limitações observadas (divergências, dúvidas e tudo que não saiu como esperado)

1. **Bug 1 no código do prompt (`np.PI`):** o NumPy não possui `PI` (possui `pi`); a primeira execução falhou com `AttributeError` (traceback completo em `logs/etapa1.md`). Correção mínima aplicada preservando a fórmula.
2. **Bug 2 no código do prompt (`h.hexdigest()`):** `h` já era `bytes` (resultado de `.digest()`); `bytes` não tem `.hexdigest()`. Falhou nas 3 seeds com traceback completo registrado. Correção mínima: `h.hex()` (string idêntica à que `hexdigest()` produziria).
3. **`torch.save` não é byte-reproduzível:** salvar o MESMO objeto duas vezes produz arquivos com hashes diferentes (o contêiner zip embute timestamp; evidência: `1d61e031... ≠ 3b711c30...` com conteúdo recarregado idêntico). Implicação prática: o SHA-256 do `.pt` valida a **integridade do arquivo** (a cópia que você tem é a que eu hashueei), mas **não** serve como prova de re-treino reproduzível — a âncora correta de reprodutibilidade é o hash da **reconstrução `.npy`** (`np.save` não usa zip; bytes determinísticos para o mesmo array). Foi por isso que o hash da receita do smoke test divergiu do hash da execução oficial, com pesos idênticos.
4. **Determinismo entre máquinas não é garantido:** nesta máquina, treino e verificação se mostraram bit-a-bit determinísticos (checagens documentadas). Porém o forward pass em float32 usa operações vetoriais (AVX-512 etc.) cujo arredondamento pode diferir entre CPUs/BLAS/versões de libm nos últimos bits — o que basta para mudar um hash. Se você rodar `verificar.py` na sua máquina e o hash da reconstrução divergir, **não é necessariamente erro meu nem seu**: confira o PSNR (deve permanecer 49.6253 dB) e o hash da receita. Para um PoUW real, isso recomenda para a fase 2: comparação tolerante (PSNR ≥ alvo com margem) ou hash de saída **quantizada** (fixed-point), que elimina a sensibilidade a último bit.
5. **"Compressão" neste escala não economiza bytes:** a receita (138.379 B) é ~4,2× MAIOR que o desafio (32.896 B); a reconstrução float32 ocupa 16.512 B. A fase 1 mede a **assimetria de tempo**, não a razão de compressão; a relação de tamanho muda com sinais/grades maiores e quantização de pesos.
6. **O alvo de 40 dB é fácil para esta família de desafios:** atingido na primeira avaliação (época 100) nas 3 seeds — o treino medido é o "mínimo para produzir receita válida" sob o critério declarado, não um treino longo. A granularidade de avaliação (a cada 100 épocas) limita a resolução do verdadeiro ponto de convergência. A execução extra com 60 dB (500 épocas, 9,74 s) mostra que o custo é parametrizável pelo alvo — o análogo do "difficulty" —, mas o escalonamento é suave, não exponencial como no PoW de hash.
7. **O import do PyTorch (~1,1 s) domina a verificação em processo frio:** o wall-clock real de cada `verificar.py` foi ~1,1–1,6 s, dos quais ~13–15 ms é o trabalho útil medido. As razões da tabela excluem imports **dos dois lados** (simétrico e declarado). Com processos frios dos dois lados, a razão cairia para ~2,5–4×; num nó de consenso real, o runtime estaria pré-carregado e a razão relevante volta a ser a da tabela.
8. **Assimetria de threads favorável à honestidade:** treino usou 2 threads (default), verificação fixou 1 thread por determinismo — ou seja, a verificação medida é mais LENTA do que poderia ser; a razão reportada é conservadora (um piso).
9. **Máquina modesta e amostra pequena:** 2 vCPUs; 1 execução oficial por seed (sem repetições estatísticas dos tempos; a determinística do resultado foi checada na seed 001). Tempos absolutos da ordem de segundos — a métrica da fase é a razão, não o absoluto.
10. **Artefato de exibição:** a linha final `[meta da receita] ...` apareceu truncada (`eta da receita] ...`) na exibição do terminal da sessão; verificado por busca no arquivo de log que o registro em disco está íntegro.
11. **PSNR de treino vs. verificação:** idênticos até a precisão impressa (ex.: 49.6253 dB) — a diferença de threads (2 no treino, 1 na verificação) não alterou o resultado impresso nesta máquina.

## 10. Conclusão factual

Sob os critérios declarados (PSNR ≥ 40 dB, batch completo, Adam 1e-4, SIREN 2→128→128→128→1), nesta máquina (Xeon 2 vCPU, CPU-only): o treino custou **3,93–4,09 s** e a verificação independente completa (carga + forward + hash + PSNR) custou **13–15 ms**, isto é, **razão treino/verificação de 255,5 a 313,0** (mediação `perf_counter`, sem imports, verificação em 1 thread). A assimetria caro-de-produzir/trivial-de-checar existe e é mensurável; a receita produzida é um artefato reaproveitável (a ejeção reproduz o sinal a 48,4–49,6 dB de PSNR), ao contrário do hash descartável do PoW tradicional. Os obstáculos identificados para uma fase 2 são: (a) determinismo bit-a-bit entre máquinas heterogêneas (solução candidata: saída quantizada/fixed-point), (b) custo de import/runtime em processo frio, e (c) parametrização de dificuldade com escalonamento mais agressivo que o observado (alvos mais altos, redes maiores, grades maiores).
