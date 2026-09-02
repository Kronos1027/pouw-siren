# PoUW via Compressão Neural — Relatório da Fase 2 (CPU-only)

**Data de execução:** 2026-09-02 (timestamps UTC em cada log)
**Local:** `/home/z/my-project/download/pouw_fase1/` (repo público: https://github.com/Kronos1027/pouw-siren)
**Protocolo anti-fabricação:** idêntico ao da Fase 1 — nenhum número deste relatório foi estimado; todos vêm de comandos executados cujos outputs brutos estão em `fase2/logs/raw/*.txt`. Tempos internos: `time.perf_counter()`; tempos de parede: `time` do bash. Todo artefato novo tem SHA-256 em `fase2/hashes_fase2.sha256` (verificável com `sha256sum -c`). A única exceção declarada: os números do teste cross-CPU do **usuário** (seção 2) são dados REPORTADOS POR ELE via chat, executados na máquina dele — e estão rotulados como tal em todo lugar em que aparecem.

---

## 1. Objetivo da Fase 2

Resolver a limitação nº 4 da Fase 1 — "determinismo entre máquinas não é garantido" — transformando o hash de saída em uma regra de **consenso cross-CPU** e medir se a **dificuldade** continua parametrizável. As perguntas, na ordem:

1. **E1:** o hash quantizado sobrevive a caminhos aritméticos genuinamente diferentes (mesmos pesos, BLAS/ordem de soma/precisão distintas)?
2. **E2+E3:** com que margem estatística? Onde exatamente ele quebra?
3. **E4:** quando a dificuldade (alvo de PSNR) sobe, o custo cresce do lado do treino (caro) ou também do lado da verificação (barato)?
4. **E5:** qual o custo real do ajuste fino de dificuldade exponencial (bits-zero de prefixo) sobre o compromisso quantizado?

## 2. Contexto: a validação cross-CPU do usuário (dado externo, rotulado)

O usuário baixou o repo, rodou a verificação da Fase 1 na própria CPU e reportou (via chat, 2026-09-02; **não executado nesta máquina**):

| Métrica | Valor no repo (Xeon, Fase 1) | Valor na máquina do usuário | Resultado |
|---|---|---|---|
| SHA-256 da receita (seed 001) | `6b644937…` | `6b644937…` | **idêntico bit-a-bit** |
| PSNR | 49.6253 dB | 49.6253 dB | **idêntico** |
| SHA-256 da reconstrução float32 | `b2fe66eb…` | `83fc3a76…` | **divergiu** |
| Diferença máx. absoluta entre os floats | — | **7.15e-07** | confirmou a limitação 4 |

A previsão da Fase 1 (seção 8 + limitação 4 do `relatorio_fase1.md`) se confirmou: o PSNR e o hash da receita são âncoras robustas; o hash de floats crus não é. A Fase 2 existe para consertar exatamente isso — e o número `7.15e-07` do usuário é usado como **calibração** do stress test E2.

## 3. Máquina e software

Idênticos à Fase 1 (mesma sessão de VM persistente): Intel Xeon 2 vCPUs (KVM), 4,1 GiB RAM, sem GPU, `lscpu` integral em `logs/raw/lscpu.txt` (Fase 1). Python 3.12.14, NumPy 2.1.3, PyTorch 2.14.0+cpu, git 2.47.3. Os treinos usam 2 threads (default do torch); a verificação fixa 1 thread (conservador, herança da Fase 1).

## 4. A especificação pouw-quant-v1 (o entregável central da Fase 2)

Implementada em `fase2/quantizar.py` (spec canônica + CLI). Regra completa (minerador e verificador devem seguir à risca):

```
Entradas: R = reconstrução (H×W) em FLOAT64 (ver abaixo), lo/hi = min/max do
DESAFIO original (.npy — âncora de bytes), B = 16 (recomendado) ou 8.

s    = (2^B − 1) / (hi − lo)              # divisão IEEE-754 float64
q_f  = (R − lo) · s                        # float64, broadcasting
q    = clip(rint(q_f), 0, 2^B − 1)         # rint = meio-para-par (np.rint)
bytes = q.astype('>u2' | '>u1').tobytes()  # big-endian, ordem C (row-major)
hash  = SHA-256( "pouw-quant-v1|B=<B>|<H>x<W>|" ‖ bytes )
```

**Regra de consenso proposta (fase2-v1):** um "bloco" `{desafio, receita, compromisso, alvo}` é válido se (1) `sha256(receita.pt)` bate com o comprometido; (2) o `sha256_desafio` gravado na meta da receita bate com o hash do `.npy`; (3) o hash quantizado B=16 da reconstrução **float64** bate com o compromisso; (4) `PSNR ≥ alvo`. O `verificar_fase2.py` implementa as 4 checagens e devolve código de saída 0/1.

**Por que float64 OBRIGATÓRIO no forward de comprometimento (e1, e2, e3 abaixo medem isto):**
- A aritmética de quantização (subtração, multiplicação, divisão, rint — escalares float64) é corretamente arredondada pelo IEEE-754 → **bit-idêntica entre CPUs** dado o mesmo `R`. A única porta de entrada de variação é o próprio `R` (forward da rede).
- O forward float32 diverge ~1e-07 entre caminhos aritméticos (E1) e ~7e-07 entre CPUs (dado do usuário) → vira bins da grade B=16 (E2: 100% de virada).
- O forward float64 diverge ~1e-15 entre caminhos (E1, medido) → fica ~5 ordens de grandeza abaixo da primeira fronteira sensível medida (E3: dist mín = 7.3e-10) → **bins idênticos** (E1: HD=0 em todos os pares, 3 seeds).
- Se minerador e verificador usarem precisões diferentes (float32 vs float64), os hashes **divergem** (E1: HD 9–21) — logo a spec exige float64 **dos dois lados**.

**Custo da quantização (PSNR, medido no smoke test, seed 001):** B=16: 49.6253 → 49.6252 dB (custo 0,0001 dB); B=8: 49.6253 → 49.1348 dB (custo 0,49 dB). B=16 é o recomendado: margem enorme sem custo perceptível.

**Comportamentos declarados da spec:** valores fora de `[lo, hi]` são clipados (no seed 8b457d0a, 2 dos 4096 elementos ficam fora e são "imunes" a ruído — nunca viram); `np.rint` usa meio-para-par; bytes big-endian para eliminar ambiguidade de endianness entre máquinas; o prefixo ASCII na pré-imagem separa domínios (B e forma não colidem entre versões).

## 5. E1 — experimento_caminhos.py: robustez a caminhos aritméticos reais

7 caminhos de forward para a MESMA receita: `p1` torch float32 1 thread (= caminho oficial da Fase 1), `p2` torch float32 2 threads, `p3` NumPy float32 (OpenBLAS — BLAS/libm diferente do torch), `p4` NumPy float32 com soma em blocos de 16 (ordem de redução forçada), `p5` torch float64 1 thread (spec), `p6` NumPy float64, `p7` NumPy float64 em blocos.

**Continuidade com a Fase 1:** `p1` reproduziu bit-a-bit os 3 arquivos `reconstrucao_*.npy` oficiais (`np.array_equal` = True ×3) — o experimento replica fielmente o caminho publicado.

| caminho | seed b0f90ffe (max\|Δ\| / HD16) | seed d037aef4 | seed 8b457d0a | HD B=8 |
|---|---|---|---|---|
| p1 torch32 1t (baseline) | 0 / 0 | 0 / 0 | 0 / 0 | 0 |
| p2 torch32 2t | 0 / 0 | 0 / 0 | 0 / 0 | 0 |
| p3 numpy32 | 7.153e-07 / 5 | 7.153e-07 / 4 | 7.153e-07 / 1 | 0 |
| p4 numpy32 bloc16 | 1.192e-06 / 6 | 8.345e-07 / 5 | 8.345e-07 / 3 | 0 |
| p5 torch64 1t (spec) | 2.094e-06 / 15 | 2.008e-06 / 21 | 1.623e-06 / 9 | 0 |
| p6 numpy64 | 2.094e-06 / 15 | 2.008e-06 / 21 | 1.623e-06 / 9 | 0 |
| p7 numpy64 bloc16 | 2.094e-06 / 15 | 2.008e-06 / 21 | 1.623e-06 / 9 | 0 |

(HD16 = distância de Hamming da quantização B=16 contra a do p1; qualquer HD>0 = hash diferente. Hashes completos dos 7 caminhos × 3 seeds no log bruto.)

**A prova central (família float64, pares entre caminhos):**

| par | max\|Δ\| (3 seeds) | quantizações B=16 |
|---|---|---|
| p5 vs p6 | 8.882e-16 … 8.882e-16 | **idênticas, HD=0** ×3 seeds |
| p5 vs p7 | 1.332e-15 … 1.776e-15 | **idênticas, HD=0** ×3 seeds |
| p6 vs p7 | 1.332e-15 … 1.776e-15 | **idênticas, HD=0** ×3 seeds |

Observações honestas: (a) `p2 == p1` bit-a-bit — nesta CPU, só mudar o nº de threads NÃO altera os bits (o GEMM paraleliza por linhas); a variação real veio de trocar de biblioteca (p3/p6) e de forçar ordem de soma (p4/p7); (b) o `max|Δ|` de p3 contra p1 (**7.153e-07**) coincide com o valor medido pelo usuário entre as duas CPUs (**7.15e-07**) — o proxy do E1 reproduz a magnitude do fenômeno real; (c) p5/p6/p7 divergem de p1 por ~2e-06 — essa é a distância float32↔float64, e é o motivo de a spec exigir float64 **dos dois lados** (minerador que computar o compromisso em float32 produz hash diferente: HD 9–21).

## 6. E2+E3 — experimento_ruido.py: fronteiras e stress estatístico

**E3 (geometria):** distância mínima de um valor à fronteira mais próxima da grade, por seed: B=16: 3.553e-09 / 1.415e-08 / 7.276e-10; B=8: 3.422e-06 / 1.236e-05 / 3.383e-06. Mediana ~2.5e-05 (B=16).

**E2 (stress):** ruído uniforme ±ε adicionado à reconstrução, 2000 ensaios por ponto, varredura de 1e-16 a 7.15e-07. Taxa de ensaios com hash diferente (baseline float64, B=16):

| ε | seed b0f90ffe | seed d037aef4 | seed 8b457d0a |
|---|---|---|---|
| ≤ 1e-10 | 0/2000 | 0/2000 | 0/2000 |
| 1e-09 | 0/2000 | 0/2000 | 249/2000 |
| 1e-08 | 627/2000 | 0/2000 | 1396/2000 |
| 1e-07 | 1382/2000 | 1958/2000 | 1792/2000 |
| 7.15e-07 (calibração do usuário) | 2000/2000 | 2000/2000 | 2000/2000 |

Em B=8, zero viradas em TODOS os pontos, incluindo ε=7.15e-07 (porém com margem fina — ver limitações).

**Calibração com o dado do usuário (baseline float32, o "mundo sem spec float64"):** ε=7.15e-07 → B=16: **2000/2000 ensaios viram** (HD médio ~15, máx 30); ε=2.1e-06 (pior caso E1 float32↔float64) → 2000/2000 (HD máx 65). B=8: 0/2000 nos dois pontos.

**Teoria × medição (e correção documentada):** a 1ª versão da fórmula teórica de flips usava P(\|ruído\|>d) bilateral e superestimava por exatamente 2× — um bin só vira quando o ruído cruza a fronteira NO sentido que aponta para ela (probabilidade unicaudal). As MEDIÇÕES apontaram o erro (seed 8b457d0a, ε=1e-08: medido 1758 HD/2000 ensaios = 0,879/ensaio vs teoria antiga 1,755). A função foi corrigida, o experimento re-executado e a teoria passou a bater: 0,877 previsto vs 0,879 medido (idem nos demais pontos: 0,322 vs 0,314; 0,136 vs 0,125; 3,13 vs 3,15). A 1ª execução crua está preservada em `fase2/logs/raw/f2_e2_ruido_EXECUCAO1_TEORIA_ERRADA.txt`; a re-execução reproduziu as medições bit-a-bit (mesmos contadores, 627/1382/1958/249/… — o RNG `default_rng(20260902)` é determinístico), o que vale como checagem extra de reprodutibilidade.

## 7. E4 — experimento_dificuldade.py: dificuldade via alvo de PSNR

Mesmo desafio (seed 001), `treinar.py` da Fase 1 **intocado**, alvo variando; verificação com `verificar_fase2.py` (float64, 1 thread, B=16, `--alvo-psnr` = alvo do treino):

| alvo (dB) | épocas | PSNR treino | PSNR verif | treino (s) | verif (s) | **razão** | compromisso B=16 |
|---|---|---|---|---|---|---|---|
| 40 | 100 | 49.6253 | 49.6253 | 3.926989 | 0.020762 | **189.1×** | `93ad1d43…` |
| 45 | 100 | 49.6253 | 49.6253 | 3.969287 | 0.020699 | **191.8×** | `93ad1d43…` |
| 50 | 200 | 54.5661 | 54.5661 | 5.742811 | 0.021292 | **269.7×** | `d2614c08…` |
| 55 | 300 | 57.3701 | 57.3701 | 7.190010 | 0.021115 | **340.5×** | `9b4584f3…` |
| 60 | 500 | 60.8704 | 60.8704 | 11.598678 | 0.022495 | **515.6×** | `92b6fe06…` |
| 65 | 900 | 65.0004 | 65.0004 | 20.013393 | 0.022219 | **900.7×** | `18d77b20…` |

**Resultado central:** a dificuldade escala o lado CARO (treino: 3,9 → 20,0 s, 5,1×) enquanto o lado BARATO permanece constante (verificação: 0,0208 → 0,0222 s, +7%) → **a assimetria cresce com a dificuldade** (189× → 901×). As 6 receitas passam na regra de consenso (código 0). A curva é SUAVE (5 dB a mais ≈ +70–80% de épocas), não exponencial — o ajuste exponencial fica por conta do E5.

Determinismo adicional observado: (a) a receita alvo-60 treinada aqui produziu o MESMO compromisso e o MESMO array quantizado (byte-a-byte, `cbeacc70…`) da receita extra-60dB treinada na sessão da Fase 1; (b) idem alvo-40 vs receita oficial seed 001 (`bf583953…`); (c) alvo-40 e alvo-45 são idênticas entre si (o critério avalia a cada 100 épocas e ambas param na época 100 com os mesmos pesos).

## 8. E5 — experimento_prefixo.py: ajuste fino exponencial

Moagem de nonce sobre `SHA-256("pouw-bloco-demo-v1|" ‖ compromisso_hex ‖ "|" ‖ nonce)` até k bits zero. Compromisso real da seed 001 recomputado; taxa calibrada: **2.249 M hashes/s** (1 thread, Python puro). Nonces iniciais de `default_rng(20260902)`.

| k | 2^k (esperado) | tentativas mediana | tempo mediano |
|---|---|---|---|
| 8 | 256 | 54 | ~0 s |
| 12 | 4.096 | 3.175 | 0,002 s |
| 16 | 65.536 | 19.203 | 0,013 s |
| 20 | 1.048.576 | 729.104 | 0,468 s |
| 24 | 16.777.216 | 8.616.058 (1 ensaio) | 5,496 s |

Extrapolação **rotulada** (2^k / taxa; NÃO executada): k=28: 119 s · k=32: 1.909 s · k=36: 8,5 h · k=40: 5,7 dias.

Framing declarado no próprio output: moer nonce é queima de hash pura; o compromisso não é "moível" sem retreinar, então o prefixo serve só como ajuste fino exponencial por cima do trabalho útil — e o k teria de ser calibrado contra implementações C/GPU (ordens de grandeza mais rápidas que Python).

## 9. Compromissos oficiais da Fase 2 (as âncoras cross-CPU)

Gerados por `verificar_fase2.py` em processo frio, 1 thread, forward float64, B=16 (outputs brutos em `fase2/logs/raw/f2_verif_oficial_*.txt`):

| receita | PSNR | compromisso quantizado B=16 | sha256 do .npy quantizado | verif. (s) |
|---|---|---|---|---|
| receita_b0f90ffe.pt | 49.6253 | `93ad1d430c47b1a66f23b3da4cb758c9173d59ef1d72786b9e32afd557e517c8` | `bf583953…f9b3e5b` | 0.021214 |
| receita_d037aef4.pt | 48.3896 | `b4b6df845ea4861d8ed4071b463828dcdb40725ccdf471f8993c07031a0e20bd` | `85f094d1…70b2b43` | 0.021366 |
| receita_8b457d0a.pt | 49.2587 | `8397befca9f69cfcc9da2fc0e7719c8fa6b7c1cc5612a8236c6cc1e8fc544f4a` | `a9b51bed…da101` | 0.019897 |
| receita_extra_60db_b0f90ffe.pt | 60.8704 | `92b6fe06dde1cd1c07120eb6f8c96e3179d230a2e3ee0c01840106c1e54af0da` | `cbeacc70…e31dce` | 0.020286 |

(Tempos copiados verbatim da linha `TEMPO TOTAL DE VERIFICAÇÃO` de cada log bruto; os .npy quantizados correspondentes estão na raiz do repo e em `fase2/hashes_fase2.sha256` — hashes completos lá.) Além destas, as 6 receitas da varredura E4 (compromissos na seção 7) também são conferíveis.

## 10. Como conferir de forma independente (o teste cross-CPU de verdade)

Na **sua** máquina (a que divergiu na Fase 1):

```bash
git clone https://github.com/Kronos1027/pouw-siren.git && cd pouw-siren
sha256sum -c hashes.sha256               # 15 âncoras da Fase 1 → 15× OK
sha256sum -c fase2/hashes_fase2.sha256   # 23 âncoras da Fase 2 → 23× OK

python3 fase2/verificar_fase2.py receita_b0f90ffe.pt desafio_b0f90ffe.npy --alvo-psnr 40
# deve imprimir, entre outras linhas:
#   PSNR (reconstrução float64 vs desafio): 49.6253 dB
#   COMPROMISSO QUANTIZADO (pouw-quant-v1|B=16|64x64|): 93ad1d430c47b1a66f23b3da4cb758c9173d59ef1d72786b9e32afd557e517c8
#   RESULTADO: VÁLIDO (código 0)

sha256sum quantizada_b0f90ffe_u16.npy
# deve devolver: bf583953b977c0619cb290def6f59dfc8f8d7cab38fd20c9af16e1b2af9b3e5b
```

**Predição registrada ANTES de você rodar:** ao contrário do hash float32 da Fase 1 (que divergiu na sua CPU), o compromisso quantizado B=16 deve bater **bit-a-bit** na sua máquina — é essa a hipótese que a Fase 2 projeta e que E1+E2 tornam plausível. Se divergir, o PSNR continuará ~49.6253 e o relatório de qual elemento caiu em fronteira (dist mín B=16 = 7.3e-10 no pior seed) dirá exatamente o que aconteceu — nesse caso a spec sobe para um regime mais conservador (ex.: B=15 com margem, ou hash com distância de Hamming tolerada = 0 exigida apenas acima de um piso). **Nota de transparência: sua CPU (que mediu 7.15e-07 de diverência float32 contra o Xeon) deveria divergir ~1e-15 no float64 — 5 ordens de grandeza abaixo da pior fronteira sensível medida; mas "deveria" é previsão, e o teste é seu.**

## 11. Comandos exatos usados, na ordem

Executados a partir da raiz do repo (`/home/z/my-project/download/pouw_fase1`), cada um embrulhado em `{ date -u …; time <cmd>; date -u …; } 2>&1 | tee fase2/logs/raw/<arquivo>.txt`:

```bash
# smoke tests da spec e do verificador
python3 -u fase2/quantizar.py reconstrucao_b0f90ffe.npy desafio_b0f90ffe.npy --bits 16
python3 -u fase2/quantizar.py reconstrucao_b0f90ffe.npy desafio_b0f90ffe.npy --bits 8
python3 -u fase2/verificar_fase2.py receita_b0f90ffe.pt desafio_b0f90ffe.npy --alvo-psnr 40

# E1 — robustez a caminhos aritméticos (7 caminhos × 3 seeds)
python3 -u fase2/experimento_caminhos.py

# E2+E3 — fronteiras + stress (2 execuções: a 2ª após corrigir a fórmula teórica; ver §6)
python3 -u fase2/experimento_ruido.py

# E4 — varredura de dificuldade (treina 6 receitas e verifica cada uma)
python3 -u fase2/experimento_dificuldade.py

# E5 — moagem de prefixo
python3 -u fase2/experimento_prefixo.py receita_b0f90ffe.pt desafio_b0f90ffe.npy

# compromissos oficiais (3 seeds F1 + extra 60 dB)
python3 -u fase2/verificar_fase2.py receita_b0f90ffe.pt           desafio_b0f90ffe.npy --alvo-psnr 40
python3 -u fase2/verificar_fase2.py receita_d037aef4.pt           desafio_d037aef4.npy --alvo-psnr 40
python3 -u fase2/verificar_fase2.py receita_8b457d0a.pt           desafio_8b457d0a.npy --alvo-psnr 40
python3 -u fase2/verificar_fase2.py receita_extra_60db_b0f90ffe.pt desafio_b0f90ffe.npy --alvo-psnr 60

# âncoras
sha256sum <23 artefatos> > fase2/hashes_fase2.sha256 && sha256sum -c fase2/hashes_fase2.sha256
```

## 12. Limitações observadas (tudo que não saiu redondo)

1. **Bug próprio corrigido no E2 (documentado no §6):** fórmula teórica bilateral superestimava flips por 2×; detectado PELOS DADOS, corrigido, re-executado; 1ª execução preservada no log. O bug não afetou nenhuma medição (a coluna teórica não alimenta os ensaios).
2. **E1 é um PROXY, não um teste cross-CPU:** as divergências entre caminhos são reais (aritmética de verdade diferente), e a magnitude bateu com a do usuário (7.153e-07 vs 7.15e-07 — coincidência notável, mas coincidência de magnitude, não prova). A validação cross-CPU definitiva é o §10, executado pelo leitor.
3. **p2 == p1 (threads não mudam bits aqui):** o GEMM do torch paraleliza por linhas nesta CPU; a variação real veio de biblioteca diferente e ordem de soma forçada. Em outras arquiteturas o paralelismo PODERIA mudar bits — não observável nesta máquina.
4. **A margem do 65 dB é navalha:** o treino parou em 65.0004 dB contra alvo 65.0 (margem de 0,0004 dB); a verificação float64 concordou (65.0004 ≥ 65.0, válido), mas uma regra de produção deveria exigir colchão (ex.: parar só com alvo + 0,01 dB) para não depender de margem fina.
5. **B=8 tem margem fina:** absorveu todo o ruído testado (até 2.1e-06) com 0 viradas, mas a distância mínima à fronteira B=8 é 3.38e-06 — só ~1,6× o pior caso observado. A recomendação B=16 deve-se à margem (5 ordens) e ao custo de PSNR quase nulo (0,0001 dB vs 0,49 dB do B=8).
6. **torch.save segue não byte-reproduzível** (limitação 3 da Fase 1, persistente): os `.pt` novos provam integridade da cópia; a âncora de reprodutibilidade agora é o `.npy` QUANTIZADO — que é byte-reproduzível por construção quando os bins batem (demonstrado: alvo60 treinada hoje ≡ extra60 da Fase 1, byte-a-byte).
7. **Variância de tempo de parede entre sessões:** F1 40 dB: 4,087526 s vs E4 hoje: 3,926989 s (−4%); F1 60 dB: 9,739328 s vs hoje: 11,598678 s (+19%), mesmas épocas e mesmos PSNRs — VM compartilhada, variância de parede normal; os compromissos e PSNRs não mudaram.
8. **Import do PyTorch (~1,1 s) continua dominando a verificação fria** (limitação 7 da Fase 1, persistente); a verificação medida em float64 é ~1,5× a da Fase 1 (19–22 ms vs 13–15 ms) — ainda 2 ordens de grandeza abaixo do treino mais fácil.
9. **Amostras pequenas no E5:** 3 ensaios por k (1 no k=24); as medianas batem a ordem de 2^k, mas com variância grande de amostragem geométrica (3–252 tentativas para k=8).
10. **A extrapolação do E5 é aritmética, não medição** (rotulada como EXTRAPOLADO no output e no §8); e a taxa é de Python puro 1-thread — C/GPU seriam ordens de grandeza mais rápidos.
11. **Artefato de exibição persistente:** a linha `[meta da receita]` continua aparecendo truncada (`eta da receita]`) no terminal da sessão (limitação 10 da Fase 1); os arquivos de log em disco estão íntegros.
12. **A curva E4 vai até 65 dB/900 épocas/20 s:** não testamos alvos > 65 (max-épocas 5000 não foi atingido) nem redes/grades maiores — a Fase 1 já indicava o caminho (redes maiores, 3D, sinais reais) e permanece como próximo passo.

## 13. Conclusão factual

Sob o protocolo anti-fabricação (tudo medido, bruto e hashueado): a combinação **forward float64 + quantização fixed-point B=16 (pouw-quant-v1)** produziu compromissos **estáveis sob 7 caminhos aritméticos genuinamente distintos** (HD=0 em 9/9 pares float64, 3 seeds), **imunes a ruído até 1e-10** (6000 ensaios, 3 seeds; 1ª falha em 1e-09, e o resíduo float64 medido é ~1e-15), enquanto o float32 — mesmo quantizado — vira o hash em 100% dos ensaios ao nível de ruído cross-CPU calibrado pelo dado do usuário (7.15e-07). A dificuldade via alvo de PSNR escala **somente o lado caro** (razão treino/verificação cresceu de 189× a 901× no intervalo 40→65 dB), e o ajuste exponencial por prefixo foi medido até k=24 (5,5 s a 2,25 M hashes/s) com extrapolação rotulada. A hipótese central da Fase 2 — consenso determinístico cross-CPU via quantização — ficou **plausível e quantificada nesta máquina; a confirmação final depende do leitor rodar o §10 na própria CPU**, para o qual as âncoras (23 hashes + 4 compromissos oficiais) já estão publicadas.
