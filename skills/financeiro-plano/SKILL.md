---
name: financeiro-plano
description: Montar o plano educativo do cliente no agente-financeiro-reiniciando (metas de corte, aporte mensal, reserva de emergência e classes de investimento por objetivo) com taxas públicas citadas com data e projeções do scripts/projetar_aporte.py, sem recomendar produto específico, para o cliente revisar e aprovar. Fluxo 5.
---

# Plano (Fluxo 5)

Objetivo: caminho concreto do orçamento atual até os objetivos do perfil. **Portão:** cliente revisa e **aprova** (até lá, o arquivo é rascunho).

## Antes de começar

1. Ler `CLAUDE.md`, `estado.md`, `dados/perfil-cliente.md`, o diagnóstico mais recente em `analise/`, o `.json` de indicadores do mesmo dia e, na entrada A, `dados/resumo-sistema.json` (cartões, contas em aberto, provisionados).
2. Ler `references/limites-eticos.md`, `references/glossario-produtos.md` e `references/fontes-taxas.md`.
3. Diagnóstico não conferido pelo cliente ⇒ avisar e parar.

## Passo a passo (uma etapa por rodada com o cliente)

1. **Ordem de prioridades** (explicar o porquê de cada uma):
   1. contas em atraso, faturas vencidas, folga imediata negativa e dívidas caras (rotativo, cheque especial, empréstimo pessoal): comparar a taxa da dívida com a taxa de aplicação. Parcelas já assumidas nos cartões reduzem o aporte possível nos meses em que vencem (tabela "compromisso por mês");
   2. reserva de emergência: alvo = N × despesa **fixa** média mensal do `.json` (N = 3 a 6 para renda estável CLT, 6 a 12 para renda variável/autônomo; confirmar com o cliente);
   3. objetivos do perfil, por prazo.
2. **Metas de corte:** só em categorias variáveis ou recorrências que o cliente apontou como dispensáveis. Para cada uma: valor atual (do script), meta proposta, quanto libera por mês. A meta é proposta; o cliente decide.
3. **Aporte mensal:** = saldo médio mensal (script) + cortes aceitos. Mostrar a conta com os números de origem.
4. **Taxas:** buscar o valor atual em fonte oficial (ver `references/fontes-taxas.md`) e registrar no plano: `taxa | valor | fonte | data da consulta`. Montar 3 cenários (conservador, base, otimista) a partir delas e explicar a escolha.
5. **Projeções:** para cada objetivo,
   ```bash
   python scripts/projetar_aporte.py --aporte <A> --inicial <I> --meses <prazo> --taxas "<c1>;<c2>;<c3>" --ipca <ipca> --ir <aliquota> [--meta <valor>]
   ```
   Colar a tabela do script no plano, sem arredondar à mão.
6. **Classes por objetivo:** usar `references/glossario-produtos.md`. Para cada objetivo: classe sugerida, por que combina com o prazo/liquidez/risco do perfil, riscos e custos a observar. **Sem nomes de produto, emissor, fundo ou corretora.**
7. Escrever `proposta/AAAA-MM-DD-plano.md` a partir de `templates/plano-investimentos.md`, com status **RASCUNHO**.
8. Apresentar ao cliente uma seção por vez. Ajustar conforme as respostas. Ao final, pedir aprovação explícita; aprovado ⇒ status **APROVADO em AAAA-MM-DD**.

## Regras

- Nenhum número sem script ou fonte com data.
- Nenhuma recomendação de produto específico; aviso educativo no fim (texto exato de `references/limites-eticos.md`).
- Perfil com dívida cara ⇒ não sugerir investimento de risco antes de tratar a dívida (explicar com números).
- Se o cliente pedir "qual fundo/ação comprar": explicar o limite, oferecer os critérios para ele mesmo comparar (taxa, liquidez, FGC, imposto, risco) e sugerir procurar profissional certificado/registrado se quiser recomendação individual.

## Ao terminar

Atualizar `estado.md` (arquivo do plano, status, data de aprovação) e sugerir quando repetir o ciclo (ex.: importar o próximo mês e comparar com as metas).
