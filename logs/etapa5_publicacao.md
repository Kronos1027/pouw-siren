# Log — Etapa 5: auditoria de integridade e publicação no GitHub

**Datas (UTC):** auditoria 2026-09-02 02:18:54 · publicação 02:22:28 · este log 02:23:56
**Agente:** Super Z (continuação do Task ID 1; nenhum subagente; todos os comandos executados diretamente)
**Escopo:** ANTES de publicar, auditar os artefatos ATUAIS da Fase 1 contra os hashes REGISTRADOS
no `relatorio_fase1.md` (§ 6) e re-executar a verificação em processo novo; em seguida, criar o
repositório público `Kronos1027/pouw-siren` e subir o conteúdo integral com toda a documentação.

**Protocolo anti-fabricação nesta etapa:** nenhum número sem comando executado; outputs colados
integrais (com uma divergência de EXIBIÇÃO explicada e provada em § 3); SHA-256 de todo arquivo
novo; tempos medidos; nenhuma credencial publicada (auditorias de vazamento em § 5).

---

## 1. Auditoria 1 — hashes dos artefatos atuais vs relatório § 6

Comando (a partir de `/home/z/my-project/download/pouw_fase1`; script integral em
`/home/z/my-project/scripts/etapa5_auditoria.sh`, fora do repo):

```
bash /home/z/my-project/scripts/etapa5_auditoria.sh
```

Saída original (cópia integral em `logs/raw/etapa5_hash_check.txt`):

```
==============================================================
AUDITORIA 1 — hashes.sha256 vs arquivos atuais (relatorio_fase1.md §6)
==============================================================
2026-09-02 02:18:54 UTC
desafio.py: OK
treinar.py: OK
verificar.py: OK
checagem_torchsave.py: OK
checagem_retreino.py: OK
desafio_b0f90ffe.npy: OK
desafio_d037aef4.npy: OK
desafio_8b457d0a.npy: OK
receita_b0f90ffe.pt: OK
receita_d037aef4.pt: OK
receita_8b457d0a.pt: OK
receita_extra_60db_b0f90ffe.pt: OK
reconstrucao_b0f90ffe.npy: OK
reconstrucao_d037aef4.npy: OK
reconstrucao_8b457d0a.npy: OK
AUDITORIA 1: OK — todos os 15 hashes conferem
```

## 2. Auditoria 2 — verificação FRESCA em processo novo (dir scratch)

Executada em `/home/z/my-project/scratch_verify` (criado para isto), com cópias de
`verificar.py`, receitas e desafios (`cp` — artefatos originais intocados). Comando núcleo
por seed (embrulhado em `{ date -u; time ...; date -u; } 2>&1 | tee logs/raw/etapa5_verif_<tag>.txt`):

```
time python3 -u verificar.py receita_<tag>.pt desafio_<tag>.npy
```

### Seed 001 (saída integral; `logs/raw/etapa5_verif_b0f90ffe.txt`)

```
---- verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy ----
2026-09-02 02:18:54 UTC
== verificar.py — PoUW Fase 1 (verificação independente em CPU) ==
Receita: receita_b0f90ffe.pt
SHA-256 da receita (recalculado aqui; conferir com o reportado no treino): 6b64493713accd20f9ef130d51db6244e386fa58ade66bd2156755ca3f033b81
Desafio de referência: desafio_b0f90ffe.npy
Threads de CPU (fixado em 1 por determinismo): 1
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.098 s

Arquitetura lida da receita: 2 -> [128, 128, 128] -> 1, omega_0=30.0
Total de parâmetros do modelo: 33537

-- Fases medidas (perf_counter) --
A) Carga da receita (torch.load + montagem da rede): 0.003618 s
B) Forward pass / ejeção (4096 pontos): 0.011890 s
C) Salvamento da reconstrução + SHA-256: 0.000358 s
D) PSNR contra o desafio original: 0.000388 s

TEMPO TOTAL DE VERIFICAÇÃO (carga -> hash -> PSNR, sem imports): 0.016257 s
Tempo total do processo (incl. import do PyTorch): 1.115166 s

Reconstrução salva em: reconstrucao_b0f90ffe.npy
SHA-256 da reconstrução: b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38
PSNR (reconstrução vs desafio): 49.6253 dB
RMSE: 2.284110e-02 | erro máximo absoluto: 1.002134e-01 | pico (max-min): 6.918026
[meta da receita] épocas: 100 | PSNR de treino: 49.62530573074805 | parada: alvo_psnr

real	0m1.632s
user	0m1.583s
sys 0m0.113s
2026-09-02 02:18:55 UTC
```

### Seed 002 (saída integral; `logs/raw/etapa5_verif_d037aef4.txt`)

```
---- verificar.py receita_d037aef4.pt desafio_d037aef4.npy ----
2026-09-02 02:18:55 UTC
== verificar.py — PoUW Fase 1 (verificação independente em CPU) ==
Receita: receita_d037aef4.pt
SHA-256 da receita (recalculado aqui; conferir com o reportado no treino): 29682d84d8844841ef54fd86c6de19284fb019aa92e8d219c6509d09e4c4c44e
Desafio de referência: desafio_d037aef4.npy
Threads de CPU (fixado em 1 por determinismo): 1
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.110 s

Arquitetura lida da receita: 2 -> [128, 128, 128] -> 1, omega_0=30.0
Total de parâmetros do modelo: 33537

-- Fases medidas (perf_counter) --
A) Carga da receita (torch.load + montagem da rede): 0.003648 s
B) Forward pass / ejeção (4096 pontos): 0.010685 s
C) Salvamento da reconstrução + SHA-256: 0.000357 s
D) PSNR contra o desafio original: 0.000386 s

TEMPO TOTAL DE VERIFICAÇÃO (carga -> hash -> PSNR, sem imports): 0.015078 s
Tempo total do processo (incl. import do PyTorch): 1.125242 s

Reconstrução salva em: reconstrucao_d037aef4.npy
SHA-256 da reconstrução: d1bc83b90115562dedafa38a16d5949274e36fb0af4abab092b9e75b6dc6676f
PSNR (reconstrução vs desafio): 48.3896 dB
RMSE: 2.572376e-02 | erro máximo absoluto: 1.168166e-01 | pico (max-min): 6.757977
[meta da receita] épocas: 100 | PSNR de treino: 48.38964354132196 | parada: alvo_psnr

real	0m1.641s
user	0m1.583s
sys 0m0.117s
2026-09-02 02:18:57 UTC
```

### Seed 003 (saída integral; `logs/raw/etapa5_verif_8b457d0a.txt`)

```
---- verificar.py receita_8b457d0a.pt desafio_8b457d0a.npy ----
2026-09-02 02:18:57 UTC
== verificar.py — PoUW Fase 1 (verificação independente em CPU) ==
Receita: receita_8b457d0a.pt
SHA-256 da receita (recalculado aqui; conferir com o reportado no treino): 98c123fd0219d3b58c6661263550d6d270c3e0958c6a2d4206634fb119a7ebea
Desafio de referência: desafio_8b457d0a.npy
Threads de CPU (fixado em 1 por determinismo): 1
Python 3.12.14 | PyTorch 2.14.0+cpu | NumPy 2.1.3
Import do PyTorch levou: 1.093 s

Arquitetura lida da receita: 2 -> [128, 128, 128] -> 1, omega_0=30.0
Total de parâmetros do modelo: 33537

-- Fases medidas (perf_counter) --
A) Carga da receita (torch.load + montagem da rede): 0.003755 s
B) Forward pass / ejeção (4096 pontos): 0.010712 s
C) Salvamento da reconstrução + SHA-256: 0.000351 s
D) PSNR contra o desafio original: 0.000371 s

TEMPO TOTAL DE VERIFICAÇÃO (carga -> hash -> PSNR, sem imports): 0.015192 s
Tempo total do processo (incl. import do PyTorch): 1.108967 s

Reconstrução salva em: reconstrucao_8b457d0a.npy
SHA-256 da reconstrução: ce66e7427a51fa89e803fb8959262d74d0f86c5d91d611475280ef0efa279385
PSNR (reconstrução vs desafio): 49.2587 dB
RMSE: 2.156159e-02 | erro máximo absoluto: 1.040967e-01 | pico (max-min): 6.260589
[meta da receita] épocas: 100 | PSNR de treino: 49.2586868752562 | parada: alvo_psnr

real	0m1.600s
user 0m1.583s
sys 0m0.100s
2026-09-02 02:18:59 UTC
```

### Hashes das reconstruções regeradas no scratch (comando + saída)

```
$ sha256sum reconstrucao_b0f90ffe.npy reconstrucao_d037aef4.npy reconstrucao_8b457d0a.npy
b2fe66eb1eb7f1744c5583b6bcc7486afeb2329156970ed28df3459c96202f38  reconstrucao_b0f90ffe.npy
d1bc83b90115562dedafa38a16d5949274e36fb0af4abab092b9e75b6dc6676f  reconstrucao_d037aef4.npy
ce66e7427a51fa89e803fb8959262d74d0f86c5d91d611475280ef0efa279385  reconstrucao_8b457d0a.npy
```

### Comparação: execução original (Fase 1) vs re-execução de hoje

| Seed | PSNR oficial (dB) | PSNR hoje (dB) | Verificação oficial (s) | Verificação hoje (s) | Hash da reconstrução |
|---|---|---|---|---|---|
| teste-seed-001 | 49.6253 | 49.6253 | 0.013060 | 0.016257 | idêntico, bit-a-bit |
| teste-seed-002 | 48.3896 | 48.3896 | 0.015376 | 0.015078 | idêntico, bit-a-bit |
| teste-seed-003 | 49.2587 | 49.2587 | 0.014319 | 0.015192 | idêntico, bit-a-bit |

Os tempos de HOJE não substituem os oficiais (a tabela oficial da Fase 1 permanece a da
execução original); servem como evidência de que os artefatos publicados continuam funcionais
e determinísticos na data da publicação.

## 3. Artefato de exibição "[m" (limitação nº 10 do relatório, agora explicada e provada)

No terminal da sessão, a linha `[meta da receita] ...` aparece como `eta da receita] ...`.
Isso é artefato da camada de EXIBIÇÃO desta sessão, que engole a sequência de 2 bytes `[m`
(como se fosse um código de escape ANSI); NÃO é o conteúdo do arquivo. Prova à prova de
exibição (hexadecimal não pode ser comido):

```
$ python3 -c "line=open('logs/raw/etapa5_verif_b0f90ffe.txt').readlines()[25]; b=line.encode(); print('primeiros 48 bytes da linha 26 (hex):', b[:48].hex()); print('comeca com 5b6d65746120 = colchete+m+e+t+a+espaco ([meta )?', b.hex().startswith('5b6d657461'))"
primeiros 48 bytes da linha 26 (hex): 5b6d65746120646120726563656974615d20c3a9706f6361733a20313030207c2050534e5220646520747265696e6f3a
comeca com 5b6d65746120 = colchete+m+e+t+a+espaco ([meta )? True
```

`5b 6d 65 74 61 20 64 61 20 72 65 63 65 69 74 61 5d 20 c3a9 ...` = `[meta da receita] é...`
O arquivo em disco está íntegro. (As linhas coladas no § 2 deste log foram transcritas com o
texto correto dos bytes, não com o artefato de exibição.)

## 4. Teste da chave de acesso (GET /user) — a chave em si nunca é impressa

A chave pessoal foi gravada em `/home/z/my-project/.github_token` (chmod 600, FORA do
repositório) e usada apenas via substituição de shell (`$(cat ...)`). Comando e saída:

```
$ TOKEN=$(cat /home/z/my-project/.github_token)
$ curl -s -m 20 -D <headers> -H "Authorization: Bearer $TOKEN" https://api.github.com/user -o <json>
x-oauth-scopes: admin:enterprise, admin:gpg_key, admin:org, admin:org_hook, admin:public_key, admin:repo_hook, admin:ssh_signing_key, audit_log, codespace, copilot, delete:packages, delete_repo, gist, notifications, project, repo, user, workflow, write:discussion, write:network_configurations, write:packages
login: Kronos1027
id: 84149831
name: ONATSKYO
message: (nenhum)
```

## 5. Criação do repositório e push

Script integral: `/home/z/my-project/scripts/publicar_github.sh` (fora do repo). Medidas de
segurança aplicadas: (a) chave lida do arquivo externo, nunca embutida em texto; (b) URL
remota contém apenas o usuário (`https://Kronos1027@github.com/...`), sem chave; (c) push via
`GIT_ASKPASS` apontando para um script que lê o arquivo externo; (d) auditoria automática de
vazamento ANTES do commit (grep no diretório) e DEPOIS (git grep no HEAD). Saída original:

```
== 0) auditoria de vazamento ANTES do commit ==
OK: a chave não aparece em nenhum arquivo do diretório do repositório

== 1) criar o repositório (POST /user/repos; privado=false) ==
HTTP 201
full_name     : Kronos1027/pouw-siren
html_url      : https://github.com/Kronos1027/pouw-siren
default_branch: main
private       : False

== 2) git init + commit (identidade: noreply do GitHub) ==
Initialized empty Git repository in /home/z/my-project/download/pouw_fase1/.git/
 create mode 100644 treinar.py
 create mode 100644 verificar.py
COMMIT: 6e602701076ccbdc414d9ceda9d60bbad4a4bf05

== 3) push (chave via GIT_ASKPASS; nada de token em URL/config/disco do repo) ==
To https://github.com/Kronos1027/pouw-siren.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.

== 4) conferência remota ==
-- git ls-remote (repo público, anônimo) --
6e602701076ccbdc414d9ceda9d60bbad4a4bf05	HEAD
6e602701076ccbdc414d9ceda9d60bbad4a4bf05	refs/heads/main
-- API: GET /repos/Kronos1027/pouw-siren --
full_name: Kronos1027/pouw-siren
html_url : https://github.com/Kronos1027/pouw-siren
size(KB) : 0
branch   : main
pushed_at: 2026-09-02T02:22:28Z

== 5) tópicos do repositório ==
topics: ['cpu', 'inr', 'neural-compression', 'pow', 'proof-of-useful-work', 'pytorch', 'reproducibility', 'siren']

== 6) auditoria de vazamento no CONTEÚDO VERSIONADO (git grep no HEAD) ==
OK: a chave não aparece em nenhum arquivo rastreado pelo commit

PUBLICAÇÃO CONCLUÍDA: https://github.com/Kronos1027/pouw-siren
```

## 6. Conteúdo real do repo remoto (API /contents, logo após o push)

```
23 entradas na raiz:
 - .gitattributes (187 B, file)
 - .gitignore (44 B, file)
 - README.md (8549 B, file)
 - checagem_retreino.py (1782 B, file)
 - checagem_torchsave.py (1361 B, file)
 - checar_integridade.sh (908 B, file)
 - desafio.py (817 B, file)
 - desafio_8b457d0a.npy (32896 B, file)
 - desafio_b0f90ffe.npy (32896 B, file)
 - desafio_d037aef4.npy (32896 B, file)
 - hashes.sha256 (1553 B, file)
 - logs (0 B, dir)
 - receita_8b457d0a.pt (138379 B, file)
 - receita_b0f90ffe.pt (138379 B, file)
 - receita_d037aef4.pt (138379 B, file)
 - receita_extra_60db_b0f90ffe.pt (138661 B, file)
 - reconstrucao_8b457d0a.npy (16512 B, file)
 - reconstrucao_b0f90ffe.npy (16512 B, file)
 - reconstrucao_d037aef4.npy (16512 B, file)
 - relatorio_fase1.md (18229 B, file)
 - requirements.txt (214 B, file)
 - treinar.py (9821 B, file)
 - verificar.py (7457 B, file)
```

Todos os tamanhos batem com os arquivos locais (`ls -la` e `stat` — § 7 do relatório).

## 7. Commit 1 — inventário

`git show --stat --oneline HEAD` (comando executado com `head -45`; total rastreado
`git ls-files | wc -l` = 57; lista integral salva em `logs/raw/etapa5_git_ls_files.txt`):

```
6e60270 Fase 1 - PoUW com SIREN em CPU: desafios deterministicos, treinos, receitas, verificacao independente, relatorio e logs brutos (protocolo anti-fabricacao)
 .gitattributes                                     |   6 +
 .gitignore                                         |   4 +
 README.md                                          | 151 ++++++++++
 checagem_retreino.py                               |  50 ++++
 checagem_torchsave.py                              |  44 ++++
 checar_integridade.sh                              |  22 ++
 desafio.py                                         |  20 ++
 desafio_8b457d0a.npy                               | Bin 0 -> 32896 bytes
 desafio_b0f90ffe.npy                               | Bin 0 -> 32896 bytes
 desafio_d037aef4.npy                               | Bin 0 -> 32896 bytes
 hashes.sha256                                      |  18 +
 logs/etapa1.md                                     | 156 ++++++++++
 logs/etapa2.md                                     | 313 +++++++++++++++++++++
 logs/etapa3.md                                     | 216 ++++++++++
 logs/raw/df.txt                                    |   2 +
 logs/raw/etapa1_desafio_seed001.txt                |  10 +
 .../etapa1_desafio_seed001_tentativa1_FALHA.txt    |  19 ++
 .../etapa1_desafio_seed001_tentativa2_FALHA.txt    |  14 ++
 logs/raw/etapa1_desafio_seed002.txt                |  10 +
 logs/raw/etapa1_desafio_seed002_tentativa2_FALHA.txt |  14 ++
 logs/raw/etapa1_desafio_seed003.txt                |  10 +
 logs/raw/etapa1_desafio_seed003_tentativa2_FALHA.txt |  14 ++
 logs/raw/etapa1_determinismo_e_hashes.txt          |  16 ++
 logs/raw/etapa2_checagem_retreino.txt              |  17 ++
 logs/raw/etapa2_checagem_torchsave.txt             |   6 +
 logs/raw/etapa2_extra_alvo60db.txt                 |  33 +
 logs/raw/etapa2_hashes_receitas.txt                |  13 +
 logs/raw/etapa2_retreino_determinismo.txt          |  29 ++
 logs/raw/etapa2_smoke_test.txt                     |  28 ++
 logs/raw/etapa2_treino_seed001.txt                 |  28 ++
 logs/raw/etapa2_treino_seed002.txt                 |  28 ++
 logs/raw/etapa2_treino_seed003.txt                 |  28 ++
 logs/raw/etapa3_determinismo_verificacao.txt       |  38 +
 logs/raw/etapa3_verif_seed001.txt                  |  31 +
 logs/raw/etapa3_verif_seed002.txt                  |  31 +
 logs/raw/etapa3_verif_seed003.txt                  |  31 +
 logs/raw/etapa5_hash_check.txt                     |  15 +
 logs/raw/etapa5_verif_8b457d0a.txt                 |  31 ++
 logs/raw/etapa5_verif_b0f90ffe.txt                 |  31 ++
 logs/raw/etapa5_verif_d037aef4.txt                 |  31 ++
 logs/raw/free.txt                                  |   3 +
 logs/raw/inventario_final_e_razoes.txt             |  21 +
 logs/raw/lscpu.txt                                 |  36 +
 logs/raw/pip_install_torch.txt                     |  15 +
 (+ relatorio_fase1.md, requirements.txt, tamanhos_finais.txt, treinar.py,
    verificar.py, versoes.txt — lista completa em logs/raw/etapa5_git_ls_files.txt)
```

## 8. SHA-256 dos arquivos criados nesta etapa (medição de hoje, mesma máquina)

```
$ sha256sum README.md requirements.txt .gitignore .gitattributes checar_integridade.sh hashes.sha256 relatorio_fase1.md logs/raw/etapa5_hash_check.txt logs/raw/etapa5_verif_b0f90ffe.txt logs/raw/etapa5_verif_d037aef4.txt logs/raw/etapa5_verif_8b457d0a.txt
4e07f666370fc212c8c5f3af5d8f8778483cfcbd7135c13d24dacbcabdcfdc05  README.md
4525d28cb80a6fc2575b7750f2e828f27bc8ac6cb7f28419aa19e000d56c497d  requirements.txt
900f63de880d9af8908aaf809d55f9b1082874d86e6f8ba2e69ed19cfcbc5f9c  .gitignore
93c3359956cfa7bf0256aa72744ec6fefdab89da4a88386aa2e7aae1a4808fc0  .gitattributes
80e559f921d6c41c1753c46b0616ec1ce40d4811119796d7b4ac637262976697  checar_integridade.sh
bc1437d48771ae4ce45e14785a69e52fb0677eaf2f35e2d5f3daec1964af1647  hashes.sha256
1e95ca9bbc8cec912a20329963e9fd9c7b51d6bd31b108eed8f054e117ef3f0d  relatorio_fase1.md
6b928e6a64634179c5266f48fa11556f0d74a225d97220f132fa38966253a48c  logs/raw/etapa5_hash_check.txt
0fc57614182f9488f64881292e0d6597cdf261e7379605b4575a940c8e1a9f30  logs/raw/etapa5_verif_b0f90ffe.txt
8a373a281af83ac3ee740309955b7aeeb8bfbf679e556e0d03ba643a1f7903f3  logs/raw/etapa5_verif_d037aef4.txt
ddfc95e5b45ce63febb180f9b1b01bedbc4afe00fee1818f48e029bff748c0a1  logs/raw/etapa5_verif_8b457d0a.txt
```

Nota: `relatorio_fase1.md` não foi alterado nesta etapa (hash medido agora pela primeira vez,
para âncora adicional); os 15 artefatos da pesquisa permanecem âncorados em `hashes.sha256`.

## 9. Commit 2 (este log) e estado final

- **Commit 1:** `6e602701076ccbdc414d9ceda9d60bbad4a4bf05` — todo o conteúdo de pesquisa +
  arquivos de publicação até este ponto.
- **Commit 2:** adiciona ESTE arquivo (`logs/etapa5_publicacao.md`), o snapshot de
  `git ls-files` e o hash do zip público (ver worklog). O hash do commit 2 é reportado no
  `worklog.md` da sessão e na conversa (um arquivo não pode conter o hash do commit que o
  carrega — auto-referência impossível).
- **Repositório público:** https://github.com/Kronos1027/pouw-siren
- **Clone:** `git clone https://github.com/Kronos1027/pouw-siren.git`
- **Conferência independente sugerida ao leitor:**
  `bash checar_integridade.sh` (15× OK) e
  `python3 -u verificar.py receita_b0f90ffe.pt desafio_b0f90ffe.npy`
  (PSNR 49.6253 dB; hash da reconstrução `b2fe66eb…c96202f38` na mesma máquina/ambiente).
