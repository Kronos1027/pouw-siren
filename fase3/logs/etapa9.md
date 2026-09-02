# logs/etapa9.md — Fase 3: cadeia demo encadeada + lote + teste negativo (Task ID 4)

**Data:** 2026-09-02, 03:43–03:53 UTC (timestamps em cada log bruto) · **Repo:** https://github.com/Kronos1027/pouw-siren

## Sequência executada

1. **Smoke (2 blocos):** `fase3/cadeia.py --blocos 2 --saida fase3/smoke` +
   `verificar_cadeia.py fase3/smoke` + `experimento_lote.py fase3/smoke` — 2/2 blocos válidos;
   compromissos do bloco 1 idênticos aos da mineração oficial subsequente. Logs:
   `f3_smoke_cadeia.txt`, `f3_smoke_verificar.txt`, `f3_smoke_lote.txt`.
2. **GATILHO de pesquisa:** o bloco 2 do smoke divergiu do oficial (comp `42f0ada7…` vs
   `0fff8405…`) com desafios byte-idênticos — investigado por script ad hoc (sha256 dos .npy,
   comparação tensor a tensor dos pesos: max|Δ| 2,8e-06) e formalizado no E5.
3. **E1 — mineração oficial:** 8 blocos, alvo 40 dB, prefixo 16 bits (`f3_e1_cadeia.txt`):
   treino 32,420560 s (útil) vs moagem 0,326192 s (quebra, razão 99:1); parede 48,607037 s;
   ponta da cadeia `00001c19b2ff…`; cadeia.json sha256 `5b7b3501…`.
4. **E2 — verificação fria:** 8/8 VÁLIDOS, código 0; 0,138637 s sem import (`f3_e2_verif_fria.txt`).
5. **E3 — lote vs frio** (`f3_e3_lote.txt`): lote 15,6 ms/bloco (64,2 blocos/s; mediana de 5
   passadas) vs frio-por-bloco 1.126 ms/bloco (72,3×); import 1,307 s = 10× o lote;
   razão mineração/lote 390,2×.
6. **E4 — teste negativo:** 1ª execução 4/5 com MINHA expectativa errada no modo "desafio"
   (fraude detectada via C3, mas eu esperava C2 também) — log preservado
   (`f3_e4_negativo_EXECUCAO1_EXPECTATIVA_ERRADA.txt`); expectativa corrigida + modo
   `comp_desafio` adicionado; 2ª execução **6/6** (`f3_e4_negativo.txt`).
7. **E5 — re-treino** (`f3_e5_retreino.py`, `f3_e5_retreino.txt`): 4 réplicas default
   BIT-IDÊNTICAS à oficial; 2 com OMP=1 divergem 5,076e-08; o evento do smoke (2,8e-06) não
   reproduzido (1 em ~8 execuções). Causa não isolada (limitação 1 do relatório F3).
8. **E6 — inventário** (`f3_e6_inventario.txt`): 181.264 B/bloco (1,38 MiB a cadeia);
   37 âncoras em `hashes_fase3.sha256` (5 scripts + cadeia oficial 25 + smoke 7) — 37/37 OK.
9. **relatorio_fase3.md** (14 seções, 13 limitações) + README atualizado (seção Fase 3) +
   `checar_integridade.sh` agora cobre 75 âncoras (15+23+37).

## Incidentes

- **Divergência do bloco 2 smoke→oficial:** virou o E5 (achado documentado; o consenso não
  depende de re-treino — princípio "verificar o publicado" reforçado).
- **Expectativa errada no E4 (1ª execução):** preservada; a detecção de fraude em si nunca falhou.

## Resultado

- Cadeia `pouw-cadeia-demo-v1` de 8 blocos publicável e verificável de ponta a ponta; 6/6 fraudes
  rejeitadas; custos medidos nos dois extremos (lote 64,2 blocos/s vs frio-por-bloco 0,89); 37
  âncoras novas; 5 scripts novos (`cadeia.py`, `verificar_cadeia.py`, `teste_negativo.py`,
  `experimento_lote.py`, `experimento_retreino.py`).
