"""Fluxo 1 (entrada A): lê a exportação "Análise Financeira Anual" do sistema de controle
financeiro do cliente (layout em templates/layout-resumo-sistema.txt) e confere todas as somas.

Uso:
  python scripts/importar_resumo.py entrada/resumo-sistema-AAAA-MM-DD.txt [--ano 2026] [--limite 100]
  python scripts/importar_resumo.py --verificar-duvidas [--limite 100]

Saídas:
  dados/resumo-sistema.json        estrutura completa (meses, resumo, contas em aberto, cartões)
  dados/duvidas-categorias.csv     categorias genéricas ou do lado "errado" (receita/despesa) com
                                   valor >= limite no ano, para o cliente explicar (Fluxo 3)

Portão (código 0): em cada mês, categorias = total, fixas + variáveis = total, saldo = receitas -
despesas; saldo acumulado encadeado; totais do ano = soma dos meses (também por categoria);
realizado + provisionado = total; contas em aberto e cartões fecham. Código 1 = divergência.
'--verificar-duvidas': código 0 só se toda dúvida >= limite tiver explicação do cliente.
"""
import argparse
import json
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from comum import RAIZ, brl, gravar_csv, ler_csv, normalizar_texto

D0 = Decimal(0)
TOL = Decimal("0.01")
MESES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO",
         "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
NOMES_MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
               "Setembro", "Outubro", "Novembro", "Dezembro"]
RE_VALOR = re.compile(r"(-?)\s*R\$\s*(-?[\d.]+,\d{2})")
CATEGORIAS_GENERICAS = {"DIVERSOS", "DESPESAS DIVERSAS", "RECEITAS DIVERSAS", "OUTROS", "NAO IDENTIFICADO"}
SO_DESPESA = {"TAXAS E IMPOSTOS", "MANUT", "COMBUSTIVEIS", "ALIMENTACAO", "ESCOLA", "PET", "ENERGIA", "INTERNET", "CELULAR"}
SO_RECEITA = {"REEMBOLSAVEIS", "SALARIOS E QUINZENAS", "PLR", "RENDIMENTOS DE APLICACOES"}
DADOS = RAIZ / "dados"


def valor(linha: str) -> Decimal | None:
    m = RE_VALOR.search(linha)
    if not m:
        return None
    v = Decimal(m.group(2).replace(".", "").replace(",", "."))
    return -abs(v) if m.group(1) == "-" else v


def depois_dois_pontos(linha: str) -> str:
    return linha.split(":", 1)[1].strip() if ":" in linha else ""


def parse(texto: str) -> dict:
    r = {"meses": [], "resumo": {}, "receitas_por_categoria": {}, "despesas_por_categoria": {},
         "realizado": {}, "provisionado": {}, "contas_em_aberto": {}, "cartoes": [], "resumo_cartoes": {}}
    mes = cartao = None
    lista = None  # dicionário onde entram as linhas "- Categoria: R$"
    bloco_contas = None
    secao = None
    for bruta in texto.splitlines():
        linha = bruta.strip()
        n = normalizar_texto(linha)
        if not linha or set(linha) <= set("=-"):
            continue
        if n.startswith("MES:"):
            nome = normalizar_texto(depois_dois_pontos(linha)).split(" ")[0].split("/")[0]
            mes = {"mes": NOMES_MESES[MESES.index(nome)], "indice": MESES.index(nome) + 1, "atual": "MES ATUAL" in n,
                   "provisionado": False, "receitas": {"categorias": {}}, "despesas": {"categorias": {}}}
            r["meses"].append(mes)
            secao, lista, cartao = "mes", None, None
            continue
        if n.startswith("RESUMO DO ANO") or n.startswith("RESUMO DO PERIODO"):
            secao, lista, mes = "ano", None, None
            continue
        if n.startswith("CONTAS EM ABERTO"):
            secao, lista = "contas", None
            continue
        if n.startswith("CARTOES DE CREDITO"):
            secao, lista = "cartoes", None
            continue
        if n.startswith("RESUMO DOS CARTOES"):
            secao, lista, cartao = "resumo_cartoes", None, None
            continue

        v = valor(linha)
        prov = "(PROVISIONADO)" in n

        if secao == "mes":
            alvo = None
            for lado, rot in (("receitas", "RECEITAS"), ("despesas", "DESPESAS")):
                if n.startswith(f"{rot} TOTAIS"):
                    mes[lado]["total"] = v
                    mes["provisionado"] |= prov
                elif n.startswith(f"{rot} FIXAS"):
                    mes[lado]["fixas"] = v
                elif n.startswith(f"{rot} VARIAVEIS"):
                    mes[lado]["variaveis"] = v
                elif n.startswith(f"{rot} POR CATEGORIA"):
                    lista = mes[lado]["categorias"]
                else:
                    continue
                alvo = lado
                break
            if alvo:
                continue
            if n.startswith("SALDO DO MES"):
                mes["saldo_mes"], lista = v, None
            elif n.startswith("SALDO ACUMULADO"):
                mes["saldo_acumulado"] = v
            elif n.startswith("APORTES EM INVESTIMENTOS"):
                mes["aportes"] = v
            elif linha.startswith("-") and lista is not None and v is not None:
                lista[linha[1:].split(":")[0].strip()] = {"valor": v, "provisionado": prov}
            continue

        if secao == "ano":
            if n.startswith("RECEITAS TOTAIS POR CATEGORIA"):
                lista = r["receitas_por_categoria"]
            elif n.startswith("DESPESAS TOTAIS POR CATEGORIA"):
                lista = r["despesas_por_categoria"]
            elif n.startswith("DO TOTAL ACIMA"):
                chave = "realizado" if "REALIZADO" in n and "JA REALIZADO" in n else "provisionado"
                vals = [valor(p) for p in linha.split("|")]
                r[chave] = {"receitas": vals[0], "despesas": vals[1] if len(vals) > 1 else None,
                            "descricao": linha.split(":")[0]}
            elif linha.startswith("-") and lista is not None and v is not None:
                lista[linha[1:].split(":")[0].strip()] = v
            elif v is not None and ":" in linha:
                r["resumo"][linha.split(":")[0].strip()] = v
            continue

        if secao == "contas":
            if n.startswith("RECEITAS A RECEBER"):
                bloco_contas = r["contas_em_aberto"].setdefault("receber", {"total": v})
            elif n.startswith("DESPESAS A PAGAR"):
                bloco_contas = r["contas_em_aberto"].setdefault("pagar", {"total": v})
            elif n.startswith("SALDO LIQUIDO"):
                r["contas_em_aberto"]["saldo_liquido"] = v
            elif linha.startswith("-") and bloco_contas is not None:
                m = re.match(r"-\s*(.+?)\s*\((\d+)\)", linha)
                if m:
                    bloco_contas[normalizar_texto(m.group(1)).lower().replace(" ", "_")] = {"qtd": int(m.group(2)), "valor": v}
            continue

        if secao == "cartoes":
            if n.startswith("CARTAO:"):
                cartao = {"nome": depois_dois_pontos(linha), "faturas": []}
                r["cartoes"].append(cartao)
            elif cartao is None:
                continue
            elif "MELHOR DIA" in n:
                dias = re.findall(r"\d+", linha)
                cartao["melhor_dia"], cartao["dia_vencimento"] = (int(dias[0]), int(dias[1])) if len(dias) >= 2 else (None, None)
            elif "LIMITE TOTAL" in n:
                cartao["limite_total"] = v
            elif "LIMITE UTILIZADO" in n:
                cartao["limite_utilizado"] = v
            elif "LIMITE DISPONIVEL" in n:
                cartao["limite_disponivel"] = v
            elif "ULTIMA FATURA PAGA" in n:
                m = re.search(r"(\d{2}/\d{2}/\d{4})", linha)
                cartao["ultima_fatura"] = {"valor": v, "vencimento": m.group(1) if m else None}
            elif "FATURAS EM ABERTO" in n:
                cartao["faturas_total"] = v
            elif n.startswith(". VENCIMENTO") or n.startswith("VENCIMENTO"):
                m = re.search(r"(\d{2})/(\d{2})/(\d{4})", linha)
                q = re.search(r"\((\d+) lan", linha)
                cartao["faturas"].append({"vencimento": f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None,
                                          "valor": v, "lancamentos": int(q.group(1)) if q else None})
            continue

        if secao == "resumo_cartoes" and v is not None and linha.startswith("-"):
            r["resumo_cartoes"][linha[1:].split(":")[0].strip()] = v
    return r


def conferir(r: dict) -> tuple[list[str], list[str]]:
    erros, avisos = [], []

    def igual(a, b, msg):
        if a is None or b is None:
            avisos.append(f"Não foi possível conferir (valor ausente): {msg}")
        elif abs(a - b) > TOL:
            erros.append(f"{msg}: {brl(a)} ≠ {brl(b)} (diferença {brl(a - b)})")

    if not r["meses"]:
        erros.append("Nenhum bloco 'Mês:' encontrado. O arquivo segue templates/layout-resumo-sistema.txt?")
        return erros, avisos

    for m in r["meses"]:
        for lado in ("receitas", "despesas"):
            d = m[lado]
            soma = sum((c["valor"] for c in d["categorias"].values()), D0)
            igual(soma, d.get("total"), f"{m['mes']}: soma das categorias de {lado} × total")
            if d.get("fixas") is not None and d.get("variaveis") is not None:
                igual(d["fixas"] + d["variaveis"], d.get("total"), f"{m['mes']}: {lado} fixas + variáveis × total")
        if None not in (m["receitas"].get("total"), m["despesas"].get("total")):
            igual(m["receitas"]["total"] - m["despesas"]["total"], m.get("saldo_mes"), f"{m['mes']}: receitas - despesas × saldo do mês")

    anterior = r["resumo"].get("Saldo do Ano Anterior")
    primeiro = r["meses"][0]
    if None not in (primeiro.get("saldo_mes"), primeiro.get("saldo_acumulado")):
        base_com = (anterior or D0) + primeiro["saldo_mes"]
        if abs(base_com - primeiro["saldo_acumulado"]) <= TOL:
            r["acumulado_inclui_saldo_anterior"] = True
        elif abs(primeiro["saldo_mes"] - primeiro["saldo_acumulado"]) <= TOL:
            r["acumulado_inclui_saldo_anterior"] = False
            if anterior:
                avisos.append("Saldo acumulado começa do zero (não soma o Saldo do Ano Anterior).")
        else:
            erros.append(f"{primeiro['mes']}: saldo acumulado não bate com o saldo do mês (nem somando o ano anterior)")
    for a, b in zip(r["meses"], r["meses"][1:]):
        if None not in (a.get("saldo_acumulado"), b.get("saldo_mes"), b.get("saldo_acumulado")):
            igual(a["saldo_acumulado"] + b["saldo_mes"], b["saldo_acumulado"], f"{b['mes']}: acumulado anterior + saldo do mês × acumulado")

    res = r["resumo"]
    for rot, lado, campo in (("Total de Receitas", "receitas", "total"), ("Total de Despesas", "despesas", "total"),
                             ("Total de Receitas Fixas", "receitas", "fixas"), ("Total de Receitas Variáveis", "receitas", "variaveis"),
                             ("Total de Despesas Fixas", "despesas", "fixas"), ("Total de Despesas Variáveis", "despesas", "variaveis")):
        if rot in res:
            igual(sum((m[lado].get(campo) or D0 for m in r["meses"]), D0), res[rot], f"Ano: soma dos meses × {rot}")
    if "Saldo Acumulado Final" in res:
        igual(r["meses"][-1].get("saldo_acumulado"), res["Saldo Acumulado Final"], "Ano: acumulado do último mês × Saldo Acumulado Final")
    for k in ("receitas", "despesas"):
        if r["realizado"].get(k) is not None and r["provisionado"].get(k) is not None:
            igual(r["realizado"][k] + r["provisionado"][k], res.get(f"Total de {k.title()}"), f"Ano: realizado + provisionado × total de {k}")
    for lado, chave in (("receitas", "receitas_por_categoria"), ("despesas", "despesas_por_categoria")):
        for cat, total in r[chave].items():
            soma = sum((m[lado]["categorias"].get(cat, {}).get("valor", D0) for m in r["meses"]), D0)
            igual(soma, total, f"Ano: {lado} '{cat}' soma dos meses × total da categoria")

    ca = r["contas_em_aberto"]
    for k in ("receber", "pagar"):
        b = ca.get(k)
        if b:
            partes = [x["valor"] for nome, x in b.items() if nome != "total" and x.get("valor") is not None]
            igual(sum(partes, D0), b.get("total"), f"Contas a {k}: atraso + hoje + a vencer × total")
    if ca.get("receber") and ca.get("pagar") and "saldo_liquido" in ca:
        igual(ca["receber"]["total"] - ca["pagar"]["total"], ca["saldo_liquido"], "Contas em aberto: receber - pagar × saldo líquido")

    for c in r["cartoes"]:
        igual(sum((f["valor"] or D0 for f in c["faturas"]), D0), c.get("faturas_total"), f"Cartão {c['nome']}: soma das faturas × total em aberto")
        if None not in (c.get("limite_total"), c.get("limite_utilizado"), c.get("limite_disponivel")):
            igual(c["limite_total"] - c["limite_utilizado"], c["limite_disponivel"], f"Cartão {c['nome']}: limite total - utilizado × disponível")
        if None not in (c.get("limite_utilizado"), c.get("faturas_total")) and abs(c["limite_utilizado"] - c["faturas_total"]) > TOL:
            avisos.append(f"Cartão {c['nome']}: limite utilizado ({brl(c['limite_utilizado'])}) difere do total de faturas em aberto "
                          f"({brl(c['faturas_total'])}). Perguntar ao cliente (pagamento parcial, crédito na fatura?).")
    rc = r["resumo_cartoes"]
    if r["cartoes"] and rc:
        def achar(trecho):
            return next((v for k, v in rc.items() if trecho in normalizar_texto(k)), None)
        igual(sum((c.get("limite_total") or D0 for c in r["cartoes"]), D0), achar("LIMITE TOTAL"), "Cartões: soma dos limites × limite total")
        igual(sum((c.get("limite_utilizado") or D0 for c in r["cartoes"]), D0), achar("TOTAL UTILIZADO"), "Cartões: soma do utilizado × total utilizado")
        igual(sum((c["faturas"][0]["valor"] for c in r["cartoes"] if c["faturas"]), D0), achar("PROXIMAS FATURAS"), "Cartões: primeira fatura de cada × próximas faturas")
        igual(sum((c.get("faturas_total") or D0 for c in r["cartoes"]), D0), achar("TODAS AS FATURAS"), "Cartões: soma das faturas × total de todas as faturas")

    todos = [m[l].get("total") or D0 for m in r["meses"] for l in ("receitas", "despesas")]
    if not any(todos):
        avisos.append("Todos os totais mensais estão zerados (layout de exemplo?). As conferências passam, mas não há o que analisar.")
    return erros, avisos


def duvidas(r: dict, limite: Decimal) -> list[dict]:
    """Categorias que pedem explicação do cliente (Fluxo 3 no caminho do resumo)."""
    saida = []
    for lado, chave, contrario in (("receita", "receitas_por_categoria", SO_DESPESA), ("despesa", "despesas_por_categoria", SO_RECEITA)):
        for cat, v in r[chave].items():
            n = normalizar_texto(cat)
            motivo = None
            if n in CATEGORIAS_GENERICAS:
                motivo = "categoria genérica: o que entra aqui?"
            elif any(n.startswith(x) for x in contrario):
                motivo = f"categoria normalmente do outro lado, lançada como {lado} (estorno? reembolso? ajuste?)"
            if motivo and abs(v) >= limite:
                saida.append({"categoria": cat, "lado": lado, "valor_ano": f"{v:.2f}", "motivo": motivo, "explicacao_cliente": ""})
    return sorted(saida, key=lambda d: abs(Decimal(d["valor_ano"])), reverse=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("arquivo", type=Path, nargs="?")
    p.add_argument("--ano", type=int, default=date.today().year)
    p.add_argument("--limite", default="100")
    p.add_argument("--verificar-duvidas", action="store_true")
    p.add_argument("--saida", type=Path, default=DADOS)
    a = p.parse_args()
    limite = Decimal(a.limite.replace(",", "."))
    arq_duvidas = a.saida / "duvidas-categorias.csv"
    campos = ["categoria", "lado", "valor_ano", "motivo", "explicacao_cliente"]

    if a.verificar_duvidas:
        pend = [d for d in ler_csv(arq_duvidas) if abs(Decimal(d["valor_ano"])) >= limite and not d["explicacao_cliente"].strip()]
        for d in pend:
            print(f"  sem explicação: {d['categoria']} ({d['lado']}, {brl(d['valor_ano'])}): {d['motivo']}")
        print("PORTÃO OK: todas as categorias em dúvida foram explicadas." if not pend else f"PORTÃO REPROVADO: {len(pend)} pendente(s).")
        return 1 if pend else 0
    if not a.arquivo:
        p.error("informe o arquivo do resumo")

    r = parse(a.arquivo.read_text(encoding="utf-8-sig"))
    r["fonte"], r["ano"], r["importado_em"] = a.arquivo.name, a.ano, f"{date.today():%Y-%m-%d}"
    erros, avisos = conferir(r)

    prov = [m["mes"] for m in r["meses"] if m["provisionado"]]
    atual = next((m["mes"] for m in r["meses"] if m["atual"]), None)
    print(f"Arquivo: {a.arquivo.name} | meses: {len(r['meses'])} | mês atual: {atual or 'não indicado'} | "
          f"provisionados: {', '.join(prov) or 'nenhum'} | cartões: {len(r['cartoes'])}")
    for x in avisos:
        print(f"AVISO: {x}")
    if erros:
        print(f"PORTÃO REPROVADO: {len(erros)} divergência(s). Nada foi gravado.")
        for x in erros:
            print(f"  {x}")
        return 1

    a.saida.mkdir(parents=True, exist_ok=True)
    (a.saida / "resumo-sistema.json").write_text(json.dumps(r, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    anteriores = {d["categoria"] + d["lado"]: d["explicacao_cliente"] for d in ler_csv(arq_duvidas)}
    novas = duvidas(r, limite)
    for d in novas:
        d["explicacao_cliente"] = anteriores.get(d["categoria"] + d["lado"], "")
    gravar_csv(arq_duvidas, novas, campos)
    print(f"Categorias para o cliente explicar (>= {brl(limite)}): {len(novas)} → {arq_duvidas.name}")
    print("PORTÃO OK: todas as somas do resumo conferem. Gravado dados/resumo-sistema.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
