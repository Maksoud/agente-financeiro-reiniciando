# Projeção fictícia

Taxas ilustrativas, **não** são taxas atuais. Comando:

```bash
python scripts/projetar_aporte.py --aporte 500 --inicial 1500 --meses 60 --taxas "10,5;12;14" --ipca 4,5 --ir 15 --meta 50000
```

Aporte mensal R$ 500,00 | inicial R$ 1.500,00 | prazo 60 meses | total investido R$ 31.500,00 | IR 15% sobre o rendimento

| Cenário (a.a.) | 12 meses | 24 meses | 36 meses | 60 meses | Rendimento | Líquido IR | Hoje (IPCA) |
|---|---|---|---|---|---|---|---|
| 10,5% | R$ 7.941,05 | R$ 15.058,40 | R$ 22.923,08 | R$ 41.216,51 | R$ 9.716,51 | R$ 39.759,04 | R$ 31.904,68 |
| 12% | R$ 8.003,25 | R$ 15.286,89 | R$ 23.444,56 | R$ 42.814,15 | R$ 11.314,15 | R$ 41.117,03 | R$ 32.994,40 |
| 14% | R$ 8.085,89 | R$ 15.593,81 | R$ 24.152,84 | R$ 45.033,45 | R$ 13.533,45 | R$ 43.003,43 | R$ 34.508,15 |

Aporte mensal necessário para chegar a R$ 50.000,00 em 60 meses (antes de IR):
- 10,5% a.a.: R$ 613,35
- 12% a.a.: R$ 589,44
- 14% a.a.: R$ 558,92

Projeção educativa. Rentabilidade passada ou estimada não garante resultado futuro.
