# Relatório da Fase 5 — PoUW-SIREN: caminho de verificação 100% INTEIRO (pouw-int-v1)

**Data:** 2026-09-15 · **Execução:** agente Super Z, mandato permanente do usuário
("prossiga com a pesquisa… garantindo que sejam dados reais") · **Protocolo
anti-fabricação:** 6 itens em vigor (§12); todos os números vêm de execuções reais
com outputs brutos em `fase5/logs/raw/*.txt`.

---

## 1. Objetivo e posição no arco da pesquisa

A Fase 2 fechou a limitação 4 da Fase 1 (hash float32 não portável) com a spec
`pouw-quant-v1`: forward em **float64** + quantização fixed-point B=16 + SHA-256
dos bytes. A Fase 4 confirmou por validação externa (Windows, stack inteiro
diferente) que o compromisso resultante é bit-a-bit reprodutível entre máquinas.
Restava, porém, um **resíduo teórico declarado**: o forward float64 depende
(a) da **ordem de soma interna do GEMM do BLAS** e (b) do **`sin()` da libm**,
que a IEEE-754 não exige corretamente arredondado — a checagem C2 da Fase 3
chegava a declarar tolerância a "~1 ulp de libm". A robustez vinha da **margem**
da grade de quantização (~5 ordens de grandeza medidas na F2/E2), não de uma
**garantia por construção**.

Esta fase elimina a classe inteira do risco: a spec **`pouw-int-v1`** define um
caminho de verificação que executa forward, quantização, gate de qualidade e
hash usando **apenas inteiros de precisão arbitrária** — sem BLAS, sem libm,
sem numpy, sem torch, sem FPU. A tese central, agora demonstrada com dados:

> **Dois universos aritméticos disjuntos — float64/BLAS/libm de um lado,
> inteiros Q63 do outro — produzem o MESMO array quantizado de 8192 bytes
> bit-a-bit em 18/18 artefatos oficiais.**

Isso transforma a propriedade de determinismo cross-CPU de *empírica* (validada
em n=2 plataformas) em **estrutural**: qualquer máquina com inteiros de 64 bits
— incluindo uma re-implementação em C sem biblioteca matemática — chega ao mesmo
compromisso, porque a adição e a multiplicação inteiras são exatas e
associativas em qualquer hardware.

## 2. Ambiente (e recuperação de ambiente)

| Item | Valor |
|------|-------|
| SO | Linux (container), 2 vCPU, 3,9 GiB RAM |
| Python | 3.12.14 |
| PyTorch | 2.14.0+cpu (reinstalado nesta sessão) |
| NumPy | 2.1.3 |
| Git | clone religado ao remoto; HEAD `e85bfff` (estado F4) |

O ambiente da sessão anterior foi resetado (git do clone substituído por repo
genérico; torch desinstalado). As **80 âncoras SHA-256 conferiram 80/80
pós-restore** ANTES de qualquer trabalho novo — o sistema de âncoras tornou a
perda do git irrelevante para a verificabilidade (log:
`f5_e0_integridade_pos_restore.txt`). Após reinstalar torch e religar o git
(remote limpo + GIT_ASKPASS, token fora do repo), a cadeia da F3 foi
re-validada em processo frio: **8/8 VÁLIDOS, 0,140862 s**, compromissos
idênticos aos publicados e aos obtidos na máquina Windows do dono (log:
`f5_e0_cadeia_fresca.txt`).

## 3. A spec pouw-int-v1 (`fase5/siren_int.py`)

Projeto conduzido por **dados medidos antes do código**: grade 64×64 (4096
pontos), arquitetura `2→128→128→128→1`, ω₀=30, max|w| = 0,501647, max|b| =
0,706801, max|ω₀·z| = 49,8915 (⇒ |k| da redução trigonométrica ≤ 32) — tudo
medido nas 8 receitas oficiais da cadeia.

**Formato dos números.** Q63 (fixed-point, valor = q/2⁶³) para pesos, ativações,
pré-ativações, argumento do seno e reconstrução; acumuladores de camada em Q126
(produto exato Q63×Q63), arredondados UMA vez por camada.

**Arredondamentos pinados.** `rhe(x,k)` e `divround(a,b)` — ambos
**half-even** ("meio-para-par"), deliberadamente a MESMA regra do `np.rint`
usada pela pouw-quant-v1 (paridade de empates verificada no smoke S1 e S5).

**Constantes pinadas.** π como literal ASCII de 50 dígitos no código-fonte —
**verificável sem confiar em ninguém** por fórmula de Machin em bigint (smoke
S2); a 1ª versão do teste tinha um erro off-by-one (comparava 51 dígitos com
50), preservado no log — o literal estava correto. Coeficientes de Taylor
1/n! são racionais exatos, arredondados uma única vez no carregamento.

**Seno inteiro.** Redução por π/2 (k = round(A/C), r = A − kC, |r| ≤ π/4) +
Taylor até r¹⁹/19! (seno) e r¹⁸/18! (cosseno) em Horner com u = r². Erro total
≤ ~2⁻⁵⁷ — 6+ ordens abaixo do passo da grade B=16. Medido contra
`numpy.sin` em ~128.580 pontos diádicos EXATOS (mesmo valor real dos dois
lados): pior |Δ| = **1,11e-16** — 1 ulp, dominado pelo erro do próprio numpy
(smoke S4); nos múltiplos exatos de π/2, `sin_q` devolve 0/±1 EXATOS (S3).

**Forward.** Coordenadas como racionais exatos ((2j−(S−1))/(S−1), a mesma
ordem meshgrid/ravel da F1); por camada: acumulação exata em Q126 — **a ordem
de soma é irrelevante por construção** (E2); z arredondado a Q63; ativação
`sin_q(ω₀·z)`; última camada sem ativação.

**Quantização (equivalente inteira exata da v1).** lo/hi do desafio por
**seleção de bits** (chave de ordem inteira com a mesma ordem dos float64;
conversão bit→Q63 exata para os extremos O(1) dos desafios reais);
`q = clip(divround((R−lo)·65535, hi−lo), 0, 65535)` — tudo inteiro, um único
arredondamento. Hash: SHA-256 com header de domínio próprio
`pouw-int-v1|B=16|HxW|` — **diferente do header v1 por projeto** (payload
idêntico, domínios distintos; um hash v2 nunca pode ser confundido com v1).

**Gate de qualidade.** PSNR ≥ alvo como **desigualdade inteira exata**:
S·10^t ≤ N·alcance² para alvos múltiplos de 10 dB; para múltiplos de 5
(extensão criada nesta fase, ver §8) via **raiz quadrada inteira** (Newton,
empate provavelmente impossível) com limiar Q63 e erro ≤ 2⁻⁶⁴ relativo — 19
ordens abaixo das margens medidas. Zero log, zero sqrt, zero divisão de float.
A referência do gate é o desafio quantizado a Q63 (erro ≤ 2⁻⁶⁴ por amostra;
lo/hi exatos).

**Pesos canônicos (.bin).** Header ASCII
(`pouw-int-v1|Q=63|camadas=…|omega_0=30|grade=64`) + int64 little-endian com
sinal. Exportador (`exportar_pesos_int.py`) usa torch APENAS para desserializar
o .pt; a conversão float32→Q63 é **por bits** (decomposição sinal/expoente/
mantissa — cada float32 é um racional diádico exato), portanto o .bin é função
determinística dos pesos: re-exportar dá bytes idênticos (18/18 confirmados).
Restrição medida: |w| < 1 (máximo real 0,5016; folga 2× em int64).

**Leitor de .npy sem numpy.** Header parseado com `ast.literal_eval` (nenhum
float materializado); bytes lidos com `int.from_bytes`; mín/máx por chave de
ordem de bits; Inf/NaN rejeitados. O verificador frio não precisa de numpy
nem torch.

## 4. Prova de ausência de floats (auditoria em runtime)

O `verificar_int.py` roda em processo próprio e confere em `sys.modules` que
math/cmath/numpy/torch/scipy/decimal/fractions/statistics/random **nunca foram
carregados**. Dois detalhes que tornam a prova séria:

1. **A auditoria pegou uma infiltração real na 1ª execução:** `pathlib`
   importa `math`. Diagnóstico por testes isolados em subprocessos limpos
   culminou em `pathlib`; o verificador o excluiu e o incidente está
   documentado no código e no log.
2. **Até a medição de tempo é inteira:** `time.perf_counter_ns` (nanossegundos
   inteiros); os decimais de exibição são formatados por `divmod`. Nenhum
   float é materializado no processo — nem para cronômetro.

## 5. E2 — Invariância à ordem de soma (o coração da tese)

Objeto: camada 2 da receita_01 — 128 unidades × 128 canais × 4096 pontos =
**67.108.864 termos somados por ordem** (log: `f5_e2_ordem.txt`).

| Lado | Ordens testadas | Resultado bit-a-bit |
|------|-----------------|---------------------|
| **Inteiro Q126** | direta (0→127), reversa (127→0), árvore pareada | **0 de 524.288 valores diferentes** |
| **Float64** | direta, reversa, árvore, **GEMM do BLAS** | 374.287–470.515 de 524.288 valores (≈72–90%) mudam de bits entre pares; max\|Δz\| = 1,7e-16…3,9e-16; bins B16 de proxy: 0 |

Leitura honesta: no lado float, a margem da grade B=16 absorveu o resíduo
(bins 0) — como a F2 já havia medido; mas o resíduo EXISTE e é empírico
(pode mudar de máquina/BLAS). No lado inteiro, **não há resíduo algum**: a
adição inteira é associativa, a igualdade é um teorema que os dados apenas
confirmam. A 1ª execução deste experimento exibia um total errado no texto
final (16.777.216 em vez de 524.288) — medições corretas, rótulo corrigido;
execução preservada em `…EXECUCAO1_NUMERO_EXIBIDO_ERRADO.txt`.

## 6. E3 — Equivalência v1×v2 nos 18 artefatos oficiais

Executado sobre TODAS as receitas publicadas do repositório: 8 blocos da
cadeia F3 + 4 receitas F1 + 6 receitas F2 (varredura de dificuldade 40–65 dB).
v1 = `verificar_fase2.forward_torch64` (float64, BLAS, libm, 1 thread);
v2 = `siren_int` sobre os `.bin` (log integral: `f5_e3_equivalencia.txt`).

| tag | PSNR v1 (dB) | gate v1 | gate v2 | bins≠ | max\|ΔR\| | payload | compromisso v2 (16 hex) | t v1 (s) | t v2 (s) |
|-----|-------------:|---------|---------|------:|----------:|:-------:|------------------------|---------:|---------:|
| cadeia_01 | 47,8726 | APROV | APROV | 0 | 7,33e-15 | = | `162d852c6b603f0c…` | 0,0194 | 26,43 |
| cadeia_02 | 48,4494 | APROV | APROV | 0 | 7,77e-15 | = | `9366457358ebfdcb…` | 0,0172 | 26,39 |
| cadeia_03 | 48,6712 | APROV | APROV | 0 | 7,83e-15 | = | `32e7e3efb99e48a8…` | 0,0174 | 26,68 |
| cadeia_04 | 48,4106 | APROV | APROV | 0 | 7,99e-15 | = | `3d34616b5ce20c03…` | 0,0176 | 26,76 |
| cadeia_05 | 48,8548 | APROV | APROV | 0 | 6,69e-15 | = | `5573254afe060d85…` | 0,0172 | 27,17 |
| cadeia_06 | 50,1790 | APROV | APROV | 0 | 7,22e-15 | = | `cad3861e224de406…` | 0,0175 | 27,16 |
| cadeia_07 | 47,0671 | APROV | APROV | 0 | 5,55e-15 | = | `5123013656af90be…` | 0,0178 | 27,36 |
| cadeia_08 | 44,7247 | APROV | APROV | 0 | 1,31e-14 | = | `f83468725ccbed6e…` | 0,0173 | 27,53 |
| f1_8b457d0a | 49,2587 | APROV | APROV | 0 | 6,00e-15 | = | `61dd3a86b1b35390…` | 0,0168 | 27,47 |
| f1_b0f90ffe | 49,6253 | APROV | APROV | 0 | 6,33e-15 | = | `0ee90ec7eb7f38b1…` | 0,0200 | 27,57 |
| f1_d037aef4 | 48,3896 | APROV | APROV | 0 | 5,33e-15 | = | `de0dbdd311f43f19…` | 0,0169 | 27,73 |
| f1_extra60db | 60,8704 | APROV | APROV | 0 | 6,22e-15 | = | `2d76414c5549e969…` | 0,0170 | 27,89 |
| f2_alvo40db | 49,6253 | APROV | APROV | 0 | 6,33e-15 | = | `0ee90ec7eb7f38b1…` | 0,0173 | 27,95 |
| f2_alvo45db | 49,6253 | APROV | APROV | 0 | 6,33e-15 | = | `0ee90ec7eb7f38b1…` | 0,0170 | 28,00 |
| f2_alvo50db | 54,5661 | APROV | APROV | 0 | 5,33e-15 | = | `831c5b0c651b8951…` | 0,0173 | 27,91 |
| f2_alvo55db | 57,3701 | APROV | APROV | 0 | 5,44e-15 | = | `762e585ecd348864…` | 0,0171 | 28,01 |
| f2_alvo60db | 60,8704 | APROV | APROV | 0 | 6,22e-15 | = | `2d76414c5549e969…` | 0,0164 | 27,96 |
| f2_alvo65db | 65,0004 | APROV | APROV | 0 | 5,33e-15 | = | `bf19114204cb4e99…` | 0,0176 | 27,91 |

**Resumo medido:**

- **payloads quantizados v1≡v2 bit-a-bit: 18/18** — 0 bins divergentes em
  **73.728** comparações pixel a pixel;
- **gates concordantes: 18/18** (incluindo os alvos 45/55/65 dB do gate
  estendido — ver §8);
- **max|ΔR| global: 1,31e-14** — 0,00 em passos da grade B=16 (passo ≈
  1,5e-4…1,6e-4; a maior divergência observada entre os dois universos
  aritméticos é ~10 ordens de grandeza menor que o menor detalhe que o
  compromisso enxerga);
- achado de curadoria: **18 artefatos = 14 conjuntos distintos de pesos** —
  `b0f90ffe` ≡ `alvo40db` ≡ `alvo45db` (treino determinístico parando no
  mesmo checkpoint, época 100, PSNR 49,63 ≥ 40 e ≥ 45) e `extra60db` ≡
  `alvo60db` (PSNR 60,87); os `.pt` correspondentes têm SHA **diferente**
  (timestamps do zip do torch.save — limitação conhecida da F1), mas os
  pesos `.bin` são **byte-idênticos** — o formato inteiro ancora os PESOS,
  não a embalagem.

A coluna "payload =" compara os ARRAYS quantizados; os HASHES v1 e v2 divergem
por projeto (headers de domínio distintos — §3). A 1ª execução do E3 abortou
na receita alvo45db (gate não suportava múltiplos de 5) e está preservada em
`…EXECUCAO1_ALVO_45_NAO_SUPORTADO.txt` com 13/18 receitas já medidas.

## 7. Demonstração oficial: 8 verificações FRIO zero-float

Cada bloco da cadeia foi verificado por um **subprocesso próprio** do
`verificar_int.py` com âncoras completas (sha256 do .bin e do desafio,
compromisso esperado e array quantizado publicado da v1):

- **8/8 VÁLIDOS, código 0** — em cada execução: auditoria zero-float OK
  (nenhum módulo de float carregado), compromisso v2 recomputado CONFERE com
  o esperado (determinismo entre execuções do caminho inteiro), gate exato
  APROVADO, e **payload 0/4096 bins divergentes contra o array publicado pelo
  caminho float64/BLAS/libm** (C3).
- O log frio integral do bloco 1 (26,000421 s no caminho inteiro, tempos em
  ns) está em `f5_verificar_int_frio_bloco1.txt`.

Em outras palavras: **um processo sem nenhuma operação de ponto flutuante
reproduz, bit-a-bit, o compromisso de conteúdo publicado pelo caminho
float64/BLAS/libm** — e recusa todas as fraudes do §8.

## 8. E4 — Suíte adversarial (log: `f5_e4_negativos.txt`)

**Sweep de sensibilidade quantitativa** (perturbação de UM peso, W₁[0][0],
medida no caminho completo):

| δ (LSB Q63) | δ (unid. do sinal) | bins ≠ /4096 | hash mudou | gate |
|------------:|-------------------:|-------------:|:----------:|------|
| 1 | 1,084e-19 | 0 | NÃO | APROVADO |
| 2¹⁰ | 1,110e-16 | 0 | NÃO | APROVADO |
| 2²⁰ | 1,137e-13 | 0 | NÃO | APROVADO |
| 2³⁰ | 1,164e-10 | 0 | NÃO | APROVADO |
| 2³³ | 9,313e-10 | 0 | NÃO | APROVADO |
| 2⁴⁰ | 1,192e-07 | **2** | **SIM** | APROVADO |

Leitura (medida): perturbações até ~9e-10 do sinal são invisíveis ao
compromisso — o **mesmo piso de ruído** que a F2/E2 mediu no quantizador
isolado; é projeto, não defeito (o hash compromete o CONTEÚDO quantizado com
passo ~1,5e-5; a integridade byte-a-byte é papel da âncora SHA-256 do .bin —
pegue em N5/H1). A 1ª execução da suíte trouxe uma LEITURA prevista errada
(piso em 2³⁰–2³³); o medido é 2⁴⁰ — corrigida, execução preservada em
`…EXECUCAO1_LEITURA_ERRADA.txt`.

**Fraudes estruturais (subprocessos frios, 6/6 conforme esperado):**

| Caso | Fraude | Pego por |
|------|--------|----------|
| N1 | controle positivo (tudo íntegro) | — (VÁLIDO, código 0) |
| N2 | compromisso esperado com 1 dígito hex adulterado | C1 (compromisso diverge) |
| N3 | pesos do bloco 2 contra o desafio do bloco 1 | C1 + C2 (gate REPROVADO, margem ∞) |
| N4 | desafio com 1 byte do pixel MÁXIMO adulterado | H2 (âncora sha256) + C1 (comp muda p/ `d75a2977…`) |
| N5 | swap dos pesos x↔y da unidade 0 no .bin | C1 + C2 (gate 0,69× — reprovado) |
| N6 | gate rígido (alvo 50 dB) com receita de ~40 dB | C2 (margem 0,91×) |

## 9. E5 — Custos (honestidade completa)

| Métrica | v1 (float64/BLAS) | v2 (bigint Q63, Python puro) |
|---------|------------------:|-----------------------------:|
| forward médio por receita | 0,0175 s | 27,44 s |
| total (18 receitas) | 0,315 s | 493,9 s |
| **razão v2/v1** | — | **1.569×** |

O caminho inteiro em Python puro custa ~1,6 mil vezes mais que o BLAS
float64 — esse é o preço da exatidão por construção NESTA implementação de
referência. Não é um preço da SPEC: um port C com int64/`__int128` executaria
o mesmo cálculo em escala de BLAS (os pesos cabem em int64 com folga 2×; os
acumuladores em 128 bits; nenhuma dependência de biblioteca). O papel desta
implementação é ser a referência canônica verificável — o custo medido está
declarado como limitação (§11) e como item de roadmap (port C + benchmark).

## 10. Como verificar você mesmo

```bash
git clone https://github.com/Kronos1027/pouw-siren.git && cd pouw-siren
bash checar_integridade.sh          # 120× OK (15 F1 + 23 F2 + 37 F3 + 5 F4 + 40 F5)

# caminho inteiro — NÃO precisa de numpy nem torch (só Python stdlib):
python3 fase5/verificar_int.py fase5/pesos_int/pesos_int_cadeia_01.bin \
    fase3/cadeia_demo/desafio_01.npy \
    --comp-esperado 162d852c6b603f0cd94568891cff9512a8a5f78f1c1f185279e69912ed2933be \
    --quantizada fase3/cadeia_demo/quantizada_01_u16.npy
# esperado: auditoria zero-float OK; C1 CONFERE; C2 APROVADO (margem ≈ 6,12×);
#           C3 payload IDÊNTICO ao v1 (0/4096 bins); RESULTADO: VÁLIDO (código 0)

# os outros 7 blocos: troque os sufixos _01 (compromissos na tabela do §6)
# varredura completa de equivalência (precisa de torch+numpy; ~12 min):
python3 fase5/experimento_equivalencia.py
```

**Windows:** o `verificar_int.py` é 100% stdlib — `python fase5\verificar_int.py
fase5\pesos_int\pesos_int_cadeia_01.bin fase3\cadeia_demo\desafio_01.npy …`
funciona sem instalar numpy/torch. A leitura é little-endian explícita;
âncoras com `certutil -hashfile` ou `python checar_integridade.py`.
Desde a **v1.0.1** (errata §15), roda em qualquer Python testado
**3.9–3.13** — inclusive 3.10/3.11, nos quais a v1.0.0 original falhava na
auditoria zero-float (datetime/platform puxavam `math`). Este é o convite
de validação externa desta fase (como o da F3 §11 foi atendido pela F4):
rode os 8 blocos e reporte — roteiro pré-registrado em
`fase6/roteiro_validacao_windows.md`.

## 11. Limitações (honestas e declaradas)

1. **Custo da implementação de referência: ~1.569× o caminho float64**
   (27,4 s vs 17,5 ms por receita, Python puro). A spec não exige esse custo;
   port C com int64/128 é o caminho natural (roadmap).
2. A equivalência v1≡v2 foi demonstrada em **18/18 artefatos nesta máquina**
   — 14 conjuntos distintos de pesos. A afirmação estrutural (inteiros são
   exatos) vale em qualquer máquina; a EQUIVALÊNCIA com o v1 foi medida em
   n=1 ambiente (validação externa convidada, §10).
3. Os hashes v1 e v2 divergem **por projeto** (headers de domínio distintos);
   a equivalência demonstrada é de PAYLOAD (o array quantizado de 8192 bytes).
   Uma futura cadeia v2 comprometeria com o header `pouw-int-v1`.
4. O gate v2 usa a referência do desafio **quantizada a Q63** (erro ≤ 2⁻⁶⁴
   por amostra) e, para alvos múltiplos de 5 (não de 10), limiar arredondado
   (erro ≤ 2⁻⁶⁴ relativo). Vereditos concordaram em 18/18 (margens medidas ≥
   2,5× para os blocos; N6 demonstra a rejeição quando a margem some).
5. Alvos de gate são múltiplos de 5 dB (40–65 medidos); outros valores exigem
   literais pinados (desnecessário ao demo; declarado na spec).
6. O exportador `.pt → .bin` requer torch para DESSERIALIZAR (lado do
   minerador) e declara máquina little-endian; o .bin resultante é portável.
7. Piso de sensibilidade medido: perturbações de peso abaixo de ~1e-7 do
   sinal não mudam o compromisso (projeto — quantização B=16); a âncora de
   bytes cobre integridade fina (N4/N5).
8. `sin_q` é preciso a ~2⁻⁵⁷ (erro medido ≤ 1 ulp do numpy.sin em 128.580
   pontos exatos); a exatidão TOTAL do compromisso não depende dessa
   precisão (qualquer implementação da spec dá bits idênticos) — a precisão
   só importa para a EQUIVALÊNCIA com o v1, medida em 18/18.
9. A cadeia demo permanece LINEAR e v1 (float64) — a pouw-int-v1 é o
   PRIMITIVO de compromisso pronto para a cadeia v2; nenhuma cadeia foi
   re-minerada nesta fase (escopo deliberado: validar o primitivo primeiro).
10. Primeira execução do E3 abortou (alvo 45 dB não suportado) — preservada;
    a lacuna foi convertida em extensão da spec (raiz quadrada inteira) com
    thresholds conferidos contra 10^(a/10).
11. O literal de π (50 dígitos) é verificável por Machin bigint incluído no
    smoke; permanece um literal PINADO — se um dia precisar de mais
    precisão que 2⁻⁶⁴, a spec versiona (pouw-int-v2).
12. Restrições de faixa medidas (max|w| < 1, |ω₀·z| ≤ 49,9, alvo ≥ 0 dB,
    desafios float64 finitos com extremos O(1)) são ASSERTS do caminho — um
    artefato fora da faixa é rejeitado com erro explícito, não aceito em
    silêncio.

## 12. Protocolo anti-fabricação (cumprimento desta fase)

1. Nenhum número sem execução; todas as tabelas acima saem de logs brutos com
   timestamp (`fase5/logs/raw/*.txt`).
2. Outputs integrais colados nos logs (inclusive das execuções intermediárias
   de desenvolvimento do smoke).
3. 40 âncoras novas em `hashes_fase5.sha256` (7 códigos + 18 .bin + 13 logs
   brutos + etapa13 + relatório) → 120 no repo; `checar_integridade.sh`
   atualizado.
4. Tempos de `time.perf_counter()` (experimentos) e `perf_counter_ns`
   inteiro (verificador frio); a única extrapolação é a menção qualitativa ao
   port C (§9), rotulada como projeção.
5. Erros reportados completos: 4 execuções com defeito preservadas com
   sufixo `_EXECUCAO1_*` (off-by-one do teste de π; rótulo errado do E2;
   LEITURA errada do E4; abort do E3 por alvo 45) + a infiltração
   `pathlib`→`math` documentada.
6. Comandos exatos na ordem: `fase5/logs/etapa13.md` §13.1–13.9.

## 13. Conclusão factual

- A spec `pouw-int-v1` executa verificação completa de receita SIREN com
  **zero operações de ponto flutuante** — provável em runtime por auditoria
  de módulos (a auditoria pegou e eliminou uma infiltração real de `math`).
- **18/18 artefatos oficiais: o caminho inteiro reproduz bit-a-bit o payload
  quantizado do caminho float64/BLAS/libm** (0 bins em 73.728; max|ΔR|
  1,31e-14 ≈ 0,00 passo B16); 18/18 vereditos de gate concordam; 8/8
  verificações frias VÁLIDAS com âncoras completas.
- A invariância à ordem de soma — a fonte do risco cross-CPu que motivou a
  Fase 2 — é **por construção** no caminho inteiro (0/524.288 vs ~90% dos
  bits no float64, medido no mesmo dado).
- 6/6 fraudes estruturais rejeitadas + piso de sensibilidade medido (2⁴⁰ LSB).
- Custo honesto: 1.569× nesta implementação de referência (limitação nº 1).

Com isto, o roadmap "forward inteiro sem BLAS" (limitação 2 da F3 / item
listado na F4) está **executado**: o resíduo ~1e-15 que a F4 fechou por margem
empírica agora está fechado por construção — resta ao ecossistema validá-lo
externamente (§10) e portá-lo a C (§9).

## 14. Próximos passos sugeridos (roadmap)

1. **Validação externa da pouw-int-v1** (convite §10 — especialmente valiosa
   porque não exige numpy/torch: qualquer Python 3 stdlib basta, inclusive no
   Windows do dono).
2. **Port C do verificar_int** (int64/`__int128`) + benchmark contra BLAS —
   fecha a limitação de custo nº 1.
3. **Cadeia v2 (pouw-cadeia-demo-v2)** comprometendo com `pouw-int-v1` +
   pesos .bin como artefato primário (âncora de pesos, não de embalagem —
   §6), mantendo o .pt como artefato de mineração.
4. Multi-minerário/forks e sinais reais/3D (roadmap herdado, abertos).

## 15. Errata v1.0.1 — portabilidade do verificador (2026-09-15/16)

Descoberta pela validação externa Windows (Fase 6): no Python **3.11.15** a
auditoria zero-float do `verificar_int.py` v1.0.0 falhava com `['math']` — em
Python ≤ 3.11, `import datetime` executa `import math as _math`
(`Lib/datetime.py`) ANTES do acelerador C. A 1ª matriz pós-correção revelou um
**segundo infiltrado**: em Python **3.10**, `import platform` puxa
`subprocess → selectors → math` (`selectors.py` usava `math.ceil`; removido
no 3.11). **Correção v1.0.1:** `agora_utc()` via `time.strftime/gmtime`
(formato idêntico; `time` nunca carrega `math`) e banner via
`sys.version.split()[0]` (idêntico a `platform.python_version()`).

**Prova de inocuidade:** matriz 3.9.25/3.10.21/3.11.16/3.12.14/3.13.5 no
bloco 1 com `--comp-esperado` + `--quantizada` — **5/5 VÁLIDOS, auditoria OK
e compromisso `162d852c…` CONFERE bit-a-bit em todas** (o caminho
computacional não mudou UM bit; logs em `fase5/logs/raw/f5_e6_correcao_*`).
A auditoria zero-float somou suas **infiltrações nº 2 e nº 3** detectadas
em runtime (a nº 1 fora `pathlib`, na F5) — e provou valer para manutenção,
não só para o congelamento inicial. Documentação completa:
`fase5/logs/etapa15_correcao_portabilidade.md`.
