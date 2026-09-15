# Etapa 15 — Correção de portabilidade v1.0.1 do `verificar_int.py` (datetime/platform → math)

**Data:** 2026-09-15/16 (UTC) · **Execução:** agente (Linux/Xeon local), sob protocolo
anti-fabricação (nenhum número sem execução; outputs brutos preservados; SHA-256 de
todo artefato; tempos medidos; erros reportados completos).

## 15.0 Contexto — a descoberta veio de FORA

Na validação externa Windows da `pouw-int-v1` (Fase 6, em andamento), o dono do repo
rodou o verificador frio no **Python 3.11.15** (Windows) e a auditoria zero-float
**falhou imediatamente**:

```text
-- AUDITORIA ZERO-FLOAT (runtime) --
FALHOU: módulos de float carregados no processo: ['math']
```

No **Python 3.12.13** (uv) o mesmo comando passou — a validação dos 8 blocos
concluiu 8/8 VÁLIDOS, 0/32.768 bins divergentes (registrada na Fase 6). A discrepância
entre 3.11 e 3.12 isolou o suspeito: `import datetime`.

## 15.1 Causa raiz nº 1 — `datetime` importa `math` em Python ≤ 3.11

Sonda por versão (processo novo por versão; comando:
`import sys, datetime; print("math" in sys.modules)`):

| Python | `math` em `sys.modules` após `import datetime` |
|--------|:---:|
| 3.10.21 | **True** |
| 3.11.16 | **True** |
| 3.12.14 | False |
| 3.13.5 | False |

Mecanismo: em Python ≤ 3.11, `Lib/datetime.py` executa `import math as _math`
(linha 12 do módulo puro) **antes** de tentar o acelerador C `_datetime` — ou seja,
até máquinas com o `_datetime` compilado carregam `math` no processo. Em 3.12+ a
ordem/inicialização mudou e `math` não é mais puxado. (O arquivo `datetime.py`
executa em todas as versões; a diferença medida está na tabela acima.)

Log bruto: `fase5/logs/raw/f5_e6_correcao_311_antes.txt` (inclui a reprodução
local pré-correção no 3.11.16: auditoria FALHA `['math']`, código de saída 1 —
idêntica à falha do Windows 3.11.15 do dono).

## 15.2 Correção nº 1 — `time` em vez de `datetime`

`agora_utc()` (a ÚNICA função que usava datetime) passou a ser:

```python
def agora_utc():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
```

O módulo `time` **não carrega `math` em nenhuma versão do Python** (comprovado na
matriz §15.4). Formato de saída **idêntico** ao anterior (`YYYY-MM-DD HH:MM:SS UTC`).
Compromissos não são afetados (timestamp não entra no hash — o hash cobre só o
payload quantizado + header da spec).

## 15.3 Causa raiz nº 2 — `platform` importa `math` em Python 3.10 (via selectors)

A **primeira** matriz pós-correção (preservada em
`f5_e6_correcao_pos_EXECUCAO1_PLATAFORMA_310.txt`) revelou um SEGUNDO infiltrado:
no Python 3.10.21 a auditoria ainda falhava com `['math']` mesmo sem datetime.

Bisect por módulo (processo novo por sonda, Python 3.10.21):

| `import` … | `math` em `sys.modules`? |
|------------|:---:|
| argparse | False |
| ast | False |
| hashlib | False |
| os | False |
| **platform** | **True** |
| sys | False |
| time | False |
| conjunto sem platform | False |

Cadeia completa medida: `platform` → `subprocess` → `selectors` → **`import math`**
(o `selectors.py` do 3.10 usa `math.ceil` para arredondar timeouts; o uso foi
removido no 3.11 — por isso 3.11.16 passou com a correção nº 1 apenas).

## 15.4 Correção nº 2 — `sys.version` em vez de `platform.python_version()`

Único uso de `platform` no verificador era a linha de banner. Substituído por
`sys.version.split()[0]` — **saída idêntica** (ex.: `3.10.21`) sem importar nada
além de `sys`. Após as duas correções, o conjunto de imports do processo é:
`argparse, ast, hashlib, os, sys, time` (+ `siren_int`, que importa `ast, hashlib,
sys`) — medido limpo de `math` em 3.9/3.10/3.11/3.12/3.13.

## 15.5 Matriz final pós-correção (v1.0.1) — bloco 1, âncoras completas

Comando por versão (ver §15.9): verificação completa do bloco 1 com
`--comp-esperado` (compromisso publicado 162d852c…) e `--quantizada`
(payload v1 publicado). Log bruto: `f5_e6_correcao_pos.txt`.

| Python | Auditoria zero-float | C1 (compromisso vs publicado) | C3 (payload v1) | TOTAL carga→gate | Código |
|--------|----------------------|-------------------------------|-----------------|------------------|:---:|
| 3.9.25 | OK | CONFERE | 0/4096 | 26.000926 s | 0 |
| 3.10.21 | OK | CONFERE | 0/4096 | 28.000632 s | 0 |
| 3.11.16 | OK | CONFERE | 0/4096 | 29.000636 s | 0 |
| 3.12.14 | OK | CONFERE | 0/4096 | 26.000098 s | 0 |
| 3.13.5 | OK | CONFERE | 0/4096 | 22.000620 s | 0 |

**5/5 VÁLIDOS; o compromisso recomputado é bit-a-bit o MESMO
(`162d852c6b603f0cd94568891cff9512a8a5f78f1c1f185279e69912ed2933be`) em todas as
versões — a correção não tocou em UM bit do caminho computacional.** Os tempos
variam por versão (22–29 s; o 3.13 é o mais rápido nesta máquina) — tempos nunca
entraram em compromisso.

## 15.6 Impacto declarado do que mudou

- **Caminho computacional (forward/quantização/gate/hash): ZERO mudança** — provado
  por C1 CONFERE contra o compromisso PRÉ-correção em 5 versões (§15.5).
- **Saída de log:** apenas 2 linhas cosméticas mudaram — o banner agora imprime a
  versão via `sys.version.split()[0]` (mesmo texto) e a linha "Imports do processo"
  lista o conjunto novo (sem datetime/platform). Timestamps continuam no mesmo
  formato.
- **Superfície de imports:** `datetime` e `platform` removidos; `platform` era
  stdlib "inofensivo" até a auditoria provar o contrário no 3.10 — a auditoria
  zero-float pegou sua **terceira infiltração real** (pathlib na F5; datetime e
  platform nesta etapa).

## 15.7 Execuções com defeito (preservadas, protocolo item 5)

1. `f5_e6_correcao_311_antes_EXECUCAO1_SONDA_SYNTAXERROR.txt` — 1ª coleta das
   sondas abortou: probe em f-string com barra invertida (`SyntaxError: f-string
   expression part cannot include a backslash` no 3.10/3.11; quoting quebrado no
   3.12/3.13). Regenerada com probe sem f-string. A captura da falha da auditoria
   foi idêntica nas duas coletas.
2. `f5_e6_correcao_pos_EXECUCAO1_PLATAFORMA_310.txt` — 1ª matriz pós-correção
   (apenas correção nº 1): 3.10.21 AINDA falhava com `['math']` → levou ao bisect
   §15.3 e à correção nº 2. 3.11.16/3.12.14/3.13.5 já passavam nela.

## 15.8 Âncoras e arquivos

- `fase5/verificar_int.py` — ALTERADO (SHA-256 novo em `hashes_fase5.sha256`).
- `fase5/relatorio_fase5.md` — errata §15 adicionada (SHA-256 novo).
- NOVOS: este log (`etapa15_correcao_portabilidade.md`) + 4 raw (2 oficiais +
  2 `_EXECUCAO1_`).
- `hashes_fase5.sha256`: **40 → 45 âncoras**.
- NOVO `fase6/hashes_fase6.sha256` (2 âncoras: roteiro da validação externa +
  `checar_integridade.py`) → repo total **127**; `checar_integridade.sh`
  atualizado (stanza Fase 6 + contagens).

## 15.9 Comandos na ordem executada

```bash
# (ambiente: clone fresco github.com/Kronos1027/pouw-siren @ 417eeae;
#  bash checar_integridade.sh -> 120x OK antes de qualquer edição)
uv python install 3.10 3.11 3.9            # interpretadores para a matriz
bash /home/z/my-project/scripts/gerar_evidencia_correcao.sh antes
#   -> f5_e6_correcao_311_antes_EXECUCAO1_SONDA_SYNTAXERROR.txt (probe com erro)
#   -> renomeado p/ preservar; probe corrigido no script; re-executado:
#   -> f5_e6_correcao_311_antes.txt (sondas 3.10/3.11/3.12/3.13 + falha 3.11.16)
# [edicoes v1.0.1 parte 1: remover datetime; agora_utc() via time]
bash /home/z/my-project/scripts/gerar_evidencia_correcao.sh depois
#   -> f5_e6_correcao_pos_EXECUCAO1_PLATAFORMA_310.txt (3.10 ainda falha!)
# [bisect: platform -> True no 3.10; cadeia platform->subprocess->selectors->math]
# [edicoes v1.0.1 parte 2: remover platform; banner via sys.version.split()[0]]
bash /home/z/my-project/scripts/gerar_evidencia_correcao.sh depois
#   -> f5_e6_correcao_pos.txt (MATRIZ FINAL 3.9/3.10/3.11/3.12/3.13: 5/5 validos)
bash /home/z/my-project/scripts/gerar_ancoras_fase5_v2.sh   # 45 ancoras
python3 checar_integridade.py                                # 127/127 OK
```
