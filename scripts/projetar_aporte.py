"""Fluxo 5: projeção de juros compostos com aporte mensal, comparando cenários de taxa.

Uso:
  python scripts/projetar_aporte.py --aporte 500 --meses 60 --taxas 10,12,14 [--inicial 1000]
        [--ipca 4,5] [--ir 15] [--meta 50000]

  --taxas  taxas ANUAIS em % (uma por cenário), separadas por vírgula ou ponto e vírgula.
           Use taxas com fonte e data (ver references/fontes-taxas.md). O script não busca taxas.
  --ipca   inflação anual esperada em %: mostra também o valor em poder de compra de hoje.
  --ir     alíquota de IR (%) aplicada sobre o rendimento no resgate final (simplificação: não
           considera come-cotas, IOF nem tabela regressiva mês a mês).
  --meta   valor-alvo: calcula o aporte mensal necessário em cada cenário.

Fórmula: taxa mensal = (1 + anual)^(1/12) - 1; saldo(m) = saldo(m-1) * (1 + i) + aporte
(aporte no fim de cada mês).
"""
import argparse
import sys
from decimal import Decimal, getcontext

from comum import brl

getcontext().prec = 28


def num(t: str) -> Decimal:
    return Decimal(t.strip().replace(",", "."))


def taxa_mensal(anual_pct: Decimal) -> Decimal:
    return Decimal(str((1 + float(anual_pct) / 100) ** (1 / 12) - 1))


def projetar(inicial: Decimal, aporte: Decimal, meses: int, i: Decimal) -> list[Decimal]:
    saldos, s = [], inicial
    for _ in range(meses):
        s = s * (1 + i) + aporte
        saldos.append(s)
    return saldos


def aporte_para_meta(meta: Decimal, inicial: Decimal, meses: int, i: Decimal) -> Decimal:
    fator = (1 + i) ** meses
    if i == 0:
        return (meta - inicial) / meses
    return max((meta - inicial * fator) * i / (fator - 1), Decimal(0))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--aporte", required=True)
    p.add_argument("--meses", type=int, required=True)
    p.add_argument("--taxas", required=True)
    p.add_argument("--inicial", default="0")
    p.add_argument("--ipca", default=None)
    p.add_argument("--ir", default="0")
    p.add_argument("--meta", default=None)
    a = p.parse_args()

    aporte, inicial, ir = num(a.aporte), num(a.inicial), num(a.ir) / 100
    sep = ";" if ";" in a.taxas else ","
    # aceita "10,5;12" ou "10.5,12"
    taxas = [num(t) for t in a.taxas.split(sep) if t.strip()]
    ipca_m = taxa_mensal(num(a.ipca)) if a.ipca else None
    investido = inicial + aporte * a.meses

    print(f"Aporte mensal {brl(aporte)} | inicial {brl(inicial)} | prazo {a.meses} meses | "
          f"total investido {brl(investido)}" + (f" | IR {a.ir}% sobre o rendimento" if ir else ""))
    marcos = sorted({m for m in (12, 24, 36, 60, 120, 240) if m < a.meses} | {a.meses})
    cab = "| Cenário (a.a.) | " + " | ".join(f"{m} meses" for m in marcos) + " | Rendimento | Líquido IR |" \
          + (" Hoje (IPCA) |" if ipca_m else "")
    print("\n" + cab)
    print("|" + "---|" * (cab.count("|") - 1))
    for t in taxas:
        i = taxa_mensal(t)
        s = projetar(inicial, aporte, a.meses, i)
        final = s[-1]
        rendimento = final - investido
        liquido = final - max(rendimento, Decimal(0)) * ir
        linha = f"| {str(t).replace('.', ',')}% | " + " | ".join(brl(s[m - 1]) for m in marcos)
        linha += f" | {brl(rendimento)} | {brl(liquido)} |"
        if ipca_m:
            linha += f" {brl(liquido / (1 + ipca_m) ** a.meses)} |"
        print(linha)

    if a.meta:
        meta = num(a.meta)
        print(f"\nAporte mensal necessário para chegar a {brl(meta)} em {a.meses} meses (antes de IR):")
        for t in taxas:
            print(f"- {str(t).replace('.', ',')}% a.a.: {brl(aporte_para_meta(meta, inicial, a.meses, taxa_mensal(t)))}")
    print("\nProjeção educativa. Rentabilidade passada ou estimada não garante resultado futuro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
