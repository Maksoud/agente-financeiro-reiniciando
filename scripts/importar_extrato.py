"""Fluxo 1: converte extrato CSV ou OFX para o formato padrão e confere o saldo.

Uso:
    python scripts/importar_extrato.py entrada/extrato.csv --conta "Banco X CC" \
        --saldo-inicial 1500,00 --saldo-final 980,35
    python scripts/importar_extrato.py entrada/extrato.ofx --conta "Banco X CC" --saldo-inicial 1500,00

Portão: saldo inicial + soma dos lançamentos = saldo final (tolerância R$ 0,01).
- OFX: o saldo final vem do próprio arquivo (LEDGERBAL), se não for informado.
- Sem saldos, o script importa mas avisa que o portão NÃO foi cumprido (código de saída 2).
- Lançamentos já importados (mesmo id) não são duplicados.

PDF: não é lido aqui. Peça ao cliente o CSV/OFX do banco; se só houver PDF, transcreva
para CSV no formato data;descricao;valor e rode este script sobre o CSV.
"""
import argparse
import csv
import io
import re
import sys
from decimal import Decimal
from pathlib import Path

from comum import CAMPOS_PADRAO, RAIZ, brl, gerar_id, gravar_csv, ler_csv, ler_data, ler_valor, normalizar_texto

NOMES_DATA = {"DATA", "DATA LANCAMENTO", "DATA DO LANCAMENTO", "DT", "DATE", "DATA MOVIMENTO"}
NOMES_DESC = {"DESCRICAO", "HISTORICO", "LANCAMENTO", "DESCRIPTION", "MEMO", "TITULO", "ESTABELECIMENTO", "DETALHES"}
NOMES_VALOR = {"VALOR", "VALOR (R$)", "AMOUNT", "QUANTIA", "VALOR R$"}
NOMES_CREDITO = {"CREDITO", "ENTRADA", "ENTRADAS", "CREDITO (R$)"}
NOMES_DEBITO = {"DEBITO", "SAIDA", "SAIDAS", "DEBITO (R$)"}


def _achar(cabecalho: list[str], nomes: set[str]) -> int | None:
    for i, c in enumerate(cabecalho):
        if normalizar_texto(c) in nomes:
            return i
    return None


def ler_csv_banco(caminho: Path) -> list[tuple[str, str, Decimal]]:
    bruto = caminho.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = bruto.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    dialeto = csv.Sniffer().sniff(texto[:4096], delimiters=";,\t")
    linhas = list(csv.reader(io.StringIO(texto), dialeto))

    # Procura a linha de cabeçalho (bancos às vezes colocam linhas de título antes)
    for n, linha in enumerate(linhas[:20]):
        i_data, i_desc = _achar(linha, NOMES_DATA), _achar(linha, NOMES_DESC)
        i_val, i_cred, i_deb = _achar(linha, NOMES_VALOR), _achar(linha, NOMES_CREDITO), _achar(linha, NOMES_DEBITO)
        if i_data is not None and i_desc is not None and (i_val is not None or (i_cred is not None and i_deb is not None)):
            break
    else:
        sys.exit("Cabeçalho não reconhecido. Colunas esperadas: data, descrição/histórico e valor "
                 "(ou crédito e débito). Ajuste o cabeçalho do CSV ou acrescente o nome em NOMES_* deste script.")

    saida = []
    for linha in linhas[n + 1:]:
        if not linha or not any(c.strip() for c in linha):
            continue
        desc = linha[i_desc].strip()
        if normalizar_texto(desc).startswith(("SALDO", "S A L D O")):
            continue  # linhas de saldo do extrato não são lançamentos
        try:
            data = ler_data(linha[i_data])
        except ValueError:
            continue
        if i_val is not None:
            valor = ler_valor(linha[i_val])
        else:
            cred = linha[i_cred].strip()
            deb = linha[i_deb].strip()
            valor = (ler_valor(cred) if cred else Decimal(0)) - (abs(ler_valor(deb)) if deb else Decimal(0))
        saida.append((data, desc, valor))
    return saida, None


def ler_ofx(caminho: Path) -> tuple[list[tuple[str, str, Decimal]], Decimal | None]:
    texto = caminho.read_bytes().decode("latin-1")

    def tag(bloco: str, nome: str) -> str | None:
        m = re.search(rf"<{nome}>\s*([^<\r\n]+)", bloco, re.I)
        return m.group(1).strip() if m else None

    saida = []
    for bloco in re.findall(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|(?=</BANKTRANLIST>))", texto, re.S | re.I):
        valor = ler_valor(tag(bloco, "TRNAMT"))
        desc = tag(bloco, "MEMO") or tag(bloco, "NAME") or ""
        saida.append((ler_data(tag(bloco, "DTPOSTED")), desc, valor))
    m = re.search(r"<LEDGERBAL>.*?<BALAMT>\s*([^<\r\n]+)", texto, re.S | re.I)
    return saida, (ler_valor(m.group(1)) if m else None)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("arquivo", type=Path)
    p.add_argument("--conta", required=True, help="nome da conta/cartão (ex.: 'Banco X CC')")
    p.add_argument("--saldo-inicial", help="saldo antes do primeiro lançamento do arquivo")
    p.add_argument("--saldo-final", help="saldo após o último lançamento (OFX: lido do arquivo)")
    p.add_argument("--saida", type=Path, default=RAIZ / "dados" / "lancamentos.csv")
    a = p.parse_args()

    if a.arquivo.suffix.lower() == ".ofx":
        lancs, saldo_ofx = ler_ofx(a.arquivo)
    elif a.arquivo.suffix.lower() in (".csv", ".txt"):
        lancs, saldo_ofx = ler_csv_banco(a.arquivo)
    else:
        sys.exit("Formato não suportado aqui (só CSV/OFX). Veja a docstring para PDF.")

    if not lancs:
        sys.exit("Nenhum lançamento encontrado no arquivo.")

    existentes = ler_csv(a.saida)
    ids = {l["id"] for l in existentes}
    novos, repetidos, seq = [], 0, {}
    for data, desc, valor in sorted(lancs, key=lambda x: x[0]):
        k = (data, normalizar_texto(desc), valor)
        seq[k] = seq.get(k, 0) + 1  # dois lançamentos idênticos no mesmo dia são legítimos
        lid = gerar_id(a.conta, data, desc, valor, seq[k])
        if lid in ids:
            repetidos += 1
            continue
        novos.append({"id": lid, "data": data, "descricao": desc, "valor": f"{valor:.2f}",
                      "conta": a.conta, "origem": a.arquivo.name})

    gravar_csv(a.saida, sorted(existentes + novos, key=lambda l: (l["data"], l["conta"])), CAMPOS_PADRAO)

    soma = sum((v for _, _, v in lancs), Decimal(0))
    entradas = sum((v for _, _, v in lancs if v > 0), Decimal(0))
    saidas = sum((v for _, _, v in lancs if v < 0), Decimal(0))
    print(f"Arquivo: {a.arquivo.name} | conta: {a.conta}")
    print(f"Período: {lancs[0][0] if lancs else '-'} a {max(l[0] for l in lancs)}")
    print(f"Lançamentos no arquivo: {len(lancs)} | novos: {len(novos)} | já importados: {repetidos}")
    print(f"Entradas: {brl(entradas)} | Saídas: {brl(saidas)} | Soma: {brl(soma)}")

    final = ler_valor(a.saldo_final) if a.saldo_final else saldo_ofx
    if a.saldo_inicial is None or final is None:
        print("PORTÃO NÃO CUMPRIDO: informe --saldo-inicial e --saldo-final (do extrato) para conferir a soma.")
        return 2
    inicial = ler_valor(a.saldo_inicial)
    calculado = inicial + soma
    diferenca = calculado - final
    print(f"Saldo inicial {brl(inicial)} + soma {brl(soma)} = {brl(calculado)} | saldo do extrato {brl(final)}")
    if abs(diferenca) > Decimal("0.01"):
        print(f"PORTÃO REPROVADO: diferença de {brl(diferenca)}. Verifique lançamentos faltando, "
              "linhas de saldo lidas como lançamento ou sinal invertido.")
        return 1
    print("PORTÃO OK: soma confere com o saldo do extrato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
