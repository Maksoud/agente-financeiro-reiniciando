---
name: financeiro-perfil-cliente
description: Conduzir o questionário do perfil financeiro do cliente (objetivos, prazos, reserva atual, tolerância a risco, dívidas, renda e dependentes) no agente-financeiro-reiniciando e salvar em dados/perfil-cliente.md. Fluxo 2.
---

# Perfil do cliente (Fluxo 2)

Objetivo: saber **para que** o dinheiro serve antes de dizer onde cortar ou investir. **Portão:** todas as perguntas marcadas ★ em `templates/perfil-cliente.md` respondidas (resposta "prefiro não dizer" vale, mas fica registrada).

## Passo a passo

1. Ler `CLAUDE.md`, `estado.md` e, se existir, `dados/perfil-cliente.md` (retomar de onde parou).
2. Copiar `templates/perfil-cliente.md` para `dados/perfil-cliente.md` se ainda não existir.
3. Perguntar **um bloco por vez**, na ordem do template. Em cada bloco:
   - fazer as perguntas em linguagem simples, com exemplos de resposta;
   - registrar a resposta literal do cliente e, ao lado, a interpretação (ex.: prazo "uns 3 anos" ⇒ 36 meses);
   - pergunta não respondida ⇒ `[A CONFIRMAR]`.
4. Perfil de risco: usar as perguntas do template (reação a perda, prazo, experiência). **Não** é suitability formal de corretora; deixar isso claro ao cliente.
5. Dívidas: pedir taxa de juros e saldo devedor de cada uma. Sem taxa ⇒ `[A CONFIRMAR]` (vai pesar no plano: quitar dívida cara costuma vir antes de investir).
6. Conflito entre resposta e dados do extrato (ex.: diz não ter dívida, mas há "JUROS" no extrato) ⇒ perguntar de forma neutra e registrar em "Conflitos e respostas".

## Regras

- Não pedir dados de acesso, número de conta ou documentos.
- Não julgar objetivos. Registrar como o cliente falou.
- Perguntas sobre terceiros (cônjuge, filhos): só o necessário para o orçamento (quantos dependentes, se a renda é compartilhada).

## Ao terminar

- Conferir o checklist ★ no fim do arquivo. Faltou algo ⇒ portão não cumprido.
- Atualizar `estado.md` e indicar o próximo passo (Fluxo 1 se ainda não importou, senão Fluxo 3).
