# logs/etapa8_conserto_e2.md — Conserto da pendência de publicação do E2 (Task ID 4)

**Data:** 2026-09-02 (timestamps UTC no log bruto `fase2/logs/raw/f2_conserto.txt`) · **Repo:** https://github.com/Kronos1027/pouw-siren · **Script:** `scripts/publicar_conserto_e2.sh` (sessão; fora do repo)

## O que aconteceu (incidente)

A sessão que publicou a Fase 2 (commits `d12eb02` + `e53dd6a`) perdeu o contexto **entre** o push final
(03:17:52 UTC) e a conclusão de uma checagem que ela própria havia iniciado às 03:18:09 UTC sobre os logs
do E2 (o bloco `CHECAGEM F2_E2_RUIDO` no fim de `f2_e2_ruido.txt`/`f2_publicacao.txt` ficou truncado no
arquivo do meio).

**O problema:** na hora do commit, o arquivo `fase2/logs/raw/f2_e2_ruido_EXECUCAO1_TEORIA_ERRADA.txt`
continha, por engano, a **re-execução pós-correção** (início 03:06:34 UTC) — e foi assim que subiu para o
GitHub. A **1ª execução crua** com o bug da fórmula bilateral (início 03:04:20 UTC) estava apenas no disco,
e o arquivo destinado à re-execução (`fase2/logs/raw/f2_e2_ruido.txt`, citado no §6 do relatório) **nunca
foi commitado** — permaneceu não-rastreado.

**A correção no disco** (feita pela sessão anterior às ~03:18, visível no diff do working tree): restaurar
a 1ª execução crua no arquivo `…_TEORIA_ERRADA.txt` e gravar a re-execução corrigida em
`fase2/logs/raw/f2_e2_ruido.txt`. A sessão morreu antes de commitar. Esta etapa commita e publica esse
estado já corrigido.

## Evidências (hashes medidos antes do conserto)

| objeto | SHA-256 | conteúdo |
|---|---|---|
| `…_TEORIA_ERRADA.txt` **no commit e53dd6a** | `fa0539c11c32fa5ed87f193b40706b17077c017b787c78682160b835c3f1bbcd` | re-execução 03:06:34 (erradamente publicada sob esse nome) |
| `…_TEORIA_ERRADA.txt` **em disco (correto)** | `9823606778a1978812d8097fef24d306bd574935942a8b84cea58fe16bea1e41` | 1ª execução crua 03:04:20 (teoria bilateral, E[flips] 22.212) |
| `f2_e2_ruido.txt` **em disco (não-rastreado)** | `fa0539c11c32fa5ed87f193b40706b17077c017b787c78682160b835c3f1bbcd` | re-execução 03:06:34 (teoria corrigida, E[flips] 11.106) |

(Fato objetivo: o hash `fa0539c1…` confirma que o conteúdo publicado como "TEORIA_ERRADA" era
byte-a-byte a re-execução — o arquivo certo com o nome errado, e o arquivo certo sem publicação.)

## Impacto avaliado

- **Nenhuma âncora afetada:** `fase2/hashes_fase2.sha256` (23 âncoras) cobre scripts, receitas e
  quantizações — **não** cobre logs brutos; `sha256sum -c` no clone público sempre passou e continua
  passando.
- **Nenhum número do relatório afetado:** o §6 do `relatorio_fase2.md` cita ambas as execuções; a partir
  deste conserto o leitor do clone encontra os **dois** logs brutos, corretamente nomeados.
- **Medições idênticas nas duas execuções** (RNG determinístico `default_rng(20260902)`): os contadores
  627/1382/1958/249… batem entre os dois arquivos; a única diferença de conteúdo é a coluna teórica
  (2× de erro na 1ª) — o que a própria narrativa do §6 documenta.

## Sequência executada

1. Evidências coletadas (`git show`, `sha256sum`, `git cat-file -e`) — acima.
2. Auditoria de vazamento da chave pessoal (grep no diretório + no HEAD) — script modo 1.
3. Commit do estado corrigido do disco: `f2_e2_ruido.txt` (novo), `…_TEORIA_ERRADA.txt` (restauração da
   1ª execução crua), `f2_publicacao.txt` (auto-referência pendente) e este log.
4. Push + conferência remota (`git ls-remote` + API).
5. Commit final do log bruto do conserto (modo 2; linhas auto-referentes residuais entram no próximo
   commit de conteúdo — a Fase 3).

## Resultado

- Clone público volta a refletir o disco byte-a-byte; as duas execuções do E2 estão publicadas com os
  nomes corretos; histórico do incidente preservado (este log + o diff do commit).
