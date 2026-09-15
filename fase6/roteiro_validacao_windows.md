# Fase 6 — Roteiro de validação externa Windows do caminho inteiro (`pouw-int-v1`)

**Pré-registro:** este roteiro foi publicado no repositório **ANTES** das execuções
que ele prescreve (commit da correção v1.0.1 + abertura da Fase 6). Todas as
predições abaixo (compromissos, margens, bins, vereditos) vêm de medições já
registradas nos logs da Fase 5 e da 1ª rodada Windows (Python 3.12.13) — **nenhum
valor deste roteiro é estimativa não medida**. Tempos de execução NÃO são critério
(dependem da máquina) e não têm valor previsto.

**Executor:** o dono do repo, na máquina Windows dele (validador EXTERNO ao ambiente
de mineração/Linux, como na Fase 4). **Agente:** registra, confere e publica os
resultados em `fase6/` quando o executor reportar as saídas.

---

## 0. Por que esta rodada existe (contexto da correção v1.0.1)

A 1ª rodada Windows (Python 3.12.13, uv) validou a cadeia inteira: **8/8 blocos
VÁLIDOS, 0/32.768 bins divergentes**. No **Python 3.11.15** (o do sistema), porém,
a auditoria zero-float do verificador falhava: `import datetime` puxa `math` em
Python ≤ 3.11. A correção **v1.0.1** (`fase5/logs/etapa15_correcao_portabilidade.md`)
removeu `datetime` (e também `platform`, que puxa `math` no 3.10 via
subprocess→selectors) e provou, em matriz local Linux 3.9/3.10/3.11/3.12/3.13,
que o compromisso recomputado é **bit-a-bit o mesmo** em todas as versões.
Esta rodada valida o mesmo **no Windows**, no Python que antes falhava.

## 1. Ambiente — registrar ANTES de tudo

Cole no relatório final: versão do Windows, `python --version` (esperado 3.11.15),
o caminho/versão do Python uv (esperado 3.12.13), `python -c "import torch, numpy;
print(torch.__version__, numpy.__version__)"` (para o Item 3), e o `git log -n 1
--oneline` após o pull. Tudo o que segue roda **a partir da raiz do clone**:

```powershell
cd E:\pesquisa_importante\pesquisadepoof\pouw-siren
```

**Em TODOS os itens**: definir primeiro `$env:PYTHONIOENCODING = "utf-8"` (a saída
dos scripts usa UTF-8; sem isso o console cp1252 pode quebrar em `→`/`δ`).

## 2. Item 0 — sincronização e integridade (≈ 1 min)

```powershell
git status                # esperado: working tree clean
git pull origin main      # traz a correção v1.0.1 + este roteiro
git log -n 2 --oneline    # REGISTRAR o novo HEAD
python checar_integridade.py
```

**Esperado (predição):** `[Fase 1] 15/15`, `[Fase 2] 23/23`, `[Fase 3] 37/37`,
`[Fase 4] 5/5`, `[Fase 5] 45/45`, `[Fase 6] 2/2`, **`TOTAL: 127/127 ancoras OK`**,
`RESULTADO: INTEGRO (codigo 0)`. (Alternativa: `bash checar_integridade.sh` no Git
Bash. Se MUITOS arquivos divergirem: `git config core.autocrlf false` +
`git checkout-index --force --all` e re rodar — causa CRLF, já documentada na F4.)

## 3. Item 1 — os 8 blocos no Python 3.11.15, âncoras completas (≈ 3 min)

**Esta é a validação da correção**: o Python que antes falhava na auditoria deve
agora verificar a cadeia inteira com compromissos bit-a-bit idênticos aos
publicados. Cole a tabela `$comp` exatamente como está (compromissos oficiais do
repo, seção DEMONSTRAÇÃO de `fase5/logs/raw/f5_e3_equivalencia.txt`):

```powershell
$env:PYTHONIOENCODING = "utf-8"
python --version    # confirmar: 3.11.15

$comp = @{
  "01" = "162d852c6b603f0cd94568891cff9512a8a5f78f1c1f185279e69912ed2933be"
  "02" = "9366457358ebfdcb9809665c8967b3936bbe5e7c190a6154510518dcbbd74569"
  "03" = "32e7e3efb99e48a8f469433aeda4c1f4ca97ec5921cf27b91d8b832c1b779582"
  "04" = "3d34616b5ce20c032ac1eddbf057b93ad8c24998b33cbf469c5daf2f07dab3e1"
  "05" = "5573254afe060d85f5a56f221fb100869eb686da1389785412a4582ac13613f5"
  "06" = "cad3861e224de406a3f70b43ea6ba0306687d4de6edca13095e2241f4e7f5bc2"
  "07" = "5123013656af90be0ff8c0be986354c15cef757d107482bff854b785b1be3855"
  "08" = "f83468725ccbed6e62d0d3933ce1e367c4f2c9a08a248753e91505d8b90986eb"
}

foreach ($k in ($comp.Keys | Sort-Object)) {
  Write-Host "================== BLOCO $k =================="
  python -u fase5\verificar_int.py "fase5\pesos_int\pesos_int_cadeia_$k.bin" "fase3\cadeia_demo\desafio_$k.npy" --comp-esperado $comp[$k] --quantizada "fase3\cadeia_demo\quantizada_${k}_u16.npy"
  Write-Host "codigo de saida: $LASTEXITCODE"
}
```

**Esperado por bloco (predição; margens são razões inteiras exatas —
idênticas em qualquer máquina):**

| Bloco | Auditoria | C1 | C2 margem | C3 bins | Resultado |
|-------|-----------|----|-----------|---------|-----------|
| 01 | OK | CONFERE | ≈ 6,12× | 0/4096 | VÁLIDO (0) |
| 02 | OK | CONFERE | ≈ 6,99× | 0/4096 | VÁLIDO (0) |
| 03 | OK | CONFERE | ≈ 7,36× | 0/4096 | VÁLIDO (0) |
| 04 | OK | CONFERE | ≈ 6,93× | 0/4096 | VÁLIDO (0) |
| 05 | OK | CONFERE | ≈ 7,68× | 0/4096 | VÁLIDO (0) |
| 06 | OK | CONFERE | ≈ 10,42× | 0/4096 | VÁLIDO (0) |
| 07 | OK | CONFERE | ≈ 5,08× | 0/4096 | VÁLIDO (0) |
| 08 | OK | CONFERE | ≈ 2,96× | 0/4096 | VÁLIDO (0) |

(Forward ≈ 15–17 s por bloco nesta máquina, pela 1ª rodada — não é critério.)
**Mantenha a sessão aberta** — os itens seguintes reutilizam a tabela `$comp`.

## 4. Item 2 — suíte adversarial E4 no 3.11.15 (≈ 4–5 min)

13 forwards inteiros (sweep + 6 fraudes em subprocessos frios que HERDAM o
Python 3.11.15 — ou seja, a auditoria zero-float roda em cada subprocesso na
versão que antes falhava):

```powershell
$env:PYTHONIOENCODING = "utf-8"
python -u fase5\teste_negativo_int.py
```

**Esperado (predição, medido no Linux; os valores inteiros são determinísticos):**
- E4a baseline: `comp 162d852c6b603f0c…`;
- sweep: δ=1, 2^10, 2^20, 2^30, 2^33 → **0 bins, hash NÃO mudou, gate APROVADO**;
  δ=2^40 → **2 bins, hash SIM, gate APROVADO** (piso de sensibilidade medido);
- E4b: **N1–N6 todos "COMPORTOU COMO ESPERADO"** (N1 válido; N2–N6 inválidos);
- `RESULTADO: SUÍTE ADVERSARIAL APROVADA (código 0)`.

## 5. Item 3 — equivalência completa E3+E5 + 8 frios no 3.11.15 (≈ 10–15 min)

**Único item que exige torch+numpy** (lado v1 float64/BLAS/libm). É a varredura
das **18 receitas oficiais** + a DEMONSTRAÇÃO com as 8 verificações frias por
subprocesso (âncoras completas: `--sha256-pesos`, `--sha256-desafio`,
`--comp-esperado`, `--quantizada`):

```powershell
$env:PYTHONIOENCODING = "utf-8"
python -c "import torch, numpy; print(torch.__version__, numpy.__version__)"  # registrar
python -u fase5\experimento_equivalencia.py
```

**Esperado (predição):**
- tabela E3: 18 linhas, todas com **bins = 0** e payload `=`;
- `payloads quantizados v1≡v2 bit-a-bit: 18/18` · `gates concordantes: 18/18`;
- `bins divergentes no total: 0 (de 73728)`;
- `max|ΔR|` global ≈ 1e-14 (Linux mediu 1,31e-14; **pode variar nos últimos
  dígitos entre BLAS — NÃO é critério**; o critério é bins = 0);
- DEMONSTRAÇÃO: `[bloco 1..8] código 0` com `C1 … → CONFERE` — **8/8 frios VÁLIDOS**;
- `RESULTADO: EQUIVALÊNCIA CONFIRMADA (código 0)`;
- razão v2/v1: grande (Linux mediu 1569×; valor depende da máquina — não é critério).

## 6. Item 4 — re-confirmação no Python 3.12.13 (≈ 3 min)

A 1ª rodada (pré-correção) já validou 8/8 no 3.12.13. Repita o Item 1 no uv
para provar que a correção **não mudou nada** nesta versão (compromissos
idênticos aos da tabela `$comp` e aos da 1ª rodada):

```powershell
$py = "C:\Users\darlan\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"
$env:PYTHONIOENCODING = "utf-8"
& $py --version    # confirmar: 3.12.13
foreach ($k in ($comp.Keys | Sort-Object)) {
  Write-Host "================== BLOCO $k (3.12.13) =================="
  & $py -u fase5\verificar_int.py "fase5\pesos_int\pesos_int_cadeia_$k.bin" "fase3\cadeia_demo\desafio_$k.npy" --comp-esperado $comp[$k] --quantizada "fase3\cadeia_demo\quantizada_${k}_u16.npy"
  Write-Host "codigo de saida: $LASTEXITCODE"
}
```

**Esperado:** idêntico ao Item 1 (8× VÁLIDO, mesmos compromissos, mesma margem).
→ com isto, a MESMA máquina Windows terá verificado a cadeia bit-a-bit em **duas
versões de Python**, contra os compromissos publicados pelo Linux.

## 7. Item 5 — OPCIONAL: Python 3.10 no Windows (≈ 2 min + download)

Amplia a matriz de compatibilidade (o 3.10 tinha o segundo infiltrado,
`platform`). O uv baixa o interpretador se necessário:

```powershell
uv run --python 3.10 --no-project -- python --version
uv run --python 3.10 --no-project -- python -u fase5\verificar_int.py fase5\pesos_int\pesos_int_cadeia_01.bin fase3\cadeia_demo\desafio_01.npy --comp-esperado $comp["01"] --quantizada fase3\cadeia_demo\quantizada_01_u16.npy
```

**Esperado:** bloco 01 VÁLIDO com `C1 … 162d852c… → CONFERE` (basta 1 bloco —
a matriz Linux já cobriu 3.9–3.13 no bloco 1; aqui é a confirmação Windows/3.10).

## 8. O que reportar de volta (protocolo anti-fabricação)

Para **cada item**: (a) o comando exato como rodou; (b) a saída **integral**
verbatim (não resumida — os logs brutos entram em `fase6/logs/raw/`); (c) os
códigos de saída; (d) versões do ambiente (§1). **Se algo divergir de uma
predição: NÃO corrija, NÃO re-rote — cole a divergência completa** (um erro
verbal é dado; o protocolo das fases anteriores preservou até execuções com
leitura errada — divergências são onde a pesquisa mora).

## 9. Critérios de sucesso da campanha (pré-registrados)

1. Integridade 127/127 após o pull (Item 0);
2. Item 1: 8/8 VÁLIDOS no 3.11.15 com C1 CONFERE contra os compromissos
   publicados (a correção v1.0.1 funciona onde a v1.0.0 falhava);
3. Item 2: 6/6 fraudes rejeitadas + sweep conforme §4 (código 0);
4. Item 3: 18/18 + 8/8 frios + código 0 (equivalência v1×v2 no Windows);
5. Item 4: compromissos idênticos entre 3.11.15 e 3.12.13 na mesma máquina;
6. (Opcional) Item 5: bloco 01 VÁLIDO no 3.10.

Cumpridos 1–5, a Fase 6 fecha a validação externa da `pouw-int-v1` com a
correção de portabilidade, e o roadmap volta para: port C (limitação de custo
nº 1) e cadeia v2 comprometendo com `pouw-int-v1`.
