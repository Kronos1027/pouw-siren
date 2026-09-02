# logs/etapa7_publicacao.md — Fase 2: publicação no GitHub (Task ID 3)

**Data:** 2026-09-02 · **Repo:** https://github.com/Kronos1027/pouw-siren · **Script:** `scripts/publicar_fase2.sh` (sessão; fora do repo) · **Output bruto integral:** `fase2/logs/raw/f2_publicacao.txt`

## Sequência executada

1. **Auditoria de vazamento (antes do commit):** grep da chave pessoal no diretório do repo (excluindo `.git`) e no conteúdo versionado (HEAD) — **OK nas duas** (a chave mora em `/home/z/my-project/.github_token`, chmod 600, fora do repo; usada apenas via GIT_ASKPASS; nunca em URL, config, arquivos ou commits).
2. **Status pré-commit:** 7 caminhos alterados/novos (`README.md`, `checar_integridade.sh` modificados; `fase2/` e 4 `quantizada_*_u16.npy` novos).
3. **Commit 1 — conteúdo da Fase 2:** `d12eb024b4e0c3f0093abb95758d0b203116e51e` ("Fase 2 - consenso cross-CPU: spec pouw-quant-v1 … 23 ancoras SHA-256, relatorio e logs brutos (protocolo anti-fabricacao)").
4. **Push:** `9e63e61..d12eb02 main -> main` (GIT_ASKPASS, GIT_TERMINAL_PROMPT=0).
5. **Conferência remota:**
   - `git ls-remote` (anônimo): HEAD e refs/heads/main = `d12eb024b4e0c3f0093abb95758d0b203116e51e` ✓
   - API `GET /repos`: 1ª tentativa **FALHOU** — rate limit anônimo do IP (`"API rate limit exceeded for 8.212.10.159"`; output bruto preservado). Reteste autenticado: `full_name: Kronos1027/pouw-siren`, `pushed_at: 2026-09-02T03:16:45Z`, `branch: main` ✓.
   - API `GET /contents/` (autenticada): **28 entradas na raiz** (4 `quantizada_*_u16.npy` novos presentes) ✓.
   - API `GET /contents/fase2` (autenticada): **22 entradas** (7 scripts, relatório, hashes, 6 receitas, 6 quantizadas, logs) ✓.
   - API `GET /contents/quantizada_b0f90ffe_u16.npy`: conteúdo decodificado em base64 → SHA-256 **`bf583953b977c0619cb290def6f59dfc8f8d7cab38fd20c9af16e1b2af9b3e5b`**, size 8320 B — **idêntico ao arquivo local** (byte-a-byte via API) ✓.
6. **Commit 2 — este log:** (modo 2 do script; hash registrado no output bruto abaixo e no `git log`).

## Incidentes

- **API rate limit (anônimo):** a conferência via API sem autenticação excedeu o limite de rate do IP compartilhado; resolvido com header de autorização (a chave seguiu somente no header do curl, nunca em arquivo). A conferência primária da publicação é o `git ls-remote` + o push em si, que já haviam confirmado `d12eb02`.
- Nenhum vazamento de credencial (2 auditorias automáticas por modo + verificação manual das saídas).

## Resultado

- **Publicada a Fase 2 completa** no `main`: spec `pouw-quant-v1`, verificador de consenso, 4 experimentos, compromissos oficiais, 23 âncoras SHA-256 (23× OK localmente; artefato binário conferido remotamente byte-a-byte), relatório com 12 limitações e logs brutos (incluindo a execução com bug teórico preservada).
- Estado local ≡ remoto (ls-remote + API + verificação binária).
