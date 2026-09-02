# logs/etapa10_publicacao.md — Fase 3: publicação no GitHub (Task ID 4)

**Data:** 2026-09-02 · **Repo:** https://github.com/Kronos1027/pouw-siren · **Script:** `scripts/publicar_fase3.sh` (sessão; fora do repo) · **Output bruto integral:** `fase3/logs/raw/f3_publicacao.txt`

## Sequência executada

1. **Checagem de integridade pré-publicação:** `bash checar_integridade.sh` → **75× OK**
   (15 âncoras F1 + 23 F2 + 37 F3).
2. **Auditoria de vazamento (antes do commit):** grep da chave pessoal no diretório do repo
   (excluindo `.git`) e no conteúdo versionado (HEAD) — OK nas duas (a chave mora em
   `/home/z/my-project/.github_token`, chmod 600, FORA do repo; usada apenas via GIT_ASKPASS;
   nunca em URL, config, arquivos ou commits).
3. **Status pré-commit:** ~60 caminhos novos (fase3/ inteira) + 2 modificados
   (README.md, checar_integridade.sh) + linhas auto-referentes do log do conserto E2
   (etapa 8, herdadas por design — ver `fase2/logs/etapa8_conserto_e2.md` item 5).
4. **Commit 1 — conteúdo da Fase 3:** mensagem "Fase 3 - cadeia demo encadeada
   pouw-cadeia-demo-v1 … 37 âncoras SHA-256, relatório e logs brutos (protocolo
   anti-fabricação)" (hash no output bruto e no `git log`).
5. **Push** (GIT_ASKPASS, GIT_TERMINAL_PROMPT=0) + **conferência remota:** `git ls-remote`
   (anônimo: HEAD e refs/heads/main no novo commit) + API `GET /repos` autenticada
   (`full_name`, `pushed_at`, `default_branch`) + `GET /contents/fase3` (22 entradas esperadas:
   5 scripts, relatório, hashes, cadeia_demo/, smoke/, logs/).
6. **Commit 2 — este log + o log bruto** (modo 2 do script; auto-referência residual esperada).

## Resultado

- Fase 3 completa publicada no `main`: cadeia oficial de 8 blocos (esqueleto de protocolo
  encadeado, candidato 3 do roadmap) + verificação em lote (candidato 4 parcial), verificador com
  9 checagens por bloco, 6/6 fraudes rejeitadas, E5 do contraexemplo de re-treino, 37 âncoras
  novas (75 no repo), relatório com 13 limitações e logs brutos integrais (incluindo a execução
  com expectativa errada preservada).
- Nenhuma credencial vazida (auditoria automática por modo + revisão manual).
