# logs/etapa6.md — Fase 2: consenso cross-CPU via quantização + dificuldade escalável

**Task ID:** 3 (sessão de 2026-09-02, retomada após validação cross-CPU do usuário)
**Gatilho:** o usuário rodou a Fase 1 na própria CPU e reportou: hash da receita ✓ bit-a-bit, PSNR ✓ 49.6253 dB, hash da reconstrução float32 ✗ (`83fc3a76…` vs `b2fe66eb…`), diferença máxima absoluta entre os floats: **7.15e-07** — confirmando a limitação 4 da Fase 1. Autorizada a execução da Fase 2 até dados suficientes, com publicação no repo.

**Formato:** idêntico às etapas 1–3 da Fase 1 — cada comando embrulhado em `{ date -u …; time <cmd>; date -u …; } 2>&1 | tee fase2/logs/raw/<arquivo>.txt`. Outputs INTEGRAIS estão nos arquivos raw citados; abaixo, comandos + resultados-chave + incidentes.

---

## 6.0 Ambiente (reconferido)

- git working tree limpo, HEAD `9e63e61` (Fase 1 publicada), remote origin OK, token presente fora do repo, torch 2.14.0+cpu / numpy 2.1.3 / Python 3.12.14, nproc 2. (Sem log dedicado — comando de sanity executado interativamente no início; ambiente idêntico ao da Fase 1.)

## 6.1 Spec canônica de quantização — `fase2/quantizar.py` (novo, 6142 B)

- Implementa **pouw-quant-v1**: fixed-point B bits, limites lo/hi do DESAFIO (âncora de bytes), aritmética escalar float64, `np.rint` (meio-para-par), clip, bytes big-endian `>u2/>u1`, pré-imagem com prefixo de domínio `pouw-quant-v1|B=<B>|<H>x<W>|`.
- Smoke (raw: `f2_smoke_quantizar.txt`): seed 001, B=16 → passo 1.0556e-04, PSNR cru 49.6253 → dequantizado 49.6252 dB (custo 0,0001 dB); B=8 → PSNR 49.1348 dB (custo 0,49 dB); hash B=16 `80ecfe99…`, B=8 `1c8a403c…` (sobre a reconstrução float32 da Fase 1).

## 6.2 Verificador de consenso — `fase2/verificar_fase2.py` (novo, 10602 B)

- forward **float64** (pesos convertidos exatos), 1 thread, checagem de âncora do desafio (meta da receita vs sha256 do arquivo), quantização B=16, PSNR float64, `--alvo-psnr` → código de saída 0/1 (oracle de consenso); salva `quantizada_<tag>_u16.npy` (âncora de arquivo conferível com sha256sum).
- Smoke (raw: `f2_smoke_verificar_fase2.txt`): seed 001 → PSNR 49.6253 dB, âncora OK, verificação 0.019184 s, compromisso `93ad1d43…`, arquivo quantizado `bf583953…`, RESULTADO VÁLIDO (código 0).

## 6.3 E1 — caminhos aritméticos (raw: `f2_e1_caminhos.txt`)

`python3 -u fase2/experimento_caminhos.py` — 7 caminhos × 3 seeds. Resultados-chave:
- Continuidade: p1 (torch32 1t) ≡ arquivos `reconstrucao_*.npy` oficiais, bit-a-bit, 3/3.
- p3 (numpy32) vs p1: max|Δ| = 7.153e-07 — **mesma magnitude do dado do usuário (7.15e-07)**.
- Família float64 (p5 torch64 / p6 numpy64 / p7 numpy64-bloc16): pares divergem ~1e-15 e quantizações B=16 **idênticas (HD=0) em 9/9 pares**; hashes dos 3 caminhos iguais por seed.
- float32↔float64 (p1 vs p5): max|Δ| ~2e-06, HD16 = 15/21/9 → hashes diferentes → a spec exige float64 dos dois lados.
- p2 (2 threads) ≡ p1: threads não mudam bits nesta CPU (GEMM paraleliza por linhas) — registrado como limitação.

## 6.4 E2+E3 — fronteiras + stress (raw: `f2_e2_ruido.txt` + `f2_e2_ruido_EXECUCAO1_TEORIA_ERRADA.txt`)

`python3 -u fase2/experimento_ruido.py` — E3: distâncias mínimas à fronteira B=16: 3.553e-09 / 1.415e-08 / 7.276e-10 (por seed). E2: 2000 ensaios/ponto, varredura 1e-16…7.15e-07.
- **B=16 + float64: 0 viradas até ε=1e-10 (todos os pontos, 3 seeds); 1ª virada ε=1e-09 (seed 8b457d0a); ε=7.15e-07 → 100%**.
- Baseline float32 + ε do usuário (7.15e-07): B=16 vira em 2000/2000 (HD máx 30); B=8: 0/2000.
- **INCIDENTE 1 (documentado):** a fórmula teórica de flips da 1ª versão era bilateral (superestimava exatamente 2×); os DADOS medidos apontaram o erro (1758 HD/2000 ensaios = 0,879 vs teoria antiga 1,755). Corrigida para unicaudal `(ε−d)/(2ε)`, re-executada; teoria passou a bater (0,877 vs 0,879 etc.). A 1ª execução crua foi PRESERVADA (`f2_e2_ruido_EXECUCAO1_TEORIA_ERRADA.txt`); a re-execução reproduziu as medições bit-a-bit (RNG `default_rng(20260902)` determinístico) — checagem extra de reprodutibilidade de graça.

## 6.5 E4 — dificuldade via alvo de PSNR (raw: `f2_e4_dificuldade.txt`)

`python3 -u fase2/experimento_dificuldade.py` — `treinar.py` da Fase 1 intocado; alvos 40/45/50/55/60/65 dB; verificação float64+B16 com código de saída. Tabela completa no relatório §7. Resultados-chave:
- Treino 3,93 → 20,01 s (5,1×) enquanto verificação 0,0208 → 0,0222 s (+7%) → **razão 189× → 901×** (dificuldade escala só o lado caro).
- 6/6 receitas VÁLIDAS na regra de consenso.
- Determinismo extra: alvo60 hoje ≡ extra60 da Fase 1 (mesmo compromisso `92b6fe06…`, .npy quantizado byte-a-byte `cbeacc70…`); alvo40 ≡ receita oficial seed 001 (`bf583953…`).
- Margem navalha no 65 dB: parou em 65.0004 contra alvo 65.0 (verificação concordou; limitação nº 4 do relatório).

## 6.6 E5 — prefixo exponencial (raw: `f2_e5_prefixo.txt`)

`python3 -u fase2/experimento_prefixo.py receita_b0f90ffe.pt desafio_b0f90ffe.npy` — compromisso real recomputado; taxa calibrada 2.249 M hashes/s (Python puro, 1 thread); k=8/12/16/20 (3 ensaios) e k=24 (1 ensaio: 8.616.058 tentativas, 5,496 s); extrapolação k=28…40 rotulada como NÃO executada; framing anti-PoW-puro impresso no próprio output.

## 6.7 Compromissos oficiais (raw: `f2_verif_oficial_*.txt` ×4)

3 seeds da Fase 1 + extra 60 dB, todos VÁLIDOS (código 0). Compromissos: `93ad1d43…` (b0f90ffe, PSNR 49.6253, 0.021214 s), `b4b6df84…` (d037aef4, 48.3896, 0.021366 s), `8397befc…` (8b457d0a, 49.2587, 0.019897 s), `92b6fe06…` (extra 60dB, 60.8704, 0.020286 s). **Estas são as âncoras para o teste cross-CPU do leitor** (relatório §10, com predição registrada ANTES do teste).

## 6.8 Âncoras e integridade (raw: `f2_inventario_hashes.txt`, `f2_hash_check.txt`)

- `fase2/hashes_fase2.sha256`: 23 âncoras (7 scripts, 6 receitas, 6 quantizadas fase2/, 4 quantizadas raiz) → `sha256sum -c` = **23× OK**.
- Cross-checks por `cmp`: extra60-F1 ≡ alvo60-E4 byte-a-byte; alvo40-E4 ≡ oficial seed 001 byte-a-byte.
- **INCIDENTE 2 (documentado):** na 1ª redação do relatório §9, três tempos de verificação foram escritos a partir de memória em vez de copiados dos logs; detectados na auto-revisão de integridade e corrigidos verbatim das linhas `TEMPO TOTAL DE VERIFICAÇÃO` (0.021214 / 0.021366 / 0.019897 / 0.020286). Nenhum outro número foi escrito sem fonte; todos os demais valores do relatório foram conferidos contra os logs brutos.
- Scripts e artefatos novos: 7 `.py` (fase2/), 6 receitas `.pt` (fase2/), 10 `.npy` quantizados (6 fase2/ + 4 raiz), `relatorio_fase2.md`, `hashes_fase2.sha256`, este log e 12 arquivos raw em `fase2/logs/raw/`.

## 6.9 Publicação

Commit e push no repo `Kronos1027/pouw-siren` (branch main), com auditoria de vazamento do token antes do commit e no conteúdo versionado; conferência via `git ls-remote` + API. Detalhes em `fase2/logs/etapa7_publicacao.md` (gerado pela execução de publicação).
