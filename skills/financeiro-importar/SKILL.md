---
name: financeiro-importar
description: Ler a entrada do cliente no agente-financeiro-reiniciando, seja a exportação "Análise Financeira Anual" do sistema de controle financeiro (entrada A, layout em templates/layout-resumo-sistema.txt) ou o extrato bancário CSV/OFX/PDF (entrada B), conferir todas as somas e gravar em dados/. Fluxo 1.
---

# Importação (Fluxo 1)

Objetivo: dados de entrada confiáveis. Há dois layouts aceitos:

| Entrada | Arquivo em `entrada/` | Script | Saída | Portão |
|---|---|---|---|---|
| **A · Resumo do sistema** (principal) | `resumo-sistema-AAAA-MM-DD.txt` no layout de `templates/layout-resumo-sistema.txt` | `importar_resumo.py` | `dados/resumo-sistema.json` + `dados/duvidas-categorias.csv` | todas as somas do resumo conferem |
| **B · Extrato** (alternativa ou complemento) | CSV/OFX do banco (PDF transcrito) | `importar_extrato.py` | `dados/lancamentos.csv` | saldo inicial + soma = saldo final |

Preferir **A** quando o cliente usa o sistema: já vem categorizado, com fixas/variáveis, provisionados, contas em aberto e cartões. Usar **B** quando não há sistema, ou para detalhar uma categoria genérica do resumo (ex.: o que há dentro de "Diversos").

## Antes de começar

1. Ler `CLAUDE.md` e `estado.md` (criar de `templates/estado.md` se não existir).
2. Listar `entrada/` e identificar o tipo de cada arquivo.
3. Sem arquivo ⇒ pedir ao cliente a exportação do sistema (entrada A). Se não tiver, o extrato exportado do banco, de preferência dos últimos 3 a 12 meses, mais o do cartão.
4. **Nunca** pedir senha nem acessar banco/app/sistema. Só arquivos em `entrada/`.

## Entrada A: resumo do sistema

1. Conferir que o texto segue o layout: blocos `Mês:` (com "(mês atual)" e "(provisionado)" quando houver), `Resumo do Ano:`, `Contas em Aberto` e `Cartões de Crédito`. O cabeçalho do prompt (antes de "DADOS FINANCEIROS") pode vir junto: é ignorado.
2. Rodar:
   ```bash
   python scripts/importar_resumo.py entrada/resumo-sistema-AAAA-MM-DD.txt --ano <ano> --limite <X>
   ```
3. O script confere, por mês, categorias = total, fixas + variáveis = total, saldo = receitas − despesas; o saldo acumulado encadeado; os totais do ano (também por categoria); realizado + provisionado; contas em aberto; e cartões (soma das faturas, limite − utilizado = disponível, resumo dos cartões).
4. **Portão reprovado** ⇒ mostrar as divergências ao cliente. A causa costuma ser uma exportação editada à mão ou cortada. Pedir uma nova exportação e não corrigir números por conta própria.
5. Avisos (ex.: limite utilizado ≠ soma das faturas) não bloqueiam, mas viram pergunta ao cliente no Fluxo 2 ou 3.

## Entrada B: extrato

1. Perguntar o nome da conta e o **saldo inicial e final** do período (no próprio extrato).
2. Rodar, por arquivo:
   ```bash
   python scripts/importar_extrato.py entrada/<arquivo> --conta "<conta>" --saldo-inicial <valor> --saldo-final <valor>
   ```
   - OFX: o saldo final é lido do arquivo.
   - Cartão: `--saldo-inicial 0` e `--saldo-final` = menos o total da fatura do período.
3. **PDF:** extrair o texto (skill de PDF), transcrever para `entrada/<nome>-transcrito.csv` (`Data;Histórico;Valor`), mostrar ao cliente as primeiras e últimas linhas e então rodar o script.
4. Portão reprovado ⇒ investigar linhas de saldo lidas como lançamento, período diferente do saldo informado, sinal invertido ou lançamentos futuros. Nunca "forçar" o saldo.

## Ao terminar

- Atualizar `estado.md`: entrada usada (A/B), arquivos, período, resultado do portão e avisos.
- Dizer ao cliente o que foi lido (números do script) e o próximo passo: Fluxo 2 se ainda não foi feito, senão Fluxo 3.
