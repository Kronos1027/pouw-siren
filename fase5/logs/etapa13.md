# Etapa 13 — PoUW Fase 5: caminho de verificação 100% inteiro (pouw-int-v1)

**Data:** 2026-09-15 (00:35–02:05 UTC) · **Agente:** Super Z · **Mandato do usuário:** "prossiga com a pesquisa testes rigorosos e avance com calma validando e testando tudo garantindo que sejam dados reais" (continuação do mandato permanente das fases anteriores).

Protocolo anti-fabricação em vigor (6 itens). Todos os números abaixo vêm de
execuções reais cujos outputs brutos estão em `fase5/logs/raw/*.txt` com
timestamps; nenhum número foi estimado.

---

## 13.1 — Recuperação de ambiente (E0)

O ambiente da sessão havia sido RESETADO (fim do contexto anterior): o `.git`
do clone foi substituído por um repo genérico de restore (commits UUID, sem
`origin`) e o PyTorch foi desinstalado. Os ARQUIVOS persistiram.

1. **Integridade do conteúdo independente do git:** as 80 âncoras SHA-256
   (15 F1 + 23 F2 + 37 F3 + 5 F4) conferidas pós-restore → **80/80 OK**
   (`f5_e0_integridade_pos_restore.txt`). O sistema de âncoras cumpriu sua
   função: a perda do git não comprometeu a verificabilidade.
2. **PyTorch reinstalado:** `python3 -m pip install torch
   --index-url https://download.pytorch.org/whl/cpu` → torch 2.14.0+cpu
   (mesma versão do ambiente original) + numpy 2.1.3 persistente
   (`f5_e0_pip_install_torch.txt`).
3. **Token conferido:** GET /user → HTTP 200, login Kronos1027 (id 84149831);
   chave lida de `/home/z/my-project/.github_token` (fora do repo, nunca
   impressa).
4. **Git religado:** `git init -b main` + remote limpo (sem token na URL) +
   fetch via GIT_ASKPASS + `reset --hard origin/main` → HEAD em `e85bfff`
   (estado publicado da F4); integridade re-conferida 80/80; árvore limpa
   exceto `fase5/` novo (`f5_e0_git_religacao.txt`).
5. **Regressão da cadeia F3:** `python3 -u fase3/verificar_cadeia.py` →
   **8/8 VÁLIDOS, código 0, 0,140862 s** (sem imports); PSNR/compromissos/
   hashes idênticos ao publicado (bloco 1: 47,8726 dB, `cd579702…`,
   `000058a7…`) — os mesmos valores que a máquina Windows do dono obteve na
   F4 (`f5_e0_cadeia_fresca.txt`).

## 13.2 — Projeto da spec (dados medidos antes de escrever o código)

Medidos nas 8 receitas da cadeia (`receita_01..08.pt`): grade **64×64**
(4096 pontos); arquitetura `2→128→128→128→1`, ω₀=30; **max|w| = 0,501647**;
**max|b| = 0,706801**; **max|ω₀·z| = 49,8915** (⇒ |k| da redução ≤ 32).
Com esses números, o formato **Q63** foi escolhido com orçamento de erro
pior-caso ≈ 2⁻³⁰ contra passo da grade B=16 ≈ 2⁻¹³·³ (margem de ~16 ordens).

## 13.3 — Implementação (fase5/)

- **`siren_int.py`** — spec canônica `pouw-int-v1` + implementação de
  referência: Q63; `rhe`/`divround` (half-even, a MESMA regra do `np.rint`
  da v1); literal de π PINADO (50 dígitos, verificável por fórmula de Machin
  em bigint); seno inteiro (redução por π/2 + Taylor até r¹⁹/r¹⁸ com
  coeficientes racionais exatos arredondados uma vez); forward com
  acumulador Q126 exato; quantização inteira exata; gate por desigualdade
  inteira; leitor de .npy POR BITS (sem numpy); pesos canônicos .bin
  (int64 LE). Importa apenas `hashlib`, `sys`, `ast`.
- **`exportar_pesos_int.py`** — .pt → .bin (torch usado SÓ para
  desserializar; conversão float32→Q63 por bits, sem aritmética de float).
- **`verificar_int.py`** — verificador FRIO 100% stdlib: auditoria zero-float
  em runtime (`sys.modules`), âncoras H1/H2, compromisso C1, gate exato C2,
  comparação de payload C3; tempos em `perf_counter_ns` (inteiros) com
  decimais formatados por `divmod`.

**Incidente pego pela auditoria:** a 1ª execução do verificar_int falhou na
auditoria porque **`pathlib` importa `math`** (infiltração stdlib identificada
por teste isolado em subprocessos limpos); `pathlib` foi excluído do
verificador e o incidente documentado no próprio código e no log
(`f5_verificar_int_frio_bloco1.txt` registra a versão final aprovada).

## 13.4 — Smoke (S1–S7, `f5_smoke_int.txt`)

S1 arredondamentos ≡ `np.rint` (9+6 casos, incl. empates negativos) · S2
literal de π ≡ Machin bigint (51 dígitos; a 1ª execução tinha um erro
OFF-BY-ONE NO TESTE — comparava 51 chars com 50 — corrigido; o literal estava
certo) · S3 `sin_q(k·π/2)` = 0/±1 EXATOS para k∈[−40,40] · S4 `sin_q` vs
`numpy.sin` em ~128.580 pontos diádicos exatos: pior 1,11e-16 (1 ulp — o erro
do próprio numpy domina) · S5 empates .5 do quantizador ≡ `np.rint` e
equivalência no dado real (0/4096 bins) · S6 **forward do bloco 1: max|ΔR| =
7,327e-15 (0,00 passo B16), 0/4096 bins, payload idêntico; hashes v1×v2
divergem POR PROJETO (header de domínio distinto), a checagem correta é a do
payload — reformulada após a 1ª redação equivocada**; gates concordam · S7
re-export determinístico (bytes idênticos).

## 13.5 — E1: exportação das 18 receitas (`f5_e1_exportacao.txt`)

18/18 exportadas (8 cadeia + 4 F1 + 6 F2), cada uma com SHA-256 reportado;
**determinismo do export confirmado em 18/18** (2ª passada, `cmp` byte a
byte). **Achado:** os `.pt` de `b0f90ffe`, `alvo40db` e `alvo45db` têm SHA
DIFERENTE (timestamps do zip do torch.save — limitação conhecida da F1), mas
os pesos exportados são **byte-idênticos** (`9b8617c4…` ×3; idem
`extra60db` ≡ `alvo60db`, `bda592cf…` ×2): 18 artefatos = **14 conjuntos
distintos de pesos** (parada determinística no mesmo checkpoint quando
PSNR ≥ 40 e ≥ 45 na época 100). O `.bin` ancora os PESOS, não a embalagem.

## 13.6 — E2: ordem de soma (`f5_e2_ordem.txt`)

Camada 2 da receita_01 (128 unidades × 128 canais × 4096 pontos =
**67.108.864 termos por ordem**):
- **INTEIRO:** 3 ordens (direta/reversa/árvore pareada) → **0 de 524.288
  valores diferentes bit-a-bit** — exatidão por construção.
- **FLOAT64:** mesmas 3 ordens + GEMM do BLAS → **~90% dos valores mudam de
  bits** entre pares (máx 374.287–470.515 de 524.288; max|Δz| = 1,7e-16 a
  3,9e-16), bins B16 de proxy: 0 (margem absorve).
- 1ª execução preservada (`…EXECUCAO1_NUMERO_EXIBIDO_ERRADO.txt`): meu texto
  final exibia o total errado (16.777.216 em vez de 524.288) — medições
  corretas, rótulo corrigido.

## 13.7 — E4: suíte adversarial (`f5_e4_negativos.txt`)

- **Sweep de sensibilidade** (1 peso, W₁[0][0]): δ=1 a 2³³ LSB Q63
  (1,1e-19 a 9,3e-10 do sinal) → **0 bins, hash inalterado** (invisível por
  projeto — piso da grade, ecoando F2/E2); δ=2⁴⁰ (1,2e-7) → **2 bins, hash
  muda**. 1ª execução preservada (`…EXECUCAO1_LEITURA_ERRADA.txt`): LEITURA
  previa piso em 2³⁰–2³³; o MEDIDO é 2⁴⁰ — corrigida.
- **N1–N6 (subprocessos frios): 6/6 conforme esperado** — N1 controle
  positivo VÁLIDO (C1 CONFERE + C3 payload 0/4096); N2 compromisso
  adulterado → C1; N3 pesos de outro bloco → C1 + C2 (margem ∞); N4 desafio
  adulterado (byte do pixel máximo) → H2 + C1 (comp muda para `d75a2977…`);
  N5 swap de pesos x↔y → C1 + C2 (0,69×); N6 gate rígido 50 dB com receita
  ~40 dB → C2 (0,91×).

## 13.8 — E3+E5: equivalência oficial (`f5_e3_equivalencia.txt`)

- **1ª execução preservada** (`…EXECUCAO1_ALVO_45_NAO_SUPORTADO.txt`): a
  escada da F2 usa alvos 45/55/65 dB e o gate exigia múltiplos de 10 —
  **lacuna da spec descoberta pelos dados**. Correção sem floats: gate
  estendido a múltiplos de 5 dB (r=5 via **raiz quadrada inteira** Newton,
  empate provavelmente impossível; erro ≤ 2⁻⁶⁴ relativo); thresholds
  conferidos contra 10^(a/10) em 6 decimais.
- **Execução oficial (após correção): 18/18 payloads quantizados
  v1(float64/BLAS/libm) ≡ v2(inteiro) bit-a-bit — 0 bins divergentes em
  73.728 comparações; 18/18 gates concordantes; max|ΔR| global 1,31e-14.**
- **E5 (custos):** forward v1 média 0,0175 s; v2 média 27,44 s; **razão
  1.569×** (custo honesto da exatidão por construção em Python puro).
- **8/8 verificações FRIO do verificar_int.py VÁLIDAS** (processos próprios,
  auditoria zero-float em cada, âncoras completas, C1 CONFERE e C3 payload
  0/4096 em todas) — log frio integral do bloco 1 em
  `f5_verificar_int_frio_bloco1.txt` (re-executado com o código final).

## 13.9 — Documentação e âncoras

`relatorio_fase5.md` (este diretório) + `hashes_fase5.sha256` (40 âncoras:
7 códigos + 18 .bin + 13 logs brutos + etapa13 + relatório) → total do repo
**80 → 120**; `checar_integridade.sh` e `README.md` atualizados. Publicação:
`scripts/publicar_fase5.sh` (modos 1 e 2), fora do repo, token via
GIT_ASKPASS.
