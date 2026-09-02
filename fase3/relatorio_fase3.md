# PoUW via Compressão Neural — Relatório da Fase 3 (CPU-only)

**Data de execução:** 2026-09-02, 03:43–03:53 UTC (timestamps em cada log bruto)
**Local:** `/home/z/my-project/download/pouw_fase1/` (repo público: https://github.com/Kronos1027/pouw-siren)
**Protocolo anti-fabricação:** idêntico ao das Fases 1–2 — nenhum número deste relatório foi estimado;
todos vêm de comandos executados cujos outputs brutos estão em `fase3/logs/raw/f3_*.txt`. Tempos internos:
`time.perf_counter()`; tempos de parede: `time` do bash. Todo artefato novo tem SHA-256 em
`fase3/hashes_fase3.sha256` (37 âncoras, verificáveis com `sha256sum -c`). Dado externo de terceiros:
nenhum nesta fase (o dado cross-CPU do usuário calibrou a Fase 2 e está lá, §2 do `relatorio_fase2.md`).

---

## 1. Objetivo da Fase 3

Fechar o arco do PoUW: a Fase 1 mediu a assimetria treino-caro/verificação-barata num bloco único; a
Fase 2 transformou o hash de saída em regra de consenso cross-CPU (`pouw-quant-v1`) e mediu a
dificuldade escalável. Faltava o **esqueleto de protocolo de cadeia** (candidato 3 do roadmap do README):
encadear blocos de modo que o trabalho seja **serial** (o desafio de cada bloco deriva do hash do bloco
anterior) e medir os custos dos dois lados nessa configuração — incluindo a **verificação em lote com
runtime persistente** (candidato 4 parcial), que responde à limitação persistente nº 7/8 (o import do
PyTorch domina a verificação fria). Cinco experimentos:

1. **E1:** minerar uma cadeia de 8 blocos (trabalho útil real por bloco, encadeado por hash).
2. **E2:** verificar a cadeia INTEIRA em processo frio e independente (9 checagens por bloco).
3. **E3:** custo da verificação em lote (runtime persistente) vs fria (cadeia e por bloco).
4. **E4:** o verificador REJEITA fraudes? (6 adulterações em cópias, código de saída 1 esperado).
5. **E5:** o re-treino é determinístico? (contraexemplo encontrado durante a mineração — investigado).

## 2. Contexto: o que a Fase 2 deixou pronto

A spec `pouw-quant-v1` (`fase2/quantizar.py`) provou, nesta máquina, que **forward float64 +
quantização fixed-point B=16** produz compromissos estáveis sob 7 caminhos aritméticos genuinamente
distintos (E1-F2, HD=0 em 9/9 pares) e imunes a ruído até 1e-10 (66.000 ensaios, E2-F2), enquanto o
float32 vira o hash em 100% dos ensaios ao nível de ruído cross-CPU calibrado pelo usuário (7.15e-07).
A Fase 3 **reutiliza essa spec sem alterá-la** — o compromisso de cada bloco é exatamente o
`hash_quantizado(quantizar(forward_float64, lo, hi, 16))` da Fase 2, e o verificador da cadeia chama o
mesmo `forward_torch64` do `verificar_fase2.py` (import, não cópia). A confirmação cross-CPU final
continua sendo externa (§11); a cadeia dá ao leitor um artefato muito mais rico para testar: 8 blocos
encadeados em vez de 1 bloco isolado.

## 3. Máquina e software

Idêntica às Fases 1–2 (mesma VM persistente): Intel Xeon 2 vCPUs (KVM), 4,1 GiB RAM, sem GPU,
`lscpu` integral em `logs/raw/lscpu.txt` (F1). Python 3.12.14, NumPy 2.1.3, PyTorch 2.14.0+cpu,
git 2.47.3. Treinos: subprocessos com threads default (2). Verificação e compromisso: 1 thread,
float64 (conservador e canônico).

## 4. A especificação pouw-cadeia-demo-v1 (o entregável central da Fase 3)

Implementada em `fase3/cadeia.py` (minerador) e `fase3/verificar_cadeia.py` (verificador; saída 0/1).

```
gênese        : genesis_hash = SHA-256("pouw-cadeia-demo-v1|genesis|v1")
                = 98866a9d6cd1cfeb8f530b5be5e5a90296337f9eec9c190a418fe8b62357930c
bloco i       : prev_i        = genesis_hash (i=1) | hash_bloco_{i-1} (i>1)
                desafio_i     = gerar_desafio(prev_i)          [função PURA; desafio.py F1,
                                                                 intocado — o desafio é função do
                                                                 bloco anterior → trabalho SERIAL]
                receita_i     = treinar.py(desafio_i, alvo 40 dB, máx 5000 épocas)
                                                                 [trabalho útil; F1, intocado]
                comp_i        = pouw-quant-v1(forward_f64(receita_i), lo/hi(desafio_i), B=16)
                comp_desafio_i= pouw-quant-v1(desafio_i, min/max(desafio_i), B=16)
                                                                 [âncora do desafio tolerante a
                                                                 libm — ver limitação 2]
                header_i      = "pouw-cadeia-demo-v1|bloco=i|prev=…|comp=…|alvo=40|nonce=n"
                hash_bloco_i  = SHA-256(header_i)  com bits-zero-prefixo ≥ 16
                                                                 [ajuste fino exponencial; E5-F2]
publicação     : desafio_XX.npy + receita_XX.pt + quantizada_XX_u16.npy + cadeia.json
                (hashes SHA-256 de tudo; 37 âncoras em hashes_fase3.sha256)
```

**Regra de validade (verificar_cadeia.py, código de saída 0/1):** C0 gênese/spec + 8 checagens por
bloco: C1 encadeamento-prev · C2 desafio-determinístico (regenerado da seed = prev, via
comp_desafio) · C3 âncora-receita-desafio (sha256 do .npy == registrado == meta da receita) ·
C4 integridade-receita (sha256 do .pt) · C5 compromisso pouw-quant-v1 recomputado == do bloco ·
C6 quantizada publicada (array recomputado == arquivo E sha256 == registrado) · C7 PSNR ≥ alvo ·
C8 header+nonce (re-derivado, re-hash, prefixo k). A regra é deliberadamente redundante: fraudes em
arquivo, registro, encadeamento e prova de trabalho são pegues por caminhos independentes (E4).

**Decisões declaradas:** B=16 fixo; float64/1-thread no compromisso e na verificação (mesmo caminho —
é o que garante o match); nonces de `default_rng(20260902)` (determinístico, demo); treino em
subprocesso com threads default; o verificador NUNCA re-treina — verifica a receita PUBLICADA
(lição consolidada no E5).

## 5. E1 — mineração da cadeia oficial (8 blocos, alvo 40 dB, prefixo 16 bits)

Log bruto integral: `fase3/logs/raw/f3_e1_cadeia.txt` (parede 50,3 s; FIM 03:45:48 UTC).

| bloco | épocas | PSNR verif (dB) | treino (s) | moagem (s) | tentativas | compromisso (16) | hash_bloco (16) |
|------:|-------:|----------------:|-----------:|-----------:|-----------:|------------------|-----------------|
| 1 | 100 | 47.8726 | 4.040129 | 0.001426 | 1.803 | `cd579702b18e133e…` | `000058a7496dd7e5…` |
| 2 | 100 | 48.4494 | 4.178929 | 0.033429 | 44.769 | `0fff8405892f2d0f…` | `0000272552967f9f…` |
| 3 | 100 | 48.6712 | 4.103007 | 0.029885 | 40.895 | `7cd2df64afce402e…` | `00001fd640b0ff3a…` |
| 4 | 100 | 48.4106 | 3.878736 | 0.043657 | 60.292 | `f388b1c19f74c7ab…` | `0000200bf1aaad7a…` |
| 5 | 100 | 48.8548 | 4.069102 | 0.005803 | 7.874 | `5cd04941ad0e9976…` | `0000618054eaeb30…` |
| 6 | 100 | 50.1790 | 3.987591 | 0.038832 | 52.611 | `d91f50f3699d5bfa…` | `00007efe852b4e76…` |
| 7 | 100 | 47.0671 | 4.116510 | 0.152859 | 197.328 | `f0d4ab32fe138b91…` | `00005d5d0b6304e3…` |
| 8 | 100 | 44.7247 | 4.046556 | 0.020301 | 27.385 | `eece79b0314d8d04…` | `00001c19b2ff024c…` |

Somatórios medidos: treino (útil) **32,420560 s** · moagem (quebra) **0,326192 s** · forward+quant
**0,158685 s** · geração de desafios **0,008557 s** · parede da mineração **48,607037 s**
(comunicação de subprocessos + salvamentos). Todos os 8 PSNR ≥ 44,7 dB (alvo 40). O último
hash_bloco (ponta da cadeia): `00001c19b2ff024c21b55cf719ce0de3e889fcdbd84b3c5723d18b2ff8c39c09`.
`cadeia.json` completo: SHA-256 `5b7b350101559fac9fbdbed7acd83e630c51b36c34900a611dbe07560daba796`.

**Leituras:** (a) a razão útil:quebra na mineração foi **99:1** (32,4 s de treino vs 0,33 s de
moagem) — o custo dominante é o trabalho útil, como projetado; (b) o encadeamento SERIALZA o
trabalho: a seed do desafio i+1 só existe após o bloco i fechar (a moagem de k=16 custou
milissegundos aqui, mas em k mais alto o encadeamento forçaria o ajuste fino a também serial); (c)
a variância das tentativas de moagem (1,8k a 197k; mediana 34.140 vs esperança 2^16=65.536) é a
variância geométrica esperada — declarada, amostra pequena.

## 6. E2 — verificação fria da cadeia inteira

Log bruto: `fase3/logs/raw/f3_e2_verif_fria.txt` (processo novo, 1 thread, float64; FIM 03:50:39 UTC).

**Resultado: 8/8 blocos VÁLIDOS — CADEIA VÁLIDA (código de saída 0).** Tempo por bloco:
15,4–26,0 ms (soma 0,138225 s); **verificação total da cadeia (carga do JSON → último PSNR, sem
import): 0,138637 s**; processo inteiro com import: 1,283290 s. Todos os compromissos, quantizadas,
encadeamentos, headers e prefixos recomputados pelo verificador bateram com o registrado pelo
minerador — incluindo o compromisso do bloco 1 `cd579702b18e133e4edae3a9a812e2067547fe9dc1fb960f9b19fbf71fb31ff7`,
idêntico ao do smoke test executado antes da mineração (mesma gênese, mesmo desafio, receita
bit-idêntica — ver E5).

## 7. E3 — verificação em lote (runtime persistente) vs fria

Log bruto: `fase3/logs/raw/f3_e3_lote.txt` (5 passadas de lote + 1 subprocesso frio-cadeia + 8
subprocessos frios-por-bloco; FIM 03:51:02 UTC). Script: `fase3/experimento_lote.py`.

| modo | verif. total (s) | parede total (s) | por bloco (s) | blocos/s |
|---|---:|---:|---:|---:|
| **lote persistente** (1 processo, 5 passadas, mediana) | 0,124568 | 1,431562 (com 1 import) | **0,015571** | **64,22** |
| frio-cadeia (1 subprocesso) | 0,137846 | 1,238598 | 0,154825 | 6,46 |
| frio-por-bloco (8 subprocessos) | 0,211458 | 9,010550 | 1,126319 | 0,89 |

Import do PyTorch medido aqui: **1,307 s = 10× o tempo de verificar os 8 blocos em lote**; o custo
por bloco no frio-por-bloco (1.126 ms de parede) é **72,3×** o do lote (15,6 ms). A razão
mineração/verificação-lote da cadeia completa foi **390,2×** (48,607 s / 0,124568 s). Conclusão de
engenharia: um nó verificador real deve manter runtime persistente e validar blocos em lote — o custo
marginal por bloco cai para ~16 ms, e o import (1,1–1,3 s, a dor declarada desde a Fase 1) é pago
uma vez por sessão de validação, não por bloco.

## 8. E4 — teste negativo: o verificador rejeita fraudes?

1ª execução (log preservado: `f3_e4_negativo_EXECUCAO1_EXPECTATIVA_ERRADA.txt`): 4/5 rejeições — o
modo "desafio" rejeitou corretamente (código 1, bloco 2, C3), mas a MINHA expectativa declarada
({C2, C3}) estava errada: C2 compara o desafio regenerado contra o REGISTRO (intacto naquela fraude);
quem pega o arquivo adulterado é a C3. Expectativa corrigida + 6º modo adicionado (`comp_desafio`,
que isola a C2). 2ª execução (log oficial: `fase3/logs/raw/f3_e4_negativo.txt`):

| adulteração (em cópia; oficiais intocados) | bloco | checagens que falharam | esperadas |
|---|---:|---|---|
| compromisso do header trocado | 4 | C5, C8 | C5, C8 |
| nonce incrementado | 4 | C8 | C8 |
| prev apontando p/ outro bloco | 5 | C1, C2, C7, C8 | C1, C2 |
| receita_04.pt sobrescrito c/ 05 | 4 | C3, C4, C5, C6, C7 | C3, C4, C5, C6, C7 |
| comp_desafio do registro trocado | 2 | C2 | C2 |
| desafio.npy com 1 pixel +0.001 | 2 | C3 | C3 |

**6/6 rejeições corretas** (código de saída 1, bloco certo, checagens esperadas ⊆ observadas). As
checagens extras observadas são consistentes com o desenho (ex.: receita trocada derruba C6 porque a
quantizada publicada deixa de bater com o forward da receita trocada). O par C2+C3 cobre as duas
fraudes complementares: registro falso (C2) e arquivo divergente do registro (C3).

## 9. E5 — determinismo do re-treino (contraexemplo investigado)

**Gatilho (fato, medido antes do experimento):** o bloco 1 do smoke (03:44 UTC) e o da mineração
oficial (03:45 UTC) saíram BIT-A-BITO idênticos (mesmo compromisso `cd579702…`, mesmo hash_bloco
`000058a7…`), mas o bloco 2 divergiu: mesmos desafios byte-a-byte (sha256 `ef50edfd…` conferido),
mesma seed de rede, e pesos finais com max|Δ| = **2,8e-06** (tensor 4) → compromisso diferente
(`42f0ada7…` vs `0fff8405…`). Log bruto do experimento: `fase3/logs/raw/f3_e5_retreino.txt`.

**Experimento (8 treinos em subprocessos, artefatos oficiais intocados):**

| comparação | resultado |
|---|---|
| oficial vs 4 réplicas default (2 threads), desafio do bloco 2 | **BIT-IDÊNTICAS (8/8 tensores) ×4** |
| oficial vs 2 réplicas com OMP_NUM_THREADS=1 | DIFERENTES, max\|Δ\| = 5,076e-08 |
| oficial_B vs 2 réplicas default, desafio do bloco 1 | BIT-IDÊNTICAS ×2 |
| réplica A1 vs A2/A3/A4 | BIT-IDÊNTICAS |

**Leitura honesta:** o re-treino com threads default é bit-reproduzível nas 7 réplicas
subsequentes; a divergência do smoke foi **1 evento em ~8 execuções do mesmo treino, magnitude
2,8e-06 (~55× o efeito documentado de trocar para 1 thread)**, não reproduzido — causa não isolada
(hipótese: condição de corrida rara no treino float32 multi-thread; 2 vCPUs compartilhadas). Isso
**nuança** as observações "re-treino bit-a-bit determinístico" da F1 (logs/etapa2.md, 2 execuções) e
da F2 (E4: alvo-40/alvo-60 reproduziram entre sessões): reproduções ocasionais coincidem, mas
determinismo de re-treino NÃO é uma propriedade garantida. **O desenho da cadeia está correto
exatamente por isso**: o compromisso é sobre a RECEITA PUBLICADA (o verificador faz forward do .pt e
jamais re-treina), e a divergência ~1e-06 é da mesma classe de ruído float32 que a spec
pouw-quant-v1 (float64 + B=16) foi construída para absorver no lado do consenso. Consequência
declarada: **re-minerar a mesma gênese pode produzir compromissos diferentes a partir de qualquer
bloco** (como num blockchain, a cadeia publicada é a âncora; o histórico não é regenerável por
execução).

## 10. E6 — inventário de dados publicados

Log bruto: `fase3/logs/raw/f3_e6_inventario.txt`. Cadeia oficial (8 blocos): **1.450.113 B
(1,38 MiB) → 181.264 B/bloco** — desafio 32.896 B + receita 138.359 B + quantizada 8.320 B +
1/8 do cadeia.json (13.513 B). A receita continua dominando (limitação 3 da F1 persistente: nesta
escala não há economia de bytes; a economia medida é de TEMPO). 37/37 âncoras SHA-256 OK
(`sha256sum -c fase3/hashes_fase3.sha256`).

## 11. Como conferir de forma independente (o teste cross-CPU de verdade, agora com cadeia)

Na **sua** máquina (a que divergiu na Fase 1 — CPU que mediu 7.15e-07 de divergência float32):

```bash
git clone https://github.com/Kronos1027/pouw-siren.git && cd pouw-siren
bash checar_integridade.sh          # 75 âncoras (15 F1 + 23 F2 + 37 F3) → 75× OK

python3 fase3/verificar_cadeia.py   # processo frio; ~1,3 s com import
# deve imprimir, entre outras linhas:
#   [bloco 1] VÁLIDO … | comp cd579702b18e133e… | hash_bloco 000058a7496dd7e5…
#   … (8 linhas, todos VÁLIDO)
#   RESULTADO: CADEIA VÁLIDA (código 0)
```

**Predições registradas ANTES de você rodar:** (a) os 8 compromissos devem bater bit-a-bit (float64
+ B=16; resíduo esperado ~1e-15, 5 ordens abaixo da pior fronteira medida na F2); (b) a checagem C2
(comp_desafio do desafio regenerado via `np.sin`/`np.cos` da SUA libm) também deve bater — o campo
pode divergir ~1 ulp (~4e-16) entre libms, o que a quantização B=16 absorve com folga (a primeira
virada medida na F2 foi em 1e-09); (c) o hash BYTES dos .npy deve bater exato (você baixa os bytes
publicados — C3 não regenera). **Se qualquer bloco divergir, o verificador aponta bloco + checagem +
valores recomputados vs publicados** — o diagnóstico sai pronto, e a spec sobe para regime mais
conservador (mesma triagem prevista na F2 §10).

## 12. Comandos exatos usados, na ordem

Executados a partir da raiz do repo, cada um com `{ date -u …; time <cmd>; date -u …; } 2>&1 | tee
fase3/logs/raw/<arquivo>.txt` (outputs brutos e timestamps integrais lá):

```bash
# smoke (2 blocos) — logs f3_smoke_*.txt
python3 -u fase3/cadeia.py --blocos 2 --saida fase3/smoke
python3 -u fase3/verificar_cadeia.py fase3/smoke
python3 -u fase3/experimento_lote.py fase3/smoke --repeticoes 3

# diagnóstico do gatilho do E5 (comparações sha256/pesos/arrays — script ad hoc, evidência no log f3_e1)
# E1..E6 — execução oficial
python3 -u fase3/cadeia.py --blocos 8 --alvo-psnr 40 --prefixo-bits 16 --saida fase3/cadeia_demo
python3 -u fase3/verificar_cadeia.py fase3/cadeia_demo
python3 -u fase3/experimento_lote.py fase3/cadeia_demo --repeticoes 5
python3 -u fase3/teste_negativo.py fase3/cadeia_demo          # 1ª execução: expectativa errada, preservada
python3 -u fase3/teste_negativo.py fase3/cadeia_demo          # 2ª: 6/6 (após corrigir expectativa + modo novo)
python3 -u fase3/experimento_retreino.py
sha256sum <37 artefatos> > fase3/hashes_fase3.sha256 && sha256sum -c fase3/hashes_fase3.sha256
```

## 13. Limitações observadas (tudo que não saiu redondo)

1. **Contraexemplo de determinismo de re-treino (E5, §9):** 1 divergência em ~8 execuções
   (2,8e-06), não reproduzida em 7 réplicas; causa não isolada. Não afeta o consenso (verificador
   nunca re-treina), mas corrige por nuance a observação da F1 e obriga a declarar: **a cadeia não é
   regenerável por re-execução** — a âncora é o artefato publicado.
2. **C2 depende de libm:** o comp_desafio regenerado usa `np.sin`/`np.cos` da libm do verificador.
   A margem teórica é enorme (1 ulp ~4e-16 vs primeira virada medida 1e-09), mas a evidência
   cross-CPU da Fase 2 cobre o FORWARD da rede, não a regeneração do desafio — a C2 é a checagem
   mais exposta a diferenças entre implementações de libm; se divergir, o diagnóstico pronto do
   verificador aponta exatamente isso (§11c).
3. **k=16 é baixo de propósito:** a moagem custou 0,33 s no total (0,7% da mineração); ajuste fino
   real exigiria k calibrado contra implementações C/GPU (o E5-F2 mediu 2,25 M hashes/s em Python
   puro; extrapolações rotuladas lá).
4. **8 blocos × 100 épocas é amostra pequena:** a cadeia demonstra o mecanismo; nada aqui mede
   estatística de consenso sob muitos minerários concorrentes, forks ou reorganizações —
   fora do escopo (não há premiação, nem escolha de ramo, nem gossips: o esqueleto é linear).
5. **A validade da cadeia não implica utilidade "redeemable":** a receita reconstrói o desafio a
   ≥44,7 dB, mas ninguém "usa" o artefato — a utilidade demonstrada é a compressão em si
   (limitação 3 da F1: 138 kB de receita vs 33 kB de desafio; sem economia de bytes nesta escala).
6. **Nonces determinísticos (`default_rng(20260902)`):** demo; minerador real escolheria nonces
   livremente (irrelevante para a validade — C8 confere o nonce registrado, não como ele nasceu).
7. **A 1ª execução do E4 teve expectativa errada** (4/5): preservada em
   `f3_e4_negativo_EXECUCAO1_EXPECTATIVA_ERRADA.txt` (padrão anti-fabricação; a fraude em si foi
   detectada em ambas as execuções — o erro era só na checagem ESPERADA, não na detecção).
8. **Tempos de parede variam com a VM** (limitação 7 da F2): treinos de 3,88–4,18 s vs 5,7–6,2 s no
   E5 (subprocessos frios com import); compromissos e PSNRs não mudam.
9. **Import do PyTorch persiste como custo dominante do frio** (1,11–1,31 s medidos nesta fase);
   o lote resolve para o nó persistente (E3), mas o verificador one-shot de 1 bloco continua pagando
   1 import por bloco (72,3× mais caro que o lote, medido).
10. **`torch.save` segue não byte-reproduzível** (limitação 3 da F1): os 8 .pt provam integridade
    da cópia; a reprodutibilidade por construção continua sendo o .npy QUANTIZADO (C6 confere
    array + sha256 — o quantizada_01_u16.npy do smoke é byte-idêntico ao oficial? NÃO precisa ser:
    são minerações distintas em diretórios distintos; dentro da cadeia oficial, C6 ata o publicado
    ao recomputado).
11. **O compromisso do desafio usa limites do próprio campo** (min/max do array): definido assim
    para manter o desafio auto-contido; uma spec de produção preferiria limites da GÊNESE ou
    faixas fixas, para blindar contra desafios com amplitude atípica.
12. **Artefato de exibição persistente** da F1/F2 (a camada de sessão engole "[m"): sem ocorrência
    nova relevante nesta fase; logs em disco íntegros.
13. **O par C2+C3 exige publicar o desafio .npy inteiro (33 kB/bloco):** em troca, o verificador
    nunca precisa confiar no minerador para o conteúdo do desafio — trade-off declarado.

## 14. Conclusão factual

Sob o protocolo anti-fabricação: a cadeia demo `pouw-cadeia-demo-v1` de **8 blocos encadeados por
hash** foi minerada (trabalho útil = treino SIREN: 32,42 s; queima = moagem de prefixo: 0,33 s;
razão 99:1), com **todos os 8 blocos válidos em verificação fria e independente** (9 checagens por
bloco, incluindo a regeneração determinística do desafio a partir do bloco anterior e o
compromisso pouw-quant-v1 da Fase 2 recomputado bit-a-bit), **6/6 fraudes adulteradas rejeitadas**
com as checagens certas, e custo de verificação medido nas duas extremidades operacionais:
**15,6 ms/bloco em lote persistente (64,2 blocos/s, razão mineração/verificação 390×)** vs
1.126 ms/bloco no frio-por-bloco (o import domina). O contraexemplo do E5 (re-treino divergiu
2,8e-06 em 1 de ~8 execuções, não reproduzido) consolidou o princípio central do desenho: **o
consenso nunca re-treina — verifica o artefato publicado**. A confirmação final cross-CPU (a
predição §11: cadeia 8/8 VÁLIDA em qualquer CPU, compromissos bit-a-bit) está publicada para o
leitor executar, com 37 âncoras novas (75 no repo inteiro).
