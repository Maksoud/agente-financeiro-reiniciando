---
name: financeiro-classificar
description: Resolver a classificação no agente-financeiro-reiniciando. Na entrada A (resumo do sistema), o cliente explica as categorias genéricas ou lançadas do lado contrário. Na entrada B (extrato), aplica regras fixas e aprendidas (RAG), sugere categoria para o que sobrar e pede confirmação; cada confirmação vira regra. Fluxo 3.
---

# Classificação (Fluxo 3)

Objetivo: saber o que cada valor representa, **com o cliente confirmando o que não estava claro**. O agente sugere e o cliente confirma. Nunca reclassificar em silêncio.

## Antes de começar

1. Ler `CLAUDE.md`, `estado.md`, `dados/perfil-cliente.md` e `references/regras-categorizacao.md`.
2. Definir o **limite X** com o cliente (padrão R$ 100; sugerir ~1% da renda mensal). Registrar em `estado.md`.

## Entrada A: resumo do sistema

As categorias já vêm do sistema. O trabalho aqui é esclarecer as que não dizem o que são.

1. Abrir `dados/duvidas-categorias.csv` (gerado no Fluxo 1). Ele lista, com valor no ano ≥ X:
   - categorias **genéricas** (Diversos, Despesas Diversas, Receitas Diversas, Outros);
   - categorias do **lado contrário** (ex.: "Taxas e Impostos" como receita, "Reembolsáveis" como despesa, "Manut. <carro>" como receita).
2. Para cada linha, sugerir uma hipótese a partir dos meses em que aparece (`dados/resumo-sistema.json`) e perguntar ao cliente, em lotes de até 5: "Diversos (despesa) somou R$ X no ano, com pico em <mês>. O que costuma entrar aqui?".
3. Registrar a resposta literal do cliente na coluna `explicacao_cliente`. Exemplos: "presentes e farmácia", "estorno de IPVA", "reembolso da empresa: entra e sai igual".
4. Se a explicação mudar a leitura do diagnóstico, anotar em "Conflitos e respostas" do perfil. Exemplo: "Reembolsáveis" na despesa e na receita se anulam e não devem pesar no consumo.
5. Se o cliente quiser detalhar uma categoria genérica grande, importar o extrato do período (entrada B) e classificar só aqueles lançamentos.
6. Portão:
   ```bash
   python scripts/importar_resumo.py --verificar-duvidas --limite <X>
   ```

## Entrada B: extrato

1. **Regras primeiro (sem LLM):** `python scripts/categorizar_regras.py aplicar --limite <X>`. A ordem é `dados/regras-aprendidas.csv` (do cliente) e depois `references/regras-categorizacao.csv`.
2. **Sugestões** para cada linha de `dados/duvidas.csv` (maiores primeiro): consultar lançamentos parecidos já categorizados e as regras aprendidas, e preencher `sugestao` e `motivo_sugestao`.
3. **Mostrar em lotes de até 10**, agrupando descrições iguais: `data | descrição | valor | sugestão (motivo)`. O cliente confirma, corrige ou responde "não sei". Nomes de PIX aparecem só aqui; nos relatórios saem anonimizados.
4. **Cada confirmação vira regra:** `python scripts/categorizar_regras.py aprender "<trecho>" "<Categoria>" [--tipo fixa|variavel]`. O trecho deve identificar um único estabelecimento ou pessoa.
5. Repetir até passar no portão: `python scripts/categorizar_regras.py verificar --limite <X>`.

## Regras

- Não editar CSVs de classificação à mão, exceto a coluna `explicacao_cliente`, que é a resposta do cliente.
- Transferência entre contas, pagamento de fatura e investimentos seguem `references/regras-categorizacao.md`.

## Ao terminar

Atualizar `estado.md` (limite, dúvidas resolvidas, regras aprendidas, portão) e indicar o próximo passo: Fluxo 4.
