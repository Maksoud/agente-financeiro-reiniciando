"""Funções compartilhadas pelos scripts do agente financeiro.

Só biblioteca padrão. Formato padrão de lançamento (dados/lancamentos.csv, separador ';'):
    id;data;descricao;valor;conta;origem
- data: AAAA-MM-DD
- valor: decimal com ponto; positivo = entrada, negativo = saída
"""
import csv
import hashlib
import re
import sys
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Console do Windows usa cp1252 por padrão; força UTF-8 para acentos e símbolos.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS_PADRAO = ["id", "data", "descricao", "valor", "conta", "origem"]
CAMPOS_CATEGORIZADOS = CAMPOS_PADRAO + ["categoria", "tipo", "regra", "status"]

# Categorias que não são consumo nem renda (movimentação entre bolsos do próprio cliente)
CATEGORIAS_NEUTRAS = {"Transferência entre contas", "Pagamento de fatura"}
CATEGORIA_INVESTIMENTO = "Investimentos"


def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_texto(texto: str) -> str:
    """Maiúsculas, sem acento e com espaços simples. Usado para casar regras."""
    return re.sub(r"\s+", " ", sem_acento(texto or "")).strip().upper()


def chave_recorrencia(descricao: str) -> str:
    """Descrição sem números/datas, para agrupar lançamentos que se repetem."""
    t = normalizar_texto(descricao)
    t = re.sub(r"\d+[/\-.]?\d*", " ", t)
    t = re.sub(r"\b(PARC(ELA)?|\d+ ?DE ?\d+)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def ler_valor(texto: str) -> Decimal:
    """Aceita '1.234,56', '-1234.56', '1234,56 D', 'R$ 10,00', '(10,00)'."""
    t = (texto or "").strip().upper().replace("R$", "").replace(" ", "")
    if not t:
        raise ValueError("valor vazio")
    negativo = False
    if t.endswith("D"):
        negativo, t = True, t[:-1]
    elif t.endswith("C"):
        t = t[:-1]
    if t.startswith("(") and t.endswith(")"):
        negativo, t = True, t[1:-1]
    if t.startswith("-"):
        negativo, t = not negativo, t[1:]
    if "," in t:  # padrão brasileiro
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    try:
        v = Decimal(t)
    except InvalidOperation as e:
        raise ValueError(f"valor inválido: {texto!r}") from e
    return -v if negativo else v


def ler_data(texto: str) -> str:
    t = (texto or "").strip()
    # OFX: 20261102120000[-3:BRT] → usa só os 8 primeiros dígitos
    if re.match(r"^\d{8}", t):
        t = t[:8]
    else:
        t = t[:10]
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(t, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"data inválida: {texto!r}")


def gerar_id(conta: str, data: str, descricao: str, valor: Decimal, seq: int) -> str:
    base = f"{conta}|{data}|{normalizar_texto(descricao)}|{valor}|{seq}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]


def ler_csv(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def gravar_csv(caminho: Path, linhas: list[dict], campos: list[str]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)


def brl(valor) -> str:
    """Formata em R$ no padrão brasileiro."""
    v = Decimal(str(valor)).quantize(Decimal("0.01"))
    sinal = "-" if v < 0 else ""
    inteiro, dec = f"{abs(v):.2f}".split(".")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    return f"{sinal}R$ {inteiro},{dec}"


# --- Anonimização de terceiros (PIX, TED, DOC, transferências) ---------------
_PADRAO_TERCEIRO = re.compile(
    r"^(?P<prefixo>.*?\b(?:PIX|TED|DOC|TEF|TRANSF(?:ERENCIA)?)\b"
    r"(?:\s+(?:ENVIAD[OA]|RECEBID[OA]|EMITID[OA]|PARA|DE|QR\s*CODE|AGENDAD[OA]))*)"
    r"\s*[-:]?\s*(?P<nome>[A-Z][A-Z .'\-]{2,})$"
)


class Anonimizador:
    """Troca nomes de terceiros por [Pessoa N], sempre o mesmo N para o mesmo nome."""

    def __init__(self) -> None:
        self.mapa: dict[str, str] = {}

    def __call__(self, descricao: str) -> str:
        t = normalizar_texto(descricao)
        m = _PADRAO_TERCEIRO.match(t)
        if not m:
            return descricao
        nome = m.group("nome").strip()
        if nome not in self.mapa:
            self.mapa[nome] = f"[Pessoa {len(self.mapa) + 1}]"
        return f"{m.group('prefixo').strip()} {self.mapa[nome]}"
