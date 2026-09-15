# Etapa 14 — Publicação da Fase 5

**Data:** 2026-09-15 02:05–02:10 UTC · Script: `/home/z/my-project/scripts/publicar_fase5.sh` (fora do repo; token via GIT_ASKPASS, nunca em URL/arquivo versionado).

## Modo 1 — commit do conteúdo + push

- Auditoria de vazamento: chave pessoal AUSENTE do diretório e do histórico (grep duplo) — OK.
- Commit `11afff4` (main): 44 arquivos (41 de `fase5/` + README.md + checar_integridade.sh atualizados + log parcial de publicação) — mensagem completa descrevendo a spec pouw-int-v1, E2–E5, as 8 verificações frias, as 4 execuções com erro preservadas e as +40 âncoras (80→120).
- Push `e85bfff..11afff4` via GIT_ASKPASS (URL limpa, sem token).
- Conferência remota:
  - `git ls-remote` (anônimo): HEAD = `11afff47e6d70a872d2482cfe052dde10c00f078` ✓
  - API `GET /repos/Kronos1027/pouw-siren` (autenticada): `pushed_at 2026-09-15T02:08:51Z`, branch main ✓
  - API `GET /contents/fase5`: 11 entradas (7 .py + hashes_fase5.sha256 + logs/ + pesos_int/ + relatorio_fase5.md), tamanhos idênticos aos locais ✓
- Integridade pós-push: `bash checar_integridade.sh` → **120/120 OK** (15 F1 + 23 F2 + 37 F3 + 5 F4 + 40 F5).

## Modo 2 — fechamento documental

- Commit final com o log bruto integral de publicação (`fase5/logs/raw/f5_publicacao.txt`, completo) — o mesmo fechamento documental das F3/F4 (o log parcial entra no modo 1 porque o `tee` cria o arquivo antes do `git add -A`; o modo 2 grava as linhas finais).

## Estado final

- Repo `Kronos1027/pouw-siren` @ commit do modo 2, local ≡ remoto, árvore limpa.
- **120 âncoras SHA-256** íntegras local e remotamente.
- Fase 5 fechada: caminho de verificação 100% inteiro (`pouw-int-v1`) — 18/18 payloads bit-a-bit idênticos ao caminho float64/BLAS/libm; 8/8 verificações frias zero-float VÁLIDAS; roadmap "forward inteiro sem BLAS" EXECUTADO.
