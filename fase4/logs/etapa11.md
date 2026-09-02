# Etapa 11 — Fase 4 (E1): registro e conferência da validação cross-CPU externa (Windows)

**Início:** 2026-09-02 04:47 UTC · **Fim:** ver logs brutos anexos
**Executor:** agente (registro e conferência). A VALIDAÇÃO em si foi executada pelo dono do
repo na máquina dele (Windows) — ver §2. Dados de terceiros nunca misturados com medições
próprias (protocolo item 7).

## 1. Contexto

A Fase 3 encerrou com a predição §11 do relatório (cadeia 8/8 VÁLIDA em qualquer CPU,
compromissos bit-a-bit) e o convite ao leitor. O dono do repositório respondeu executando o
teste decisivo na própria máquina Windows (a mesma CPU cujo hash float32 divergira na Fase 1):
integridade 75/75 + `python -u fase3/verificar_cadeia.py` → **8/8 VÁLIDOS, código 0,
0,505768 s**. O output integral chegou via chat e é a evidência primária desta etapa.

## 2. Trabalho do agente nesta etapa (tudo executado, nesta ordem)

1. **Verificação de ambiente/estado**: repo local limpo, local ≡ remoto (`d00573f`);
   token GitHub testado (GET /user → HTTP 200, ainda válido — usuário já orientado a revogar).
2. **Transcrição verbatim** do output do usuário → `fase4/logs/raw/f4_e1_saida_windows.txt`
   (com cabeçalho de proveniência: executor, comandos git relatados, canal de transmissão;
   conteúdo entre marcadores ==== sem NENHUMA edição).
3. **Script novo** `fase4/conferir_saida.py`: parseia linhas `[bloco N] VÁLIDO (t s) | PSNR x
   dB | comp 16hex… | hash_bloco 16hex…` de um output capturado e confere contra o
   `fase3/cadeia_demo/cadeia.json` oficial (status, PSNR 4 dec vs psnr_verificacao E
   psnr_treino, prefixos 16 hex de compromisso e hash_bloco, sumário e RESULTADO). Stdlib
   pura; reutilizável por qualquer leitor.
4. **Execução da conferência** (comando real, com timestamps):
   ```bash
   { date -u; time python3 -u fase4/conferir_saida.py fase4/logs/raw/f4_e1_saida_windows.txt; date -u; } \
       2>&1 | tee fase4/logs/raw/f4_e1_conferimento.txt
   ```
   Resultado: **8/8 CONFERE — 100% dos blocos** (código 0; 0,037 s de processo). Log bruto
   anexo. PSNR do output = oficial a 4 decimais nos 8; prefixos comp e hash_bloco = oficiais
   nos 8; sumário 8/8 e "CADEIA VÁLIDA (código 0)" lidos e conferidos.
5. **Relatório formal** `fase4/validacao_cross_cpu_windows.md` (9 seções: o que foi validado,
   tabela de ambientes mineração×validação, comandos relatados, output verbatim, métricas do
   executor, conferência do agente, veredito das predições §11 a/b/c — todas CONFIRMADAS —,
   6 limitações, como reproduzir).

## 3. Decisões

- A validação externa vira a **Fase 4 (E1)** — primeiro item do roadmap F3, agora executado;
  item 2 do roadmap (forward inteiro sem BLAS) permanece aberto.
- A evidência é classificada como **dado de terceiro** em todos os artefatos (cabeçalho do
  raw, relatório §1/§8, README) — o agente só garante a conferência (§6), nunca os números
  da máquina Windows.
- 5 âncoras novas (`fase4/hashes_fase4.sha256`): relatório, script, 2 logs brutos e este log
  de etapa → o total do repo passa de 75 para **80 âncoras** (checar_integridade.sh atualizado).
- `checar_integridade.sh` e README atualizados na mesma etapa; README ganha também a dica
  Windows (`core.autocrlf`) derivada da sequência de comandos do executor.

## 4. Artefatos desta etapa

| Arquivo | Papel |
|---|---|
| `fase4/validacao_cross_cpu_windows.md` | relatório formal da validação (9 seções) |
| `fase4/conferir_saida.py` | ferramenta de conferência (reutilizável por leitores) |
| `fase4/logs/raw/f4_e1_saida_windows.txt` | output do executor, VERBATIM + proveniência |
| `fase4/logs/raw/f4_e1_conferimento.txt` | log bruto da conferência do agente |
| `fase4/logs/etapa11.md` | este log |
| `fase4/hashes_fase4.sha256` | 5 âncoras SHA-256 da fase |

## 5. Resultado central

**A predição §11 da Fase 3 foi confirmada por validação externa:** 8/8 blocos VÁLIDOS na
máquina Windows do dono (SO, Python, PyTorch e NumPy todos diferentes do ambiente de
mineração), compromissos recomputados bit-a-bit idênticos (certificados pela C5 interna +
conferência de prefixos pelo agente), integridade 75/75 no clone dele. A limitação 2 da
Fase 1 (hash não portável) está fechada COM evidência externa; a limitação de consenso
restante é o resíduo teórico ~1e-15 (roadmap F4 item 2: forward inteiro sem BLAS).
