# exemplos/

Dados **fictícios** (persona e valores gerados) para testar os scripts e mostrar o formato das saídas.

**Entrada A · resumo do sistema**
- `resumo-sistema-ficticio.txt`: o layout de `templates/layout-resumo-sistema.txt` preenchido com valores fictícios consistentes (12 meses, dezembro provisionado, 4 cartões fictícios). Passa em todas as conferências do `importar_resumo.py`.
- `indicadores-resumo-ficticio.md`: saída de `indicadores_resumo.py --hoje 2026-11-20` sobre o arquivo acima.

**Entrada B · extrato**
- `extrato-ficticio.csv`: 3 meses de conta corrente (saldo inicial R$ 2.350,00, final R$ 3.317,07). Inclui PIX para terceiros, fatura de cartão e aporte, para exercitar anonimização e categorias neutras.
- `indicadores-ficticio.md`: saída de `indicadores.py --fatura-como-despesa` depois de classificar o extrato acima.

**Fluxo 5**
- `projecao-ficticia.md`: saída de `projetar_aporte.py` com taxas ilustrativas (não são taxas atuais).
