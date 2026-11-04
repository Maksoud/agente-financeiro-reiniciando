# Agente Financeiro Reiniciando

Agente para Claude (Claude Code ou Cowork) que transforma a exportação do sistema de controle financeiro (ou o extrato bancário) de uma pessoa em:

1. uma tabela organizada de lançamentos,
2. um diagnóstico com números conferidos (renda, gastos fixos e variáveis, recorrências, taxa de poupança),
3. um plano **educativo** de orçamento e investimentos por objetivo.

O agente não acessa banco nem conta: ele só lê os arquivos que você coloca em `entrada/`. Todo número vem de um script ou de uma fonte citada com data.

> Conteúdo educativo. Não é recomendação individual de investimento (atividade regulada pela CVM).

## Como usar

1. Coloque em `entrada/` um destes:
   - **A (principal):** a exportação "Análise Financeira Anual" do sistema, como `resumo-sistema-AAAA-MM-DD.txt`, no layout de [`templates/layout-resumo-sistema.txt`](templates/layout-resumo-sistema.txt);
   - **B:** o extrato do banco e do cartão (CSV ou OFX; PDF também serve, mas dá mais trabalho).
2. Abra a pasta no Claude Code e diga: **"siga o agente-financeiro"**.
3. O agente conduz os 5 fluxos, um de cada vez, e para quando precisa de você:

| # | Fluxo | O que você faz |
|---|---|---|
| 1 | Importação | Nada (A) ou informa o saldo inicial e final do extrato (B) |
| 2 | Perfil | Responde o questionário (objetivos, prazo, reserva, risco, dívidas) |
| 3 | Classificação | Explica categorias genéricas como "Diversos" (A) ou confirma as categorias em que o agente ficou em dúvida (B) |
| 4 | Diagnóstico | Confere os números |
| 5 | Plano | Revisa e aprova |

O progresso fica em `estado.md`. Pode parar e continuar depois.

## Requisitos

- Python 3.10 ou mais novo (só biblioteca padrão, nada para instalar).
- Testar com os exemplos fictícios:

```bash
# Entrada A: resumo do sistema
python scripts/importar_resumo.py exemplos/resumo-sistema-ficticio.txt
python scripts/indicadores_resumo.py --hoje 2026-11-20

# Entrada B: extrato
python scripts/importar_extrato.py exemplos/extrato-ficticio.csv --conta "Banco Ficticio CC" --saldo-inicial 2.350,00 --saldo-final 3.317,07
python scripts/categorizar_regras.py aplicar
python scripts/indicadores.py --fatura-como-despesa
python scripts/projetar_aporte.py --aporte 500 --inicial 1500 --meses 60 --taxas "10,5;12;14" --ipca 4,5 --ir 15
```

(Depois do teste, apague `dados/` e `analise/` antes de usar com dados reais.)

## Privacidade

`entrada/`, `dados/`, `analise/`, `proposta/` e `estado.md` estão no `.gitignore`. Extrato bancário é dado sensível: nada disso vai para o repositório. Nomes de terceiros (PIX, transferências) saem anonimizados nos relatórios.

## Estrutura

Veja `CLAUDE.md` (regras e fluxos) e `scripts/LEIAME.md` (formato dos dados e uso dos scripts).

Licença: MIT (`LICENSE.md`).
