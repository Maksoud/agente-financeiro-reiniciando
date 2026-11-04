---
name: financeiro-diagnostico
description: Calcular os indicadores (renda, gastos fixos e variáveis, taxa de poupança, reserva, cartões, contas em aberto, compromisso futuro) com scripts/indicadores_resumo.py ou scripts/indicadores.py e escrever o diagnóstico do cliente em analise/ do agente-financeiro-reiniciando, conferido com o cliente. Fluxo 4.
---

# Diagnóstico (Fluxo 4)

Objetivo: retrato fiel de onde o dinheiro entra e sai e do que já está comprometido. **Portão:** script sem erro **e** cliente confirma que os números batem com a percepção dele (ou explica a diferença).

## Antes de começar

1. Ler `CLAUDE.md`, `estado.md` e `dados/perfil-cliente.md`. O portão do Fluxo 3 foi cumprido? Se não, avisar e parar.
2. Ver em `estado.md` qual entrada foi usada (A, B ou ambas).

## Passo a passo

1. Rodar o script da entrada:
   - **A · resumo do sistema:**
     ```bash
     python scripts/indicadores_resumo.py --hoje <data da exportação>
     ```
     `--hoje` = data em que o cliente exportou o resumo (vale para faturas vencidas e contas em atraso).
   - **B · extrato:**
     ```bash
     python scripts/indicadores.py --saldo-anterior <saldo antes do 1º mês> [--fatura-como-despesa]
     ```
     Sem extrato do cartão ⇒ `--fatura-como-despesa` e avisar que falta o detalhe por categoria.
   - Ambas: gerar as duas saídas e dizer de onde vem cada número. Não somar uma com a outra.
2. Escrever `analise/AAAA-MM-DD-diagnostico.md` a partir de `templates/relatorio-diagnostico.md`, usando **só números dos arquivos gerados** (copiar, não recalcular). Seguir os 5 tópicos de `references/prompt-analise-anual.md`:
   1. saúde geral e tendência (meses fechados; mês atual e provisionados à parte);
   2. despesas: categorias que mais pesam, consumo/receita, fixas/receita, uso dos cartões;
   3. pontos de atenção: faturas vencidas, contas em atraso, folga imediata negativa, meses negativos, compromisso futuro nos cartões (por mês), juros, dívidas do perfil;
   4. oportunidades de economia em R$/mês, citando a categoria de origem (sem plano ainda: o plano é o Fluxo 5);
   5. fechamento do ano: "Saldo acumulado final" do sistema (entrada A), explicando que inclui provisionados. Na entrada B, só se houver média calculada por script.
3. Usar as explicações do cliente de `dados/duvidas-categorias.csv` ao comentar categorias genéricas.
4. Mostrar ao cliente o **Resumo** e os **3 principais pontos de atenção** e perguntar: "esses números batem com o que você imagina?". Registrar a resposta na seção Conferência.

## Regras

- Nada de número sem origem. Cada tabela cita o arquivo de onde saiu.
- Nomes de terceiros anonimizados.
- Sem tom de julgamento: fato, impacto em R$ e pergunta.
- Terminar com o aviso educativo de `references/limites-eticos.md`.

## Ao terminar

Atualizar `estado.md` (arquivo do diagnóstico, conferência do cliente) e indicar o próximo passo: Fluxo 5.
