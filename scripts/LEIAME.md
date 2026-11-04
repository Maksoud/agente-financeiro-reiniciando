# scripts/

Python 3.10+, **só biblioteca padrão**. Rodar a partir da raiz do agente. Todos leem/gravam em `dados/` e `analise/` por padrão; `--help` mostra as opções.

| Script | Fluxo | Faz | Portão (código de saída) |
|---|---|---|---|
| `importar_resumo.py` | 1 (A) | resumo do sistema (layout `templates/layout-resumo-sistema.txt`) → `dados/resumo-sistema.json` + `dados/duvidas-categorias.csv` | 0 = todas as somas conferem · 1 = divergência (nada gravado) |
| `importar_resumo.py --verificar-duvidas` | 3 (A) | confere se o cliente explicou as categorias em dúvida | 0 = tudo explicado · 1 = pendente |
| `importar_extrato.py` | 1 (B) | CSV/OFX do banco → `dados/lancamentos.csv` (sem duplicar) | 0 = soma confere com o saldo · 1 = diferença · 2 = saldos não informados |
| `categorizar_regras.py aplicar` | 3 (B) | aplica regras do cliente + genéricas; gera `dados/duvidas.csv` | — |
| `categorizar_regras.py aprender` | 3 (B) | grava confirmação do cliente como regra nova | — |
| `categorizar_regras.py verificar` | 3 (B) | confere o limite X | 0 = nada ≥ X sem categoria · 1 = falta categoria |
| `indicadores_resumo.py` | 4 (A) | médias dos meses fechados, poupança, reserva em meses, contas em aberto, folga imediata, cartões, faturas vencidas, compromisso por mês | — (dados já conferidos no Fluxo 1) |
| `indicadores.py` | 4 (B) | totais por mês e categoria, fixas/variáveis, recorrências, taxa de poupança; anonimiza terceiros | 0 = decomposição fecha com a soma bruta · 1 = não fecha |
| `projetar_aporte.py` | 5 | juros compostos com aporte mensal em vários cenários; aporte para meta; IR e IPCA | — |
| `comum.py` | — | leitura de valores/datas BR, CSV, formatação `R$`, anonimização | — |

## Formato padrão da entrada B (`dados/lancamentos.csv`, separador `;`)

| Campo | Exemplo | Observação |
|---|---|---|
| id | `ef49de0c47be` | hash de conta+data+descrição+valor+sequência (evita duplicar na reimportação) |
| data | `2026-09-17` | AAAA-MM-DD |
| descricao | `LOJA XYZ COMERCIO` | literal do extrato |
| valor | `-389.90` | ponto decimal; negativo = saída |
| conta | `Banco X CC` | informado em `--conta` |
| origem | `extrato.csv` | arquivo de `entrada/` |

`lancamentos-categorizados.csv` acrescenta `categoria;tipo;regra;status`. `regra` diz quem decidiu: `geral:...` (regra genérica) ou `cliente:...` (confirmado pelo cliente; nunca é reclassificado).

## Taxas no `projetar_aporte.py`

Separe cenários com `;` quando usar vírgula decimal: `--taxas "10,5;12;14"`. Com ponto decimal, vírgula também serve: `--taxas 10.5,12,14`.
