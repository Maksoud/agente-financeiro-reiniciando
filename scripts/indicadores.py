"""Fluxo 4: calcula os indicadores do diagnóstico a partir de dados/lancamentos-categorizados.csv.

Uso:
  python scripts/indicadores.py [--saldo-anterior 0] [--data AAAA-MM-DD] [--fatura-como-despesa]

Saídas (data de hoje no nome, nunca sobrescreve outro dia):
  analise/AAAA-MM-DD-indicadores.md     tabelas para o relatório (nomes de terceiros anonimizados)
  analise/AAAA-MM-DD-indicadores.json   os mesmos números, para o Fluxo 5
  analise/AAAA-MM-DD-dados-para-analise.txt  bloco "DADOS FINANCEIROS" no formato de
                                        references/prompt-analise-anual.md

Regras de cálculo:
  - 'Transferência entre contas' e 'Pagamento de fatura' não contam como receita nem despesa.
  - ATENÇÃO cartão: com o extrato do cartão importado, o pagamento da fatura é neutro (os gastos
    já estão nos lançamentos do cartão). SEM o extrato do cartão, use --fatura-como-despesa: a fatura
    vira a despesa 'Cartão de crédito (sem detalhe)', senão a despesa fica subestimada.
  - 'Investimentos': saída = aporte (poupança), entrada = resgate. Ficam fora de receita/despesa.
  - Sem categoria → 'Não classificado' (o portão do Fluxo 3 garante que só sobram valores pequenos).
  - Fixa/variável: usa o tipo da regra; sem tipo, é 'fixa' se a mesma descrição aparece em 3+ meses
    com valor até 15% da mediana (recorrência).
  - Taxa de poupança = (receitas - despesas) / receitas.
Portão: o script confere que categorias somam o total de cada mês e que tudo fecha com a soma
bruta dos lançamentos. Se não fechar, sai com código 1 e não grava nada.
"""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from comum import (CATEGORIA_INVESTIMENTO, CATEGORIAS_NEUTRAS, RAIZ, Anonimizador, brl,
                   chave_recorrencia, ler_csv)

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
         "Setembro", "Outubro", "Novembro", "Dezembro"]
D0 = Decimal(0)


def detectar_recorrencias(lancs: list[dict]) -> dict[str, dict]:
    grupos = defaultdict(list)
    for l in lancs:
        grupos[(chave_recorrencia(l["descricao"]), Decimal(l["valor"]) > 0)].append(l)
    rec = {}
    for (chave, _), itens in grupos.items():
        meses = {i["data"][:7] for i in itens}
        if len(meses) < 3 or not chave:
            continue
        valores = [abs(Decimal(i["valor"])) for i in itens]
        mediana = Decimal(str(statistics.median(valores)))
        if mediana and all(abs(v - mediana) <= mediana * Decimal("0.15") for v in valores):
            for i in itens:
                rec[i["id"]] = {"chave": chave, "meses": len(meses), "mediana": mediana}
    return rec


def pct(a: Decimal, b: Decimal) -> str:
    return f"{(a / b * 100):.1f}%".replace(".", ",") if b else "n/d"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entrada", type=Path, default=RAIZ / "dados" / "lancamentos-categorizados.csv")
    p.add_argument("--saldo-anterior", default="0", help="saldo acumulado antes do primeiro mês")
    p.add_argument("--data", default=f"{date.today():%Y-%m-%d}", help="data usada no nome dos arquivos")
    p.add_argument("--saida", type=Path, default=RAIZ / "analise")
    p.add_argument("--fatura-como-despesa", action="store_true",
                   help="conta o pagamento de fatura como despesa (use quando o extrato do cartão NÃO foi importado)")
    a = p.parse_args()

    lancs = ler_csv(a.entrada)
    if not lancs:
        sys.exit("Sem lançamentos categorizados. Rode o Fluxo 3 primeiro.")
    rec = detectar_recorrencias(lancs)
    anon = Anonimizador()

    mes = defaultdict(lambda: {"rec": defaultdict(lambda: D0), "desp": defaultdict(lambda: D0),
                               "rec_fixa": D0, "desp_fixa": D0, "aporte": D0, "resgate": D0, "neutro": D0})
    bruto = D0
    fatura_total = [D0]
    for l in lancs:
        v = Decimal(l["valor"])
        bruto += v
        m = mes[l["data"][:7]]
        cat = l.get("categoria") or "Não classificado"
        if cat == "Pagamento de fatura":
            fatura_total[0] += -v
            if a.fatura_como_despesa:
                cat = "Cartão de crédito (sem detalhe)"
        if cat in CATEGORIAS_NEUTRAS:
            m["neutro"] += v
            continue
        if cat == CATEGORIA_INVESTIMENTO:
            m["aporte" if v < 0 else "resgate"] += abs(v)
            continue
        tipo = l.get("tipo") or ("fixa" if l["id"] in rec else "variavel")
        if cat == "Cartão de crédito (sem detalhe)":
            tipo = "variavel"  # fatura mistura gastos fixos e variáveis; sem detalhe, não conta como fixa
        if v > 0:
            m["rec"][cat] += v
            m["rec_fixa"] += v if tipo == "fixa" else D0
        else:
            m["desp"][cat] += -v
            m["desp_fixa"] += -v if tipo == "fixa" else D0

    # --- Totais e conferência -------------------------------------------------
    acumulado = Decimal(a.saldo_anterior.replace(".", "").replace(",", ".")) if "," in a.saldo_anterior else Decimal(a.saldo_anterior)
    saldo_anterior = acumulado
    linhas_mes, tot = [], defaultdict(lambda: D0)
    tot_cat_rec, tot_cat_desp = defaultdict(lambda: D0), defaultdict(lambda: D0)
    conferencia = D0
    for chave in sorted(mes):
        m = mes[chave]
        r, d = sum(m["rec"].values(), D0), sum(m["desp"].values(), D0)
        saldo = r - d
        acumulado += saldo
        conferencia += saldo + m["neutro"] + m["resgate"] - m["aporte"]
        for c, v in m["rec"].items():
            tot_cat_rec[c] += v
        for c, v in m["desp"].items():
            tot_cat_desp[c] += v
        for k, v in (("rec", r), ("desp", d), ("rec_fixa", m["rec_fixa"]), ("desp_fixa", m["desp_fixa"]),
                     ("aporte", m["aporte"]), ("resgate", m["resgate"]), ("neutro", m["neutro"])):
            tot[k] += v
        linhas_mes.append({"mes": chave, "receitas": r, "receitas_fixas": m["rec_fixa"], "despesas": d,
                           "despesas_fixas": m["desp_fixa"], "saldo": saldo, "acumulado": acumulado,
                           "aportes": m["aporte"], "resgates": m["resgate"], "neutros": m["neutro"],
                           "rec_cat": dict(m["rec"]), "desp_cat": dict(m["desp"])})

    if abs(conferencia - bruto) > Decimal("0.01") or sum(tot_cat_desp.values(), D0) != tot["desp"]:
        print(f"PORTÃO REPROVADO: decomposição ({brl(conferencia)}) não fecha com a soma bruta ({brl(bruto)}).")
        return 1

    receitas, despesas = tot["rec"], tot["desp"]
    n_meses = len(linhas_mes)
    ind = {
        "periodo": [linhas_mes[0]["mes"], linhas_mes[-1]["mes"]], "meses": n_meses,
        "receitas": receitas, "despesas": despesas, "saldo": receitas - despesas,
        "receitas_fixas": tot["rec_fixa"], "despesas_fixas": tot["desp_fixa"],
        "aportes": tot["aporte"], "resgates": tot["resgate"],
        "taxa_poupanca": pct(receitas - despesas, receitas),
        "despesa_sobre_receita": pct(despesas, receitas),
        "fixas_sobre_receita": pct(tot["desp_fixa"], receitas),
        "receita_media_mensal": receitas / n_meses, "despesa_media_mensal": despesas / n_meses,
        "despesa_fixa_media_mensal": tot["desp_fixa"] / n_meses,
        "juros_e_encargos": tot_cat_desp.get("Juros e encargos", D0),
        "nao_classificado": tot_cat_desp.get("Não classificado", D0) + tot_cat_rec.get("Não classificado", D0),
    }

    # Recorrências (anonimizadas)
    vistos = {}
    for l in lancs:
        if l["id"] in rec and Decimal(l["valor"]) < 0 and (l.get("categoria") or "") not in CATEGORIAS_NEUTRAS | {CATEGORIA_INVESTIMENTO}:
            k = rec[l["id"]]["chave"]
            vistos.setdefault(k, {"descricao": anon(l["descricao"]), "meses": rec[l["id"]]["meses"],
                                  "valor_tipico": rec[l["id"]]["mediana"], "categoria": l.get("categoria") or "Não classificado"})
    recorrencias = sorted(vistos.values(), key=lambda x: x["valor_tipico"], reverse=True)
    maiores = sorted((l for l in lancs if Decimal(l["valor"]) < 0 and (l.get("categoria") or "") not in CATEGORIAS_NEUTRAS | {CATEGORIA_INVESTIMENTO}),
                     key=lambda l: Decimal(l["valor"]))[:10]

    # --- Markdown ----------------------------------------------------------------
    md = [f"# Indicadores ({ind['periodo'][0]} a {ind['periodo'][1]})", "",
          f"Gerado por `scripts/indicadores.py` em {a.data} a partir de `{a.entrada.name}` ({len(lancs)} lançamentos).",
          "Todos os números abaixo vêm deste script. Nomes de terceiros anonimizados.", "",
          "## Resumo", "", "| Indicador | Valor |", "|---|---|"]
    for rot, k in (("Receitas", "receitas"), ("Despesas", "despesas"), ("Saldo do período", "saldo"),
                   ("Receita média mensal", "receita_media_mensal"), ("Despesa média mensal", "despesa_media_mensal"),
                   ("Despesa fixa média mensal", "despesa_fixa_media_mensal"), ("Aportes em investimentos", "aportes"),
                   ("Resgates", "resgates"), ("Juros e encargos pagos", "juros_e_encargos"), ("Não classificado", "nao_classificado")):
        md.append(f"| {rot} | {brl(ind[k])} |")
    md += [f"| Taxa de poupança | {ind['taxa_poupanca']} |", f"| Despesa / receita | {ind['despesa_sobre_receita']} |",
           f"| Despesas fixas / receita | {ind['fixas_sobre_receita']} |", "",
           "## Por mês", "", "| Mês | Receitas | Despesas | Fixas | Saldo | Acumulado | Aportes |", "|---|---:|---:|---:|---:|---:|---:|"]
    for lm in linhas_mes:
        md.append(f"| {lm['mes']} | {brl(lm['receitas'])} | {brl(lm['despesas'])} | {brl(lm['despesas_fixas'])} | "
                  f"{brl(lm['saldo'])} | {brl(lm['acumulado'])} | {brl(lm['aportes'])} |")
    md += ["", "## Despesas por categoria", "", "| Categoria | Total | % das despesas | Média/mês |", "|---|---:|---:|---:|"]
    for c, v in sorted(tot_cat_desp.items(), key=lambda x: x[1], reverse=True):
        md.append(f"| {c} | {brl(v)} | {pct(v, despesas)} | {brl(v / n_meses)} |")
    md += ["", "## Receitas por categoria", "", "| Categoria | Total | % |", "|---|---:|---:|"]
    for c, v in sorted(tot_cat_rec.items(), key=lambda x: x[1], reverse=True):
        md.append(f"| {c} | {brl(v)} | {pct(v, receitas)} |")
    md += ["", "## Gastos recorrentes detectados", "", "| Descrição | Categoria | Meses | Valor típico |", "|---|---|---:|---:|"]
    md += [f"| {r['descricao']} | {r['categoria']} | {r['meses']} | {brl(r['valor_tipico'])} |" for r in recorrencias] or ["| (nenhum) | | | |"]
    md += ["", "## 10 maiores despesas", "", "| Data | Descrição | Categoria | Valor |", "|---|---|---|---:|"]
    md += [f"| {l['data']} | {anon(l['descricao'])} | {l.get('categoria') or 'Não classificado'} | {brl(-Decimal(l['valor']))} |" for l in maiores]
    if fatura_total[0] and not a.fatura_como_despesa:
        md += ["", f"> **Atenção:** {brl(fatura_total[0])} em pagamentos de fatura foram tratados como neutros. "
               "Se o extrato do cartão não foi importado, a despesa está subestimada: rode com `--fatura-como-despesa`."]
    md += ["", f"Conferência: decomposição = soma bruta dos lançamentos ({brl(bruto)}). OK."]

    # --- Bloco no formato do prompt de análise anual -----------------------------
    txt = ["Análise Financeira", ""]
    for lm in linhas_mes:
        ano, nm = lm["mes"].split("-")
        txt += [f"Mês: {MESES[int(nm) - 1]}/{ano}", f"Receitas Totais: {brl(lm['receitas'])}",
                f"Receitas Fixas: {brl(lm['receitas_fixas'])}", f"Receitas Variáveis: {brl(lm['receitas'] - lm['receitas_fixas'])}",
                "Receitas por Categoria:"]
        txt += [f"- {c}: {brl(v)}" for c, v in sorted(lm["rec_cat"].items(), key=lambda x: x[1], reverse=True)]
        txt += [f"Despesas Totais: {brl(lm['despesas'])}", f"Despesas Fixas: {brl(lm['despesas_fixas'])}",
                f"Despesas Variáveis: {brl(lm['despesas'] - lm['despesas_fixas'])}", "Despesas por Categoria:"]
        txt += [f"- {c}: {brl(v)}" for c, v in sorted(lm["desp_cat"].items(), key=lambda x: x[1], reverse=True)]
        txt += [f"Aportes em Investimentos: {brl(lm['aportes'])}", f"Saldo do mês: {brl(lm['saldo'])}",
                f"Saldo acumulado: {brl(lm['acumulado'])}", "", "-------------", ""]
    txt += ["Resumo do Período:", f"Saldo Anterior: {brl(saldo_anterior)}",
            f"Total de Receitas: {brl(receitas)}", f"Total de Receitas Fixas: {brl(tot['rec_fixa'])}",
            f"Total de Receitas Variáveis: {brl(receitas - tot['rec_fixa'])}", f"Total de Despesas: {brl(despesas)}",
            f"Total de Despesas Fixas: {brl(tot['desp_fixa'])}", f"Total de Despesas Variáveis: {brl(despesas - tot['desp_fixa'])}",
            f"Total de Aportes: {brl(tot['aporte'])} | Resgates: {brl(tot['resgate'])}",
            f"Saldo Acumulado Final: {brl(acumulado)}", "", "Despesas Totais por Categoria no Período:"]
    txt += [f"- {c}: {brl(v)}" for c, v in sorted(tot_cat_desp.items(), key=lambda x: x[1], reverse=True)]

    a.saida.mkdir(parents=True, exist_ok=True)
    base = a.saida / f"{a.data}-indicadores"
    (a.saida / f"{a.data}-indicadores.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (a.saida / f"{a.data}-dados-para-analise.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    serial = {**{k: (str(v) if isinstance(v, Decimal) else v) for k, v in ind.items()},
              "por_mes": [{k: (str(v) if isinstance(v, Decimal) else {c: str(x) for c, x in v.items()} if isinstance(v, dict) else v)
                           for k, v in lm.items()} for lm in linhas_mes],
              "despesas_por_categoria": {c: str(v) for c, v in tot_cat_desp.items()},
              "receitas_por_categoria": {c: str(v) for c, v in tot_cat_rec.items()},
              "recorrencias": [{**r, "valor_tipico": str(r["valor_tipico"])} for r in recorrencias]}
    base.with_suffix(".json").write_text(json.dumps(serial, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Período {ind['periodo'][0]} a {ind['periodo'][1]} ({n_meses} meses) | receitas {brl(receitas)} | "
          f"despesas {brl(despesas)} | poupança {ind['taxa_poupanca']} | fixas/receita {ind['fixas_sobre_receita']}")
    if fatura_total[0] and not a.fatura_como_despesa:
        print(f"ATENÇÃO: {brl(fatura_total[0])} em faturas tratados como neutros. Sem extrato do cartão importado, "
              "rode de novo com --fatura-como-despesa.")
    print(f"PORTÃO OK: conferência fechou. Arquivos em {a.saida}/{a.data}-indicadores.(md|json) e -dados-para-analise.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
