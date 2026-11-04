# Fontes de taxas (Fluxo 5)

Toda taxa usada em projeção entra no plano com **valor, fonte e data da consulta**. Nunca usar taxa de memória.

| Indicador | Fonte oficial | Onde |
|---|---|---|
| Meta Selic | Banco Central do Brasil (Copom) | bcb.gov.br → Política monetária → Taxa Selic |
| CDI | B3 | b3.com.br → Market data → Taxas (DI) |
| IPCA (12 meses) | IBGE | ibge.gov.br → Índices de preços → IPCA |
| Expectativas (Selic, IPCA fim de ano) | BCB, Boletim Focus (semanal) | bcb.gov.br → Publicações → Focus |
| Taxas do Tesouro Direto | Tesouro Nacional | tesourodireto.com.br → Preços e taxas |
| Séries históricas | BCB SGS | api.bcb.gov.br/dados/serie/bcdata.sgs.<código>/dados/ultimos/1?formato=json (432 = meta Selic; 4389 = CDI anualizado; 13522 = IPCA 12 meses) |

## Como montar os cenários

- **Conservador:** pós-fixado próximo do CDI atual descontado de IR, ou poupança, conforme a classe.
- **Base:** expectativa do Focus para os próximos anos (média, não a taxa de hoje, se o prazo for longo).
- **Otimista:** taxa real do Tesouro IPCA+ com vencimento próximo ao objetivo + IPCA esperado.
- Explicar no plano por que cada cenário foi escolhido. Para prazos longos, preferir mostrar o resultado em **valores de hoje** (`--ipca`).

## Registro no plano

```
| Taxa | Valor | Fonte | Consulta |
|---|---|---|---|
| Meta Selic | __,__% a.a. | BCB, Copom | AAAA-MM-DD |
```
