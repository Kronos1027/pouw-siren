# PoUW-SIREN — Proof of Useful Work via compressão neural (Fase 1 + Fase 2, CPU-only)

Pesquisa exploratória: usar **compressão neural (SIREN — Implicit Neural Representation)** como
"trabalho útil" no lugar da queima de hash do Proof-of-Work tradicional. O minerador **treina**
uma rede para comprimir um desafio determinístico (segundos — caro); o verificador confere a
**receita** produzida (milissegundos — barato), em processo frio e independente. É a mesma
assimetria produzir-caro/conferir-trivial do PoW — mas com um subproduto **reaproveitável**:
a receita reconstrói o sinal a ~49 dB de PSNR, em vez de virar lixo entrópico como o hash do
bitcoin.

Projeto-irmão / motivação: [Kronos1027/black-hole](https://github.com/Kronos1027/black-hole).

## Fase 2 (2026-09-02): consenso cross-CPU via quantização + dificuldade escalável

**Problema herdado da Fase 1:** o hash da reconstrução float32 diverge entre CPUs (validado
pelo usuário: PSNR idêntico, hash diferente, diferença máxima de 7.15e-07 — exatamente a
limitação 4 prevista).

**Solução medida nesta fase — spec `pouw-quant-v1`** (`fase2/quantizar.py`): forward em
**float64** + quantização **fixed-point B=16** com limites do desafio (âncora de bytes) +
SHA-256 dos bytes big-endian. Resultados centrais (tudo medido; relatório completo em
`fase2/relatorio_fase2.md`):

- **E1 — 7 caminhos aritméticos reais** (torch/numpy/threads/ordem-de-soma × float32/float64,
  3 seeds): float32 diverge ~1e-07 e vira bins; **float64 diverge ~1e-15 e as quantizações
  B=16 ficam idênticas (HD=0) em 9/9 pares**. O caminho numpy-float32 divergiu do torch em
  7.153e-07 — a MESMA magnitude que o usuário mediu entre CPUs.
- **E2 — 66.000 ensaios de stress:** B=16+float64: **zero viradas até ruído de 1e-10**
  (resíduo real float64 medido: ~1e-15, 5 ordens de grandeza de margem); float32+ruído do
  usuário (7.15e-07): **100% dos ensaios viram o hash** → quantização sem float64 não é consenso.
- **E4 — dificuldade via alvo de PSNR (40→65 dB):** treino 3,9→20,0 s enquanto a verificação
  fica constante (~21 ms) → **a razão treino/verificação CRESCE com a dificuldade: 189× → 901×**.
  6/6 receitas válidas na regra de consenso.
- **E5 — ajuste exponencial:** moagem de prefixo medida até k=24 bits zero (8,6 M tentativas,
  5,5 s a 2,25 M hashes/s em Python puro) — rotulada como queima de hash pura, servindo só de
  ajuste fino sobre o trabalho útil.
- **Verificador de consenso:** `fase2/verificar_fase2.py` (4 checagens, código de saída 0/1).

### Teste cross-CPU (se você é o leitor que divergiu na Fase 1 — é você, Kronos 😉)

```bash
git clone https://github.com/Kronos1027/pouw-siren.git && cd pouw-siren
bash checar_integridade.sh                 # 38 âncoras (15 da F1 + 23 da F2) → 38× OK

python3 fase2/verificar_fase2.py receita_b0f90ffe.pt desafio_b0f90ffe.npy --alvo-psnr 40
# esperado (predição registrada ANTES de você rodar — relatório §10):
#   PSNR: 49.6253 dB
#   COMPROMISSO QUANTIZADO: 93ad1d430c47b1a66f23b3da4cb758c9173d59ef1d72786b9e32afd557e517c8
#   RESULTADO: VÁLIDO (código 0)
# (o hash float32 da Fase 1 divergiu na sua CPU; o hash QUANTIZADO deve bater bit-a-bit)

sha256sum quantizada_b0f90ffe_u16.npy
# esperado: bf583953b977c0619cb290def6f59dfc8f8d7cab38fd20c9af16e1b2af9b3e5b
```

Compromissos oficiais das 4 receitas publicadas (tabela completa no relatório §9):
`93ad1d43…` (seed 001) · `b4b6df84…` (seed 002) · `8397befc…` (seed 003) · `92b6fe06…` (extra 60 dB).

---

## Resultado central da Fase 1 (medido; nada estimado — ver protocolo anti-fabricação abaixo)

Máquina: Intel Xeon, **2 vCPUs** (KVM), 4,1 GiB RAM, **sem GPU** · Python 3.12.14 · NumPy 2.1.3 ·
PyTorch 2.14.0+cpu · specs completas em `relatorio_fase1.md` §2 e `logs/raw/lscpu.txt`.

| Seed | Hash da seed (SHA-256) | Treino (s) | Verificação (s) | Razão | PSNR (dB) |
|------|------------------------|-----------:|----------------:|------:|----------:|
| teste-seed-001 | `b0f90ffe`…`21155` | 4.087526 | 0.013060 | **313,0×** | 49.6253 |
| teste-seed-002 | `d037aef4`…`82208` | 3.928582 | 0.015376 | **255,5×** | 48.3896 |
| teste-seed-003 | `8b457d0a`…`a4ca6` | 4.010014 | 0.014319 | **280,0×** | 49.2587 |

"Verificação" = processo novo e frio: carga da receita do disco + forward + SHA-256 + PSNR,
com 1 thread (escolha conservadora) e sem contar o import do PyTorch — definição completa e
simétrica em `relatorio_fase1.md` §3; custo de import discutido no §9 item 7.

Âncoras de integridade (SHA-256 completos em `hashes.sha256`, `fase2/hashes_fase2.sha256` e
nos relatórios §6/§9):

```
receita_b0f90ffe.pt  6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81
receita_d037aef4.pt  29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e
receita_8b457d0a.pt  98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea
```

**Auditoria da data de publicação (2026-09-02):** `sha256sum -c hashes.sha256` → 15× OK;
verificação re-executada em processo novo com hashes das reconstruções bit-a-bit idênticos
e PSNR 49.6253 / 48.3896 / 49.2587 dB. Saída bruta: `logs/raw/etapa5_*.txt` e
`logs/etapa5_publicacao.md`. **Validação do usuário (cross-CPU):** hash da receita ✓,
PSNR ✓, hash float32 da reconstrução ✗ (7.15e-07) — o disparador da Fase 2.

## Verificar você mesmo (≈5 min)

```bash
# dependências (CPU only)
pip install numpy
pip install torch --index-url https://download.pytorch.org/whl/cpu

git clone https://github.com/Kronos1027/pouw-siren.git
cd pouw-siren

bash checar_integridade.sh        # 38× OK (Fases 1 e 2)

# Fase 1 (float32 — na MESMA máquina os hashes batem; em OUTRA CPU pode divergir no último bit)
python3 -u verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy
#   PSNR: 49.6253 dB | SHA-256 da reconstrução: b2fe66eb… (idêntico só na mesma CPU)

# Fase 2 (float64 + quantizado — deve bater em QUALQUER CPU; é o ponto da fase)
python3 -u fase2/verificar_fase2.py receita_b0f90ffe.pt desafio_b0f90ffe.npy --alvo-psnr 40
#   COMPROMISSO QUANTIZADO: 93ad1d43… (bit-a-bit em qualquer máquina, hipótese da Fase 2)
```

Windows: `certutil -hashfile receita_b0f90ffe.pt SHA256` e compare com `hashes.sha256`.

## Reproduzir do zero

```bash
python3 -u desafio.py teste-seed-001          # → desafio_b0f90ffe.npy (hash f1dffaec…2720bd8)
python3 -u treinar.py desafio_b0f90ffe.npy --max-epocas 5000 --alvo-psnr 40
python3 -u verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy
python3 -u fase2/verificar_fase2.py receita_b0f90ffe.pt desafio_b0f90ffe.npy --alvo-psnr 40
# varredura de dificuldade + experimentos completos:
python3 -u fase2/experimento_dificuldade.py
python3 -u fase2/experimento_caminhos.py
python3 -u fase2/experimento_ruido.py
python3 -u fase2/experimento_prefixo.py receita_b0f90ffe.pt desafio_b0f90ffe.npy
```

O que já foi checado nesta máquina (evidência nos logs):
- re-gerar o desafio → arquivo bit-a-bit idêntico (`logs/etapa1.md`);
- re-treinar a seed 001 → pesos bit-a-bit idênticos, 8/8 tensores (`logs/etapa2.md`);
- `torch.save` NÃO é byte-reproduzível (zip com timestamp) → o hash do `.pt` prova integridade
  da **cópia**; a âncora de reprodutibilidade da Fase 2 é o `.npy` **quantizado**
  (byte-reproduzível: alvo60 treinada na F2 ≡ extra60 treinada na F1, byte-a-byte);
- re-executar a verificação → reconstrução bit-a-bit idêntica (`logs/etapa3.md`);
- E2 re-executado após correção de fórmula teórica → medições idênticas bit-a-bit
  (RNG determinístico; `fase2/logs/raw/f2_e2_ruido*.txt`).

## O que tem neste repositório

```
pouw-siren/
├── README.md                  ← você está aqui
├── relatorio_fase1.md         ← F1: tabela, decisões, comandos, 11 limitações
├── hashes.sha256              ← âncoras F1 (15)
├── checar_integridade.sh      ← checa as 38 âncoras (F1 + F2)
├── requirements.txt
├── desafio.py                 ← F1 ETAPA 1: gerador determinístico de desafios 64×64
├── treinar.py                 ← F1 ETAPA 2: treino SIREN (CPU) → receita .pt (intocado na F2)
├── verificar.py               ← F1 ETAPA 3: verificação independente (float32)
├── checagem_torchsave.py, checagem_retreino.py  ← evidências auxiliares F1
├── desafio_*.npy (3)          ← desafios oficiais
├── receita_*.pt (4)           ← 3 receitas oficiais F1 + 1 extra (60 dB)
├── reconstrucao_*.npy (3)     ← ejeções F1 (float32; âncora somente na mesma CPU)
├── quantizada_*_u16.npy (4)   ← F2: arrays quantizados B=16 (âncoras cross-CPU, byte-reproduzíveis)
├── logs/                      ← F1: etapas 1–3, 5 (publicação) + raw/*.txt (inclusive FALHAS)
└── fase2/
    ├── relatorio_fase2.md     ← relatório completo: spec, E1–E5, 12 limitações
    ├── hashes_fase2.sha256    ← 23 âncoras da F2
    ├── quantizar.py           ← spec canônica pouw-quant-v1 (quantização + hash)
    ├── verificar_fase2.py     ← verificador de consenso (float64 + B=16, código 0/1)
    ├── siren_numpy.py         ← forward SIREN em NumPy (caminho aritmético alternativo)
    ├── experimento_caminhos.py     ← E1: robustez a 7 caminhos aritméticos
    ├── experimento_ruido.py        ← E2+E3: fronteiras + stress de ruído (66k ensaios)
    ├── experimento_dificuldade.py  ← E4: varredura de alvo PSNR (40–65 dB)
    ├── experimento_prefixo.py      ← E5: moagem de prefixo (k até 24 medido)
    ├── receita_alvo*.pt (6)   ← receitas da varredura E4
    ├── quantizada_alvo* (6)   ← quantizações correspondentes
    └── logs/etapa6.md + logs/raw/*.txt  ← outputs brutos (inclusive a execução com bug corrigido)
```

`desafio.py` é o código do prompt original com **2 correções mínimas documentadas**
(`np.PI` → `np.pi`; `h.hexdigest()` → `h.hex()`; tracebacks completos em `logs/etapa1.md`).

## Limitações principais (resumo — 11 itens na F1 §9, 12 itens na F2 §12)

1. O import do PyTorch (~1,1 s) domina a verificação em processo frio; as razões das tabelas
   excluem imports **dos dois lados** (simétrico e declarado). Com runtime pré-carregado,
   a razão é a da tabela.
2. ~~Hash de saída float32 não é portável entre CPUs~~ → **resolvido na Fase 2 pela spec
   pouw-quant-v1** (float64 + B=16), com margem de ~5 ordens de grandeza medida — pendente
   apenas a confirmação cross-CPU do leitor (README acima / relatório F2 §10).
3. Nesta escala não há economia de bytes (receita 138 kB vs desafio 33 kB) — a Fase 1 mede
   assimetria de **tempo**, não razão de compressão.
4. 40 dB é "fácil" para esta família de desafios (época 100); a F2 mediu a curva até 65 dB
   (época 900) e o escalonamento é suave — o ajuste exponencial é feito por prefixo (E5).
5. Moer nonce é queima de hash pura; no design PoUW-SIREN ela só serve de ajuste fino —
   o custo dominante (e útil) continua sendo o treino.

## Próximos passos (Fase 3 — candidatos)

- Confirmação cross-CPU da spec por múltiplos leitores (rodar o teste acima e reportar).
- Forward **exatamente determinístico** (aritmética inteira/fixed-point no forward, sem BLAS)
  para eliminar o resíduo ~1e-15 e a dependência de libm/sin entre implementações.
- Esqueleto de protocolo de cadeia: challenge → receita → bloco com compromisso + nonce;
  geração do desafio também quantizada/ancorada (sin/cos de libm não é garantido idêntico
  entre implementações — o .npy é a âncora).
- Escala: grades maiores, sinais 3D ou reais; runtime persistente / verificação em lote.

## Protocolo anti-fabricação (como esta pesquisa foi conduzida)

1. Nenhum número sem comando realmente executado; o que não rodou está declarado como não-rodado.
2. Todo métrico vem com o output bruto e integral colado (com timestamps, em `logs/raw/*.txt`
   e `fase2/logs/raw/*.txt`).
3. Todo artefato tem SHA-256 reportado (`hashes.sha256` + `fase2/hashes_fase2.sha256`) para
   conferência externa.
4. Tempos só de `time`/`time.perf_counter()`, nunca estimados. A única exceção rotulada:
   extrapolações aritméticas do E5, marcadas como EXTRAPOLADO.
5. Erros reportados completos, sem poda (ver arquivos `*_FALHA.txt` e a execução com bug
   teórico preservada em `fase2/logs/raw/f2_e2_ruido_EXECUCAO1_TEORIA_ERRADA.txt`).
6. Log por etapa + relatório com os comandos exatos na ordem (F1 §7, F2 §11).
7. Dados de terceiros (teste cross-CPU do usuário) citados como tais, nunca misturados com
   medições próprias.

## Notas

- **Nenhuma credencial** (token/segredo) existe neste repositório; a publicação usou um token
  pessoal aplicado apenas ao `git push`, nunca gravado em arquivo versionado. (O token foi
  exposto no chat ao ser enviado — o dono deve revogá-lo se ainda não o fez.)
- Licença: a definir (pesquisa em andamento).
