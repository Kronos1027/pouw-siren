# PoUW-SIREN — Proof of Useful Work via compressão neural (Fase 1, CPU-only)

Pesquisa exploratória: usar **compressão neural (SIREN — Implicit Neural Representation)** como
"trabalho útil" no lugar da queima de hash do Proof-of-Work tradicional. O minerador **treina**
uma rede para comprimir um desafio determinístico (segundos — caro); o verificador confere a
**receita** produzida (milissegundos — barato), em processo frio e independente. É a mesma
assimetria produzir-caro/conferir-trivial do PoW — mas com um subproduto **reaproveitável**:
a receita reconstrói o sinal a ~49 dB de PSNR, em vez de virar lixo entrópico como o hash do
bitcoin.

Projeto-irmão / motivação: [Kronos1027/black-hole](https://github.com/Kronos1027/black-hole).

## Resultado central (medido; nada estimado — ver protocolo anti-fabricação abaixo)

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

Âncoras de integridade (SHA-256 completos em `hashes.sha256` e no relatório §6):

```
receita_b0f90ffe.pt  6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81
receita_d037aef4.pt  29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e
receita_8b457d0a.pt  98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea
```

**Auditoria da data de publicação (2026-09-02):** `sha256sum -c hashes.sha256` → 15× OK;
verificação re-executada em processo novo com hashes das reconstruções bit-a-bit idênticos
e PSNR 49.6253 / 48.3896 / 49.2587 dB (tempos de 16,3 / 15,1 / 15,2 ms). Saída bruta:
`logs/raw/etapa5_*.txt` e `logs/etapa5_publicacao.md`.

## Verificar você mesmo (≈5 min)

```bash
# dependências (CPU only)
pip install numpy
pip install torch --index-url https://download.pytorch.org/whl/cpu

git clone https://github.com/Kronos1027/pouw-siren.git   # (ajuste o dono se diferente)
cd pouw-siren

bash checar_integridade.sh        # ou: sha256sum -c hashes.sha256  → 15× OK

python3 -u verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy
# esperado (entre outras linhas):
#   PSNR (reconstrução vs desafio): 49.6253 dB
#   SHA-256 da reconstrução: b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38
```

Windows: `certutil -hashfile receita_b0f90ffe.pt SHA256` e compare com `hashes.sha256`.

Aviso de determinismo entre máquinas: na **mesma** máquina/versões, treino e verificação são
bit-a-bit determinísticos (checado — ver abaixo). Em **outra** CPU/BLAS o hash da reconstrução
pode divergir nos últimos bits (float32 vetorial); nesse caso o **PSNR deve permanecer
49.6253 dB** e o hash da **receita** (o arquivo em si) é a âncora que não muda. Detalhe e
implicação para o design da Fase 2 em `relatorio_fase1.md` §9 item 4.

## Reproduzir do zero

```bash
python3 -u desafio.py teste-seed-001          # → desafio_b0f90ffe.npy (hash f1dffaec…2720bd8)
python3 -u treinar.py desafio_b0f90ffe.npy --max-epocas 5000 --alvo-psnr 40
python3 -u verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy
```

O que já foi checado nesta máquina (evidência nos logs):
- re-gerar o desafio → arquivo bit-a-bit idêntico (`logs/etapa1.md`);
- re-treinar a seed 001 → pesos bit-a-bit idênticos, 8/8 tensores, diferença máxima 0
  (`logs/etapa2.md`, `logs/raw/etapa2_retreino_determinismo.txt`);
- `torch.save` NÃO é byte-reproduzível (zip com timestamp) → o hash do `.pt` prova integridade
  da **cópia**, e o hash da **reconstrução `.npy`** é a âncora de reprodutibilidade
  (`logs/raw/etapa2_checagem_torchsave.txt`);
- re-executar a verificação → reconstrução bit-a-bit idêntica (`logs/etapa3.md`).

## O que tem neste repositório

```
pouw-siren/
├── README.md                  ← você está aqui
├── relatorio_fase1.md         ← relatório completo: tabela, decisões, comandos, 11 limitações
├── hashes.sha256              ← âncoras de integridade (formato sha256sum -c)
├── checar_integridade.sh      ← wrapper da checagem de hashes
├── requirements.txt
├── desafio.py                 ← ETAPA 1: gerador determinístico de desafios 64×64
├── treinar.py                 ← ETAPA 2: treino SIREN (CPU) → receita .pt
├── verificar.py               ← ETAPA 3: verificação independente e fria
├── checagem_torchsave.py      ← extra: evidência de que torch.save não é byte-reproduzível
├── checagem_retreino.py       ← extra: evidência de determinismo bit-a-bit do treino
├── desafio_*.npy              ← 3 desafios oficiais (id = hash da seed no nome)
├── receita_*.pt               ← 3 receitas oficiais + 1 extra (alvo 60 dB)
├── reconstrucao_*.npy         ← ejeções oficiais (np.save, bytes determinísticos)
└── logs/
    ├── etapa1.md, etapa2.md, etapa3.md, etapa5_publicacao.md
    └── raw/*.txt              ← outputs brutos com timestamps, INCLUSIVE as falhas
```

`desafio.py` é o código do prompt original com **2 correções mínimas documentadas**
(`np.PI` → `np.pi`; `h.hexdigest()` → `h.hex()`; tracebacks completos em `logs/etapa1.md`).

## Execuções extras (rotuladas; fora da tabela oficial)

- **Escalonamento de dificuldade:** mesmo desafio da seed 001 com alvo 60 dB → 500 épocas,
  9,739328 s, PSNR 60.8704 dB (`receita_extra_60db_b0f90ffe.pt`). Ou seja: o alvo de PSNR
  funciona como "difficulty" análogo ao do PoW — mas o escalonamento observado é suave
  (40 dB→100 épocas; 60 dB→500 épocas), não exponencial. §5 do relatório.
- Smoke test de 300 épocas, checagens de `torch.save` e de re-treino determinístico.

## Limitações principais (resumo — lista completa com 11 itens no relatório §9)

1. O import do PyTorch (~1,1 s) domina a verificação em processo frio; as razões da tabela
   excluem imports **dos dois lados** (simétrico e declarado). Com processo frio dos dois
   lados a razão cai para ~2,5–4×; com runtime pré-carregado, volta à da tabela.
2. Hash de saída float32 não é portável entre CPUs no último bit → Fase 2 deve usar saída
   quantizada (fixed-point) ou comparação tolerante.
3. Nesta escala não há economia de bytes (receita 138 kB vs desafio 33 kB) — a Fase 1 mede
   assimetria de **tempo**, não razão de compressão.
4. 40 dB é "fácil" para esta família de desafios (época 100); máquina modesta, 2 vCPUs,
   1 execução oficial por seed.

## Próximos passos (Fase 2 — candidatos)

- Hash de saída **quantizada/fixed-point** para determinismo cross-CPU (requisito de consenso).
- Dificuldade parametrizável com escalonamento mais agressivo (alvo de PSNR, redes/grades
  maiores, sinais 3D ou reais).
- Runtime persistente / verificação em lote para eliminar o custo de import por receita.
- Esqueleto de protocolo: challenge → receita → verificação por pares, com a receita como
  bloco reaproveitável.

## Protocolo anti-fabricação (como esta pesquisa foi conduzida)

1. Nenhum número sem comando realmente executado; o que não rodou está declarado como não-rodado.
2. Todo métrico vem com o output bruto e integral colado (com timestamps, em `logs/raw/*.txt`).
3. Todo artefato tem SHA-256 reportado (`hashes.sha256`, relatório §6) para conferência externa.
4. Temos só de `time`/`time.perf_counter()`, nunca estimados.
5. Erros reportados completos, sem poda (ver arquivos `*_FALHA.txt` em `logs/raw/`).
6. Log por etapa + relatório com os comandos exatos na ordem.

## Notas

- **Nenhuma credencial** (token/segredo) existe neste repositório; a publicação usou um token
  pessoal aplicado apenas ao `git push`, nunca gravado em arquivo versionado.
- Licença: a definir (pesquisa em andamento).
