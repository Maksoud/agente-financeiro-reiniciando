"""Fluxo 3: aplica regras fixas de categorização ANTES de qualquer sugestão do LLM.

Ordem das regras (a primeira que casar vence):
  1. dados/regras-aprendidas.csv   ← confirmações do cliente (privado, não publicado)
  2. references/regras-categorizacao.csv ← regras genéricas do agente
Formato das regras: padrao;categoria;tipo;observacao
  - padrao: trecho da descrição (sem acento, maiúsculas). Começando com 're:' é expressão regular.
  - tipo: fixa | variavel | (vazio = decidido no diagnóstico pela recorrência)

Uso:
  python scripts/categorizar_regras.py aplicar [--limite 100]
  python scripts/categorizar_regras.py aprender "PADRAO" "Categoria" [--tipo fixa] [--obs "confirmado em 2026-11-02"]
  python scripts/categorizar_regras.py verificar [--limite 100]

Saídas de 'aplicar':
  dados/lancamentos-categorizados.csv  (status: ok | duvida | pendente)
  dados/duvidas.csv  lançamentos sem regra, do maior para o menor valor, com coluna 'sugestao'
                     vazia para o agente preencher e o CLIENTE confirmar.
Lançamentos já confirmados (regra=cliente:...) nunca são reclassificados.

Portão ('verificar'): nenhum lançamento com |valor| >= limite sem categoria. Código 1 se reprovar.
"""
import argparse
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from comum import CAMPOS_CATEGORIZADOS, RAIZ, brl, gravar_csv, ler_csv, normalizar_texto

DADOS = RAIZ / "dados"
REGRAS_GERAIS = RAIZ / "references" / "regras-categorizacao.csv"
REGRAS_CLIENTE = DADOS / "regras-aprendidas.csv"
CAMPOS_REGRA = ["padrao", "categoria", "tipo", "observacao"]


def carregar_regras() -> list[dict]:
    regras = []
    for origem, caminho in (("cliente", REGRAS_CLIENTE), ("geral", REGRAS_GERAIS)):
        for n, r in enumerate(ler_csv(caminho), start=2):
            pad = (r.get("padrao") or "").strip()
            if not pad or pad.startswith("#"):
                continue
            if pad.startswith("re:"):
                casa = re.compile(pad[3:], re.I).search
            else:
                alvo = normalizar_texto(pad)
                casa = lambda t, alvo=alvo: alvo in t  # noqa: E731
            regras.append({**r, "casa": casa, "id": f"{origem}:{caminho.name}:{n}"})
    return regras


def aplicar(limite: Decimal) -> int:
    base = ler_csv(DADOS / "lancamentos.csv")
    if not base:
        sys.exit("dados/lancamentos.csv vazio. Rode o Fluxo 1 (importar_extrato.py) primeiro.")
    anteriores = {l["id"]: l for l in ler_csv(DADOS / "lancamentos-categorizados.csv")}
    regras = carregar_regras()

    saida, duvidas = [], []
    for l in base:
        ant = anteriores.get(l["id"])
        if ant and ant.get("regra", "").startswith("cliente:"):
            saida.append(ant)  # confirmado pelo cliente: não mexer
            continue
        t = normalizar_texto(l["descricao"])
        regra = next((r for r in regras if r["casa"](t)), None)
        if regra:
            saida.append({**l, "categoria": regra["categoria"], "tipo": regra.get("tipo", ""),
                          "regra": regra["id"], "status": "ok"})
        else:
            grande = abs(Decimal(l["valor"])) >= limite
            linha = {**l, "categoria": "", "tipo": "", "regra": "", "status": "duvida" if grande else "pendente"}
            saida.append(linha)
            duvidas.append({**linha, "sugestao": "", "motivo_sugestao": "", "confirmado": ""})

    duvidas.sort(key=lambda d: abs(Decimal(d["valor"])), reverse=True)
    gravar_csv(DADOS / "lancamentos-categorizados.csv", saida, CAMPOS_CATEGORIZADOS)
    gravar_csv(DADOS / "duvidas.csv", duvidas,
               ["id", "data", "descricao", "valor", "conta", "status", "sugestao", "motivo_sugestao", "confirmado"])

    ok = sum(1 for s in saida if s["status"] == "ok")
    acima = sum(1 for d in duvidas if d["status"] == "duvida")
    print(f"Lançamentos: {len(saida)} | categorizados por regra: {ok} | sem regra: {len(duvidas)} "
          f"(acima de {brl(limite)}: {acima})")
    print("Dúvidas em dados/duvidas.csv (maiores primeiro). O agente SUGERE; o cliente CONFIRMA.")
    return 0


def aprender(padrao: str, categoria: str, tipo: str, obs: str) -> int:
    regras = ler_csv(REGRAS_CLIENTE)
    alvo = normalizar_texto(padrao) if not padrao.startswith("re:") else padrao
    if any((r["padrao"] if r["padrao"].startswith("re:") else normalizar_texto(r["padrao"])) == alvo for r in regras):
        sys.exit(f"Já existe regra para {padrao!r} em {REGRAS_CLIENTE.name}. Edite o arquivo se quiser mudar.")
    regras.insert(0, {"padrao": alvo, "categoria": categoria, "tipo": tipo,
                      "observacao": obs or f"confirmado pelo cliente em {date.today():%Y-%m-%d}"})
    gravar_csv(REGRAS_CLIENTE, regras, CAMPOS_REGRA)

    # Marca como confirmados pelo cliente os lançamentos que casam com a nova regra
    cat = DADOS / "lancamentos-categorizados.csv"
    linhas = ler_csv(cat)
    casa = re.compile(alvo[3:], re.I).search if alvo.startswith("re:") else (lambda t: alvo in t)
    n = 0
    for l in linhas:
        if casa(normalizar_texto(l["descricao"])) and not l.get("regra", "").startswith("cliente:"):
            l.update(categoria=categoria, tipo=tipo, regra=f"cliente:{REGRAS_CLIENTE.name}:1", status="ok")
            n += 1
    if linhas:
        gravar_csv(cat, linhas, CAMPOS_CATEGORIZADOS)
    print(f"Regra salva: {alvo!r} → {categoria} ({tipo or 'tipo pela recorrência'}). Lançamentos atualizados: {n}.")
    print("Rode 'aplicar' de novo para recalcular dados/duvidas.csv.")
    return 0


def verificar(limite: Decimal) -> int:
    linhas = ler_csv(DADOS / "lancamentos-categorizados.csv")
    if not linhas:
        sys.exit("Rode 'aplicar' primeiro.")
    faltando = [l for l in linhas if not l["categoria"] and abs(Decimal(l["valor"])) >= limite]
    pequenos = [l for l in linhas if not l["categoria"] and abs(Decimal(l["valor"])) < limite]
    soma_peq = sum((abs(Decimal(l["valor"])) for l in pequenos), Decimal(0))
    print(f"Sem categoria abaixo de {brl(limite)}: {len(pequenos)} (total {brl(soma_peq)}) → entram como 'Não classificado'.")
    if faltando:
        print(f"PORTÃO REPROVADO: {len(faltando)} lançamento(s) de {brl(limite)} ou mais sem categoria:")
        for l in faltando[:20]:
            print(f"  {l['data']}  {brl(l['valor']):>14}  {l['descricao']}")
        return 1
    print("PORTÃO OK: nenhum lançamento acima do limite sem categoria.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for nome in ("aplicar", "verificar"):
        s = sub.add_parser(nome)
        s.add_argument("--limite", default="100", help="valor X do portão (padrão R$ 100)")
    s = sub.add_parser("aprender")
    s.add_argument("padrao")
    s.add_argument("categoria")
    s.add_argument("--tipo", default="", choices=["", "fixa", "variavel"])
    s.add_argument("--obs", default="")
    a = p.parse_args()
    if a.cmd == "aplicar":
        return aplicar(Decimal(a.limite.replace(",", ".")))
    if a.cmd == "verificar":
        return verificar(Decimal(a.limite.replace(",", ".")))
    return aprender(a.padrao, a.categoria, a.tipo, a.obs)


if __name__ == "__main__":
    sys.exit(main())
