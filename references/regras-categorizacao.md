# Regras de categorização

Usado no Fluxo 3. As regras aplicáveis por script ficam em CSV:

| Arquivo | Conteúdo | Publicado? |
|---|---|---|
| `references/regras-categorizacao.csv` | regras genéricas (IFOOD → Alimentação etc.) | sim |
| `dados/regras-aprendidas.csv` | confirmações do cliente (têm prioridade) | **não** |

Formato: `padrao;categoria;tipo;observacao`. O `padrao` é procurado dentro da descrição já normalizada (maiúsculas, sem acento). Começando com `re:` é expressão regular (ex.: `re:^PIX .*CONDOMINIO`). A primeira regra que casar vence; por isso, padrões específicos antes dos genéricos.

## Categorias

**As categorias são do cliente, não do agente.** Cada cliente organiza receitas e despesas do seu jeito (nomes, agrupamentos, o que é receita ou despesa). A lista abaixo é **apenas um exemplo** de estrutura de um cliente, usada como ponto de partida quando o cliente não tem a sua.

- Usar sempre as categorias que vierem do sistema ou da explicação do próprio cliente, com os mesmos nomes, para os relatórios serem comparáveis.
- Não renomear, juntar nem "corrigir" categorias do cliente para encaixar neste exemplo.
- Quando não estiver claro se uma categoria é **receita, despesa ou neutra** (ex.: "Reembolsáveis", "Empréstimos", "Família", "Diversos"), ou qual é o significado dela, **perguntar ao cliente** (registrar em `dados/duvidas-categorias.csv` ou `dados/duvidas.csv`). Nunca assumir pelo nome.
- A resposta do cliente vira regra em `dados/regras-aprendidas.csv`, que tem prioridade sobre `references/regras-categorizacao.csv`.

### Exemplo de estrutura (de um cliente)

**Receitas:** Salários e Quinzenas · PLR · Férias e 13° salário · Rendimentos de Aplicações · Reembolsáveis · Receitas Diversas

**Despesas:**
| Grupo | Categorias |
|---|---|
| Moradia | Habitação (aluguel, condomínio, financiamento) · Despesas de Casa (água, gás, manutenção) · Energia · Internet · Celular |
| Alimentação | Alimentação |
| Transporte | Transportes · Combustíveis · Carros · Manut. <veículo> (uma por veículo, se o cliente quiser) |
| Saúde | Saúde e Medicamentos |
| Educação | Escola · Cursos e Treinamentos |
| Pessoal | Roupas e Acessórios · Pet · Doações · Planos e Assinaturas |
| Financeiro | Taxas e Impostos · Juros e encargos · Empréstimos |
| Outros | Despesas Diversas · Não identificado |

**Neutras (não entram em receita nem despesa):**
- `Transferência entre contas`: entre contas do próprio cliente.
- `Pagamento de fatura`: o gasto já está no extrato do cartão. Sem o extrato do cartão, `indicadores.py --fatura-como-despesa`.
- `Investimentos`: aporte (saída) e resgate (entrada). Conta como poupança, não como consumo.

## Fixa ou variável

- **Fixa:** valor e periodicidade previsíveis (aluguel, escola, plano de saúde, assinaturas, mesada/PIX mensal combinado).
- **Variável:** depende do uso (mercado, combustível, delivery, compras).
- A regra pode fixar o tipo. Sem tipo, o `indicadores.py` marca como fixa a descrição que aparece em 3+ meses com valor até 15% da mediana.

## Boas práticas ao criar regra (`categorizar_regras.py aprender`)

- Trecho que identifique **um** estabelecimento ou pessoa: `ACADEMIA CORPO`, não `ACADEMIA`.
- PIX para pessoa: usar o nome como aparece no extrato (fica só em `dados/`, que é privado).
- Mesmo destino com finalidades diferentes (ex.: PIX para um parente que às vezes é presente e às vezes é reembolso) ⇒ **não** criar regra; confirmar caso a caso.
- Marketplaces e intermediadores (Mercado Pago, PicPay, PagSeguro, Amazon) costumam misturar categorias: evitar regra genérica.
