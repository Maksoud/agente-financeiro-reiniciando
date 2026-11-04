# Estado do agente financeiro

Cliente: [nome ou apelido] · Tratamento: [como prefere ser tratado] · Início: AAAA-MM-DD

| # | Fluxo | Status | Data | Arquivo | Portão |
|---|---|---|---|---|---|
| 1 | Importação | ⏳ pendente | | A: `dados/resumo-sistema.json` · B: `dados/lancamentos.csv` | A: somas conferem · B: soma = saldo do extrato |
| 2 | Perfil do cliente | ⏳ pendente | | `dados/perfil-cliente.md` | ★ respondidas |
| 3 | Classificação | ⏳ pendente | | A: `dados/duvidas-categorias.csv` · B: `dados/lancamentos-categorizados.csv` | nada ≥ R$ ___ sem explicação/categoria |
| 4 | Diagnóstico | ⏳ pendente | | `analise/` | script OK + cliente conferiu |
| 5 | Plano | ⏳ pendente | | `proposta/` | cliente aprovou |

Status: ⏳ pendente · 🔄 em andamento · ✅ concluído · ⛔ bloqueado (motivo abaixo)

## Fluxo 1: arquivos importados

Entrada usada: [A · resumo do sistema / B · extrato / A + B]

| Arquivo | Conta | Período | Lançamentos | Portão |
|---|---|---|---|---|

## Fluxo 3: classificação

- Limite X: R$ ___ (motivo: ___)
- Regras aprendidas até agora: ___

## Pendências e bloqueios

-

## Histórico

- AAAA-MM-DD: ___
