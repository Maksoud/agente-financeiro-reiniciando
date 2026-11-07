"""Fluxo 4 (entrada A): indicadores a partir de dados/resumo-sistema.json (gerado por importar_resumo.py).

Uso:
  python scripts/indicadores_resumo.py [--hoje AAAA-MM-DD] [--data AAAA-MM-DD]

Saídas: analise/AAAA-MM-DD-indicadores.md e .json

Regras de cálculo:
  - Médias mensais usam só meses FECHADOS (nem o mês atual, que está em andamento, nem provisionados).
  - Categoria 'Investimentos' lançada como despesa é aporte: sai da despesa de consumo e aparece à parte.
  - Taxa de poupança (realizado) = (receitas - despesas de consumo) / receitas, meses fechados.
  - Reserva em meses = aplicações / despesa fixa média mensal (e / despesa média total).
  - Folga imediata = saldo bancário + a receber - a pagar - próximas faturas dos cartões.
  - Fatura em aberto com vencimento anterior a --hoje = fatura atrasada.
  - --neutras "Cat1,Cat2": categorias de repasse (ex.: Reembolsáveis). Saem da receita E da despesa
    (médias, taxas e % por categoria). As colunas Saldo/Acumulado continuam as do sistema (com repasses).
  - --eventuais "Cat1,Cat2": categorias de receita que não se repetem. Continuam no total, mas a
    "receita recorrente" (sem elas) aparece à parte, com a taxa de poupança correspondente.
Nenhum número é estimado: tudo sai do JSON importado (que passou pelo portão do Fluxo 1).
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from comum import RAIZ, brl, ler_csv, normalizar_texto

D0 = Decimal(0)


def dec(x) -> Decimal:
    return Decimal(str(x)) if x not in (None, "None") else D0


def pct(a: Decimal, b: Decimal) -> str:
    return f"{a / b * 100:.1f}%".replace(".", ",") if b else "n/d"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entrada", type=Path, default=RAIZ / "dados" / "resumo-sistema.json")
    p.add_argument("--hoje", default=f"{date.today():%Y-%m-%d}")
    p.add_argument("--data", default=f"{date.today():%Y-%m-%d}")
    p.add_argument("--saida", type=Path, default=RAIZ / "analise")
    p.add_argument("--neutras", default="", help="categorias de repasse, separadas por vírgula")
    p.add_argument("--eventuais", default="", help="categorias de receita não recorrentes, separadas por vírgula")
    a = p.parse_args()
    if not a.entrada.exists():
        sys.exit("dados/resumo-sistema.json não existe. Rode scripts/importar_resumo.py (Fluxo 1).")
    r = json.loads(a.entrada.read_text(encoding="utf-8"))
    res = {k: dec(v) for k, v in r["resumo"].items()}

    def eh_invest(cat):
        return normalizar_texto(cat).startswith("INVESTIMENTO")

    def lista(txt):
        return {normalizar_texto(x) for x in txt.split(",") if x.strip()}
    neutras, eventuais = lista(a.neutras), lista(a.eventuais)

    def soma_cats(cats, alvo):
        return sum((dec(c["valor"]) for k, c in cats.items() if normalizar_texto(k) in alvo), D0)
    rec_fech_cat = defaultdict(lambda: D0)
    desp_fech_cat = defaultdict(lambda: D0)

    meses = []
    for m in r["meses"]:
        neu_r = soma_cats(m["receitas"]["categorias"], neutras)
        neu_d = soma_cats(m["despesas"]["categorias"], neutras)
        rec = dec(m["receitas"].get("total")) - neu_r
        desp = dec(m["despesas"].get("total")) - neu_d
        evt = soma_cats(m["receitas"]["categorias"], eventuais)
        if not m["provisionado"] and not m["atual"]:
            for k, c in m["receitas"]["categorias"].items():
                if normalizar_texto(k) not in neutras:
                    rec_fech_cat[k] += dec(c["valor"])
            for k, c in m["despesas"]["categorias"].items():
                if normalizar_texto(k) not in neutras:
                    desp_fech_cat[k] += dec(c["valor"])
        aporte = sum((dec(c["valor"]) for k, c in m["despesas"]["categorias"].items() if eh_invest(k)), D0)
        meses.append({"mes": m["mes"], "estado": "provisionado" if m["provisionado"] else "atual" if m["atual"] else "fechado",
                      "receitas": rec, "despesas": desp, "aporte": aporte, "consumo": desp - aporte, "eventuais": evt, "rec_recorrente": rec - evt,
                      "rec_fixas": dec(m["receitas"].get("fixas")), "desp_fixas": dec(m["despesas"].get("fixas")),
                      "saldo": dec(m.get("saldo_mes")), "acumulado": dec(m.get("saldo_acumulado"))})
    fech = [m for m in meses if m["estado"] == "fechado"]
    n = len(fech) or 1
    soma = {k: sum((m[k] for m in fech), D0) for k in ("receitas", "despesas", "consumo", "aporte", "desp_fixas", "rec_fixas", "saldo", "eventuais", "rec_recorrente")}
    media = {k: v / n for k, v in soma.items()}
    negativos = [m for m in meses if m["saldo"] < 0]
    metade = len(fech) // 2
    tend = (sum((m["saldo"] for m in fech[metade:]), D0) / max(len(fech) - metade, 1)
            - sum((m["saldo"] for m in fech[:metade]), D0) / max(metade, 1)) if len(fech) >= 2 else D0

    aplic = res.get("Valor de Aplicações do Saldo Atual", D0)
    banco = res.get("Saldo Bancário Atual", D0)
    ca = r.get("contas_em_aberto", {})
    receber, pagar = dec(ca.get("receber", {}).get("total")), dec(ca.get("pagar", {}).get("total"))
    atraso_rec = dec(ca.get("receber", {}).get("em_atraso", {}).get("valor"))
    atraso_pag = dec(ca.get("pagar", {}).get("em_atraso", {}).get("valor"))

    cartoes, compromisso, atrasadas = [], defaultdict(lambda: D0), []
    for c in r.get("cartoes", []):
        fats = [{**f, "valor": dec(f["valor"])} for f in c["faturas"]]
        for f in fats:
            if f["vencimento"]:
                compromisso[f["vencimento"][:7]] += f["valor"]
                if f["vencimento"] < a.hoje and f["valor"]:
                    atrasadas.append((c["nome"], f["vencimento"], f["valor"]))
        cartoes.append({"nome": c["nome"], "limite": dec(c.get("limite_total")), "utilizado": dec(c.get("limite_utilizado")),
                        "proxima": fats[0] if fats else None, "total": dec(c.get("faturas_total")), "n": len(fats),
                        "ultima_venc": fats[-1]["vencimento"] if fats else None})
    lim_total = sum((c["limite"] for c in cartoes), D0)
    usado = sum((c["utilizado"] for c in cartoes), D0)
    proximas = sum((c["proxima"]["valor"] for c in cartoes if c["proxima"]), D0)
    total_faturas = sum((c["total"] for c in cartoes), D0)
    folga = banco + receber - pagar - proximas

    desp_cat = {k: dec(v) for k, v in r["despesas_por_categoria"].items() if normalizar_texto(k) not in neutras}
    consumo_ano = sum((v for k, v in desp_cat.items() if not eh_invest(k)), D0)
    duvidas = [d for d in ler_csv(RAIZ / "dados" / "duvidas-categorias.csv") if not d["explicacao_cliente"].strip()]

    md = [f"# Indicadores · resumo do sistema ({r.get('ano')})", "",
          f"Gerado por `scripts/indicadores_resumo.py` em {a.data} a partir de `{r.get('fonte')}` (importado em {r.get('importado_em')}).",
          f"Médias sobre {len(fech)} meses fechados ({', '.join(m['mes'] for m in fech)}). Posição de contas e cartões em {a.hoje}.", ""]
    if neutras:
        md += [f"Categorias neutras (repasse), fora de receitas e despesas: {a.neutras}.", ""]
    if eventuais:
        md += [f"Receitas eventuais (não recorrentes): {a.eventuais}.", ""]
    if duvidas:
        md += [f"> **Atenção:** {len(duvidas)} categoria(s) em `dados/duvidas-categorias.csv` ainda sem explicação do cliente "
               "(Fluxo 3). A leitura dessas categorias é provisória.", ""]
    md += ["## Resumo", "", "| Indicador | Valor |", "|---|---|",
           f"| Receita média mensal | {brl(media['receitas'])} |",
           f"| Despesa média mensal (consumo, sem aportes) | {brl(media['consumo'])} |",
           f"| Despesa fixa média mensal | {brl(media['desp_fixas'])} |",
           f"| Aporte médio mensal (categoria Investimentos) | {brl(media['aporte'])} |",
           f"| Taxa de poupança (meses fechados) | {pct(soma['receitas'] - soma['consumo'], soma['receitas'])} |",
           *([f"| Receita recorrente média mensal (sem eventuais) | {brl(media['rec_recorrente'])} |",
              f"| Taxa de poupança só com receita recorrente | {pct(soma['rec_recorrente'] - soma['consumo'], soma['rec_recorrente'])} |"] if eventuais else []),
           f"| Despesa de consumo / receita | {pct(soma['consumo'], soma['receitas'])} |",
           f"| Despesas fixas / receita | {pct(soma['desp_fixas'], soma['receitas'])} |",
           f"| Receitas fixas / receita | {pct(soma['rec_fixas'], soma['receitas'])} |",
           f"| Meses com saldo negativo | {len(negativos)} ({', '.join(m['mes'] for m in negativos) or 'nenhum'}) |",
           f"| Tendência do saldo mensal (2ª metade − 1ª metade dos meses fechados) | {brl(tend)} |",
           f"| Saldo bancário atual | {brl(banco)} |",
           f"| Aplicações | {brl(aplic)} |",
           f"| Reserva em meses de despesa fixa | {(aplic / media['desp_fixas']):.1f}".replace(".", ",") + " |" if media["desp_fixas"] else "| Reserva em meses de despesa fixa | n/d |",
           f"| Reserva em meses de despesa total | {(aplic / media['consumo']):.1f}".replace(".", ",") + " |" if media["consumo"] else "| Reserva em meses de despesa total | n/d |",
           f"| Saldo acumulado final projetado pelo sistema | {brl(res.get('Saldo Acumulado Final', D0))} |", "",
           "## Por mês", "", "| Mês | Estado | Receitas | Despesas | Aportes | Fixas | Saldo (sistema) | Acumulado (sistema) |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    md += [f"| {m['mes']} | {m['estado']} | {brl(m['receitas'])} | {brl(m['despesas'])} | {brl(m['aporte'])} | {brl(m['desp_fixas'])} | "
           f"{'**' if m['saldo'] < 0 else ''}{brl(m['saldo'])}{'**' if m['saldo'] < 0 else ''} | {brl(m['acumulado'])} |" for m in meses]
    md += ["", "## Receitas por categoria nos meses fechados", "", "| Categoria | Total | Média mensal | Tipo |", "|---|---:|---:|---|"]
    md += [f"| {k} | {brl(v)} | {brl(v / n)} | {'eventual' if normalizar_texto(k) in eventuais else 'recorrente/anual'} |"
           for k, v in sorted(rec_fech_cat.items(), key=lambda x: x[1], reverse=True)]
    md += ["", "## Despesas por categoria nos meses fechados", "", "| Categoria | Total | Média mensal | Meses com lançamento |", "|---|---:|---:|---:|"]
    md += [f"| {k} | {brl(v)} | {brl(v / n)} | {sum(1 for m in r['meses'] if not m['provisionado'] and not m['atual'] and k in m['despesas']['categorias'])} |"
           for k, v in sorted(desp_fech_cat.items(), key=lambda x: x[1], reverse=True)]
    md += ["", "## Despesas por categoria no ano (realizado + provisionado)", "",
           "| Categoria | Total | % do consumo |", "|---|---:|---:|"]
    md += [f"| {k} | {brl(v)} | {'aporte' if eh_invest(k) else pct(v, consumo_ano)} |" for k, v in sorted(desp_cat.items(), key=lambda x: x[1], reverse=True)]
    md += ["", "## Contas em aberto", "", "| Item | Valor |", "|---|---:|",
           f"| A receber | {brl(receber)} (em atraso: {brl(atraso_rec)}) |", f"| A pagar | {brl(pagar)} (em atraso: {brl(atraso_pag)}) |",
           f"| Próximas faturas (1ª de cada cartão) | {brl(proximas)} |",
           f"| **Folga imediata** (banco + receber − pagar − próximas faturas) | **{brl(folga)}** |", "",
           "## Cartões", "", "| Cartão | Limite | Utilizado | % | Próxima fatura | Faturas em aberto | Última parcela |", "|---|---:|---:|---:|---|---:|---|"]
    for c in cartoes:
        prox = f"{brl(c['proxima']['valor'])} em {c['proxima']['vencimento']}" if c["proxima"] else "-"
        md.append(f"| {c['nome']} | {brl(c['limite'])} | {brl(c['utilizado'])} | {pct(c['utilizado'], c['limite'])} | {prox} | "
                  f"{brl(c['total'])} ({c['n']}) | {c['ultima_venc'] or '-'} |")
    md.append(f"| **Total** | {brl(lim_total)} | {brl(usado)} | {pct(usado, lim_total)} | {brl(proximas)} | {brl(total_faturas)} | |")
    md += ["", "### Compromisso já assumido nos cartões, por mês de vencimento", "", "| Mês | Valor | % da receita média |", "|---|---:|---:|"]
    md += [f"| {k} | {brl(v)} | {pct(v, media['receitas'])} |" for k, v in sorted(compromisso.items())]
    if atrasadas:
        md += ["", "### Faturas vencidas e ainda em aberto", ""] + [f"- {n_}: {brl(v)} (venc. {d})" for n_, d, v in atrasadas]
    md += ["", "Conferência: todos os valores vêm de `dados/resumo-sistema.json`, que passou no portão de `importar_resumo.py`."]

    ind = {"meses_fechados": [m["mes"] for m in fech], "media": {k: str(v) for k, v in media.items()},
           "soma_fechados": {k: str(v) for k, v in soma.items()}, "meses_negativos": [m["mes"] for m in negativos],
           "tendencia_saldo": str(tend), "neutras": a.neutras, "eventuais": a.eventuais,
           "receitas_fechados_por_categoria": {k: str(v) for k, v in rec_fech_cat.items()},
           "despesas_fechados_por_categoria": {k: str(v) for k, v in desp_fech_cat.items()}, "saldo_bancario": str(banco), "aplicacoes": str(aplic), "folga_imediata": str(folga),
           "a_receber": str(receber), "a_pagar": str(pagar), "atraso_receber": str(atraso_rec), "atraso_pagar": str(atraso_pag),
           "cartoes_limite": str(lim_total), "cartoes_utilizado": str(usado), "proximas_faturas": str(proximas),
           "faturas_total": str(total_faturas), "compromisso_por_mes": {k: str(v) for k, v in sorted(compromisso.items())},
           "faturas_atrasadas": [{"cartao": c, "vencimento": d, "valor": str(v)} for c, d, v in atrasadas],
           "saldo_acumulado_final": str(res.get("Saldo Acumulado Final", D0)), "duvidas_pendentes": len(duvidas)}
    a.saida.mkdir(parents=True, exist_ok=True)
    (a.saida / f"{a.data}-indicadores.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (a.saida / f"{a.data}-indicadores.json").write_text(json.dumps(ind, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Meses fechados: {len(fech)} | receita média {brl(media['receitas'])} | consumo médio {brl(media['consumo'])} | "
          f"poupança {pct(soma['receitas'] - soma['consumo'], soma['receitas'])} | cartões {brl(usado)} ({pct(usado, lim_total)}) | "
          f"folga imediata {brl(folga)}" + (f" | {len(atrasadas)} fatura(s) vencida(s)" if atrasadas else ""))
    print(f"Arquivos: {a.saida}/{a.data}-indicadores.md|json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
