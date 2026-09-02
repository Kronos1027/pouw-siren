# Fase 4 — E1: validação cross-CPU EXTERNA da cadeia (Windows / dono do repositório)

> **Evento validado:** 2026-09-02 04:41 UTC · **Registrado no repo:** 2026-09-02 (etapa 11)
> **Executor:** o DONO do repositório, na máquina local dele (Windows) — **NÃO o agente autor**.
> Protocolo anti-fabricação, item 7: dados de terceiros citados como tais, nunca misturados com
> medições próprias. **Nenhum número da validação (seções 2–5) foi executado pelo agente**; a
> única execução própria nesta fase é a conferência formal da seção 6 (log bruto anexado).

## 1. O que foi validado

A predição central da Fase 3 (relatório §11, registrada ANTES da execução): **a cadeia oficial de
8 blocos deve verificar 8/8 VÁLIDA em qualquer CPU**, com compromissos `pouw-quant-v1`
(float64 + quantização B=16) idênticos **bit-a-bit** àqueles minerados no ambiente do agente
(Linux, Xeon 2 vCPU). O convite era endereçado ao leitor cuja CPU havia **divergido** no hash
float32 da Fase 1 (7,15e-07) — o dono do repo atendeu ao convite na própria máquina Windows, o
ambiente mais distante possível do de mineração dentro do alcance do projeto: **sistema
operacional, Python, PyTorch e NumPy são TODOS diferentes** (tabela §2).

Resultado relatado: `python -u fase3/verificar_cadeia.py` → **8/8 blocos VÁLIDOS, código 0,
0,505768 s** para a cadeia inteira (sem imports), após checagem de integridade das **75/75
âncoras SHA-256** no clone local dele.

## 2. Ambientes comparados (mineração vs validação)

| | Mineração + verificação oficial (agente) | Validação externa (dono do repo) |
|---|---|---|
| Sistema operacional | Linux (container) | **Windows** (caminho `E:\pesquisa_importante\…`) |
| Python | 3.12.14 | **3.11.15** |
| PyTorch | 2.14.0+cpu | **2.13.0+cpu** |
| NumPy | 2.1.3 | **2.4.3** |
| CPU | Intel Xeon, 2 vCPU (KVM) | não reportada |
| Threads na verificação | 1 (`torch.set_num_threads(1)`) | 1 (mesma linha de código) |
| Papel | gerou a cadeia (F3 E1) | só verificou o publicado |

Diferenças em **negrito**. É a primeira vez na pesquisa que a validação cross-CPU cobre SO,
interpretação e bibliotecas de versões todas distintas — mais forte que qualquer par que o
agente poderia produzir sozinho na mesma infraestrutura.

## 3. Sequência de comandos relatada pelo executor (Windows, na ordem)

```text
git pull origin main || git pull
git fetch origin; git reset --hard origin/main
git log -n 5 --stat
git config core.autocrlf                          (consulta do valor vigente)
git config core.autocrlf false; git checkout-index --force --all
python -c "<checagem das 75 âncoras — equivalente Python do checar_integridade.sh>"
python -u fase3/verificar_cadeia.py
```

Observações do agente sobre essa sequência (fatos, sem inferência além do declarado):
- a checagem de integridade foi feita por um one-liner Python que recalcula o SHA-256 dos
  arquivos listados nas três âncoras (`hashes.sha256`, `fase2/hashes_fase2.sha256`,
  `fase3/hashes_fase3.sha256`) e os compara — função idêntica à do `checar_integridade.sh`,
  que não roda nativamente no Windows (PowerShell). **Resumo relatado: F1 15/15, F2 23/23,
  F3 37/37 → 75/75 OK.** Os outputs brutos dessa checagem não foram transmitidos — só o
  resumo (limitação §8);
- o executor consultou e normalizou `core.autocrlf` (false + `checkout-index --force --all`)
  **antes** da checagem final e do teste decisivo — higiene padrão no Windows para evitar
  corrupção de fim-de-linha em checkout de repositórios com artefatos binários. Lição
  registrada no README ("Verificar você mesmo") para outros leitores Windows: se as âncoras
  falharem após o clone, normalize o autocrlf antes de concluir divergência real.

## 4. Output bruto, VERBATIM

Preservado integralmente (sem nenhuma edição, incluindo travessões, reticências e acentos) em:
**`fase4/logs/raw/f4_e1_saida_windows.txt`** — com cabeçalho de proveniência declarando
executor, comando e canal de transmissão. As linhas centrais:

```text
Python 3.11.15 | PyTorch 2.13.0+cpu | NumPy 2.4.3
[bloco 1] VÁLIDO (0.390166 s) | PSNR 47.8726 dB | comp cd579702b18e133e… | hash_bloco 000058a7496dd7e5…
[bloco 2] VÁLIDO (0.015529 s) | PSNR 48.4494 dB | comp 0fff8405892f2d0f… | hash_bloco 0000272552967f9f…
[bloco 3] VÁLIDO (0.015242 s) | PSNR 48.6712 dB | comp 7cd2df64afce402e… | hash_bloco 00001fd640b0ff3a…
[bloco 4] VÁLIDO (0.015209 s) | PSNR 48.4106 dB | comp f388b1c19f74c7ab… | hash_bloco 0000200bf1aaad7a…
[bloco 5] VÁLIDO (0.017026 s) | PSNR 48.8548 dB | comp 5cd04941ad0e9976… | hash_bloco 0000618054eaeb30…
[bloco 6] VÁLIDO (0.016882 s) | PSNR 50.1790 dB | comp d91f50f3699d5bfa… | hash_bloco 00007efe852b4e76…
[bloco 7] VÁLIDO (0.018017 s) | PSNR 47.0671 dB | comp f0d4ab32fe138b91… | hash_bloco 00005d5d0b6304e3…
[bloco 8] VÁLIDO (0.017179 s) | PSNR 44.7247 dB | comp eece79b0314d8d04… | hash_bloco 00001c19b2ff024c…
RESULTADO: CADEIA VÁLIDA (código 0)
```

O verificador imprime o prefixo de 16 hex do compromisso **recomputado na máquina dele**; a
igualdade COMPLETA (64 hex) é garantida pela checagem C5 dentro do verificador — qualquer
1 bit de divergência tornaria o bloco INVÁLIDO. **8/8 VÁLIDO ⇒ 8 compromissos recomputados
são bit-a-bit idênticos aos minerados em Linux/Xeon.**

## 5. Métricas relatadas pelo executor (medição DELE, não do agente)

| Métrica | Valor (máquina Windows do executor) | Referência do agente (Linux/Xeon) |
|---|---|---|
| Integridade das âncoras | 75/75 OK | 75/75 OK (pré-push F3) |
| Blocos válidos | 8/8 (código 0) | 8/8 (E2, código 0) |
| Verificação da cadeia (sem imports) | 0,505768 s | 0,138637 s (E2) — mesma ordem de grandeza |
| Tempo por bloco (após o 1º) | 15,2–18,0 ms | 8,6–18,4 ms no frio-por-bloco (E2/E3) |
| 1º bloco (aquecimento) | 0,390166 s | 0,124 s (E2) — mesmo padrão de aquecimento |
| Import do PyTorch (à parte) | 9,195 s | ~1,3 s |

A máquina do executor é ~3,6× mais lenta na verificação da cadeia inteira — coerente com
hardware diferente e SEM qualquer efeito sobre o consenso (compromissos idênticos). O import
de 9,195 s na máquina dele reforça a limitação 1 da F1/F3: o custo de import domina a
verificação fria; o nó verificador de produção é o lote persistente (F3 E3).

## 6. Conferência formal contra a cadeia oficial (executada pelo AGENTE)

O output verbatim foi conferido programaticamente contra o `fase3/cadeia_demo/cadeia.json`
por **`fase4/conferir_saida.py`** (script novo desta fase, stdlib pura, reutilizável por
qualquer leitor). Execução própria, log bruto em
**`fase4/logs/raw/f4_e1_conferimento.txt`** (04:51:04 UTC):

```text
    1 | VÁLIDO | 47.8726 | cd579702b18e133e | 000058a7496dd7e5 | CONFERE
    … (8 linhas, todas CONFERE)
RESULTADO DA CONFERÊNCIA: OK — 100% dos blocos conferem (código 0)
```

Para os 8 blocos: status VÁLIDO ✓ · PSNR impresso = `psnr_verificacao` E `psnr_treino`
oficiais a 4 decimais ✓ · prefixo do compromisso = oficial ✓ · prefixo do hash_bloco =
oficial ✓ · sumário e RESULTADO ✓. Escopo declarado: o script confere o **nível impresso**
(prefixos 16 hex + PSNR 4 dec); a igualdade completa dos 64 hex é certificada pela C5 dentro
do verificador do executor (status VÁLIDO), não re-derivada pelo agente.

## 7. Veredito das predições registradas (relatório F3 §11, ANTES da execução)

| Predição (§11) | Resultado | Evidência |
|---|---|---|
| (a) 8 compromissos bit-a-bit (float64 + B=16; resíduo esperado ~1e-15) | **CONFIRMADA** | 8/8 VÁLIDO (C5 compara 64 hex completos); §6: prefixos = oficiais |
| (b) C2 com a libm DO EXECUTOR (np.sin/np.cos, tolerância a ~1 ulp) | **CONFIRMADA** | C2 integra o veredito VÁLIDO de cada bloco; nenhuma falha apontada |
| (c) hash de BYTES dos .npy publicado = conferido exato (C3/C4/C6) | **CONFIRMADA** | VÁLIDO em todos os blocos + 75/75 âncoras relatadas |

**Leitura científica:** a mesma classe de máquina que na Fase 1 produzia hashes float32
divergentes (7,15e-07 → 100% de virada de bin na F2 E2) agora, sob a spec `pouw-quant-v1`,
reproduz compromissos **idênticos bit-a-bit** com SO/Python/PyTorch/NumPy todos diferentes
do ambiente de mineração. A cadeia demo `pouw-cadeia-demo-v1` verifica de forma determinística
fora do ambiente que a gerou — a propriedade de consenso que faltava para fechar a limitação 2
da Fase 1, agora com **validação externa**, não apenas intra-máquina do agente.

## 8. Limitações desta validação

1. **Executor = dono do repo**, não terceiro independente; o valor de prova é a distância de
   ambiente (Windows + stack inteiro diferente), não a independência de interesse.
2. **CPU da máquina do executor não foi reportada** (o verificador não imprime modelo de CPU);
   o dado é o SO/stack, não o microarquitetura.
3. Os **outputs brutos das checagens de integridade** (75/75) não foram transmitidos — apenas o
   resumo e a lista de comandos; o output do teste decisivo (verificar_cadeia.py) sim, integral.
4. O canal de transmissão foi **chat (IM)**, não um commit/Gist assinado pela máquina de origem;
   a proveniência está declarada, mas não é criptograficamente atestada.
5. A conferência do agente (§6) cobre o **nível impresso** do output (16 hex + 4 decimais); a
   igualdade completa depende da C5 internal ao verificador que rodou lá (status VÁLIDO).
6. **1 máquina externa**: amostra de 1 não generaliza para "qualquer CPU" — a frase correta é
   "2 ambientes muito distintos, 0 divergências". Mais leitores = mais força (roadmap).

## 9. Como reproduzir / conferir esta página

```bash
# na SUA máquina (qualquer SO com Python 3 + numpy + torch CPU):
git clone https://github.com/Kronos1027/pouw-siren.git && cd pouw-siren
bash checar_integridade.sh                                  # 80 âncoras (15+23+37+5)
python3 fase3/verificar_cadeia.py > minha_saida.txt 2>&1    # confere a cadeia (C0+C1–C8)
python3 fase4/conferir_saida.py minha_saida.txt             # confere SUA saída contra a oficial
# código 0 dos dois = sua máquina reproduz os compromissos bit-a-bit — registre e reporte!
```

SHA-256 das âncoras desta fase: `fase4/hashes_fase4.sha256` (5 âncoras; inclui este relatório,
o script de conferência, o output verbatim, o log da conferência e o log da etapa 11).
