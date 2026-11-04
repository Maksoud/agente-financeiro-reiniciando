# dados/

Fatos organizados. **Não publicar** (pasta no `.gitignore`).

| Arquivo | Entrada | Gerado por | Conteúdo |
|---|---|---|---|
| `resumo-sistema.json` | A | `importar_resumo.py` (Fluxo 1) | meses, resumo do ano, contas em aberto e cartões, já conferidos |
| `duvidas-categorias.csv` | A | `importar_resumo.py` (Fluxo 1/3) | categorias genéricas ou do lado contrário; a coluna `explicacao_cliente` recebe a resposta do cliente |
| `lancamentos.csv` | B | `importar_extrato.py` (Fluxo 1) | `id;data;descricao;valor;conta;origem` |
| `lancamentos-categorizados.csv` | B | `categorizar_regras.py` (Fluxo 3) | + `categoria;tipo;regra;status` |
| `duvidas.csv` | B | `categorizar_regras.py aplicar` | sem regra, com sugestão do agente para o cliente confirmar |
| `regras-aprendidas.csv` | B | `categorizar_regras.py aprender` | regras confirmadas pelo cliente (prioridade sobre as genéricas) |
| `perfil-cliente.md` | A e B | Fluxo 2 (de `templates/perfil-cliente.md`) | questionário respondido |

Não editar à mão, exceto a coluna `explicacao_cliente`. Use os scripts para manter o histórico de quem decidiu o quê.
