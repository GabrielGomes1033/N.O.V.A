from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re


_UNIDADES = [
    "zero",
    "um",
    "dois",
    "tres",
    "quatro",
    "cinco",
    "seis",
    "sete",
    "oito",
    "nove",
]
_DEZ_A_DEZENOVE = {
    10: "dez",
    11: "onze",
    12: "doze",
    13: "treze",
    14: "quatorze",
    15: "quinze",
    16: "dezesseis",
    17: "dezessete",
    18: "dezoito",
    19: "dezenove",
}
_DEZENAS = {
    20: "vinte",
    30: "trinta",
    40: "quarenta",
    50: "cinquenta",
    60: "sessenta",
    70: "setenta",
    80: "oitenta",
    90: "noventa",
}
_CENTENAS = {
    100: "cem",
    200: "duzentos",
    300: "trezentos",
    400: "quatrocentos",
    500: "quinhentos",
    600: "seiscentos",
    700: "setecentos",
    800: "oitocentos",
    900: "novecentos",
}
_MESES = {
    1: "janeiro",
    2: "fevereiro",
    3: "marco",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}
_MOEDAS = {
    "BRL": ("real", "reais"),
    "USD": ("dolar", "dolares"),
    "EUR": ("euro", "euros"),
}
_PERIODOS = {
    "madrugada": "da madrugada",
    "manha": "da manha",
    "tarde": "da tarde",
    "noite": "da noite",
}


@dataclass(frozen=True)
class LugarTempo:
    hora: int
    minuto: int


def _juntar_partes(partes: list[str]) -> str:
    limpas = [p.strip() for p in partes if p and p.strip()]
    if not limpas:
        return ""
    if len(limpas) == 1:
        return limpas[0]
    return ", ".join(limpas[:-1]) + " e " + limpas[-1]


def numero_por_extenso(numero: int) -> str:
    if numero == 0:
        return _UNIDADES[0]
    if numero < 0:
        return "menos " + numero_por_extenso(abs(numero))
    if numero < 10:
        return _UNIDADES[numero]
    if numero < 20:
        return _DEZ_A_DEZENOVE[numero]
    if numero < 100:
        dezena = (numero // 10) * 10
        resto = numero % 10
        if resto == 0:
            return _DEZENAS[dezena]
        return f"{_DEZENAS[dezena]} e {numero_por_extenso(resto)}"
    if numero < 1000:
        if numero == 100:
            return _CENTENAS[100]
        centena = (numero // 100) * 100
        resto = numero % 100
        if centena == 100:
            prefixo = "cento"
        else:
            prefixo = _CENTENAS[centena]
        if resto == 0:
            return prefixo
        return f"{prefixo} e {numero_por_extenso(resto)}"

    escalas = (
        (10**12, "trilhao", "trilhoes"),
        (10**9, "bilhao", "bilhoes"),
        (10**6, "milhao", "milhoes"),
        (10**3, "mil", "mil"),
    )
    partes: list[str] = []
    restante = numero
    for divisor, singular, plural in escalas:
        quantidade = restante // divisor
        if not quantidade:
            continue
        restante %= divisor
        if divisor == 10**3:
            if quantidade == 1:
                partes.append("mil")
            else:
                partes.append(f"{numero_por_extenso(quantidade)} mil")
            continue
        nome = singular if quantidade == 1 else plural
        partes.append(f"{numero_por_extenso(quantidade)} {nome}")

    if restante:
        partes.append(numero_por_extenso(restante))

    return _juntar_partes(partes)


def numero_decimal_por_extenso(valor: Decimal) -> str:
    quantizado = valor.normalize()
    texto = format(quantizado, "f")
    if "." not in texto:
        return numero_por_extenso(int(quantizado))
    inteiro_txt, decimal_txt = texto.split(".", 1)
    decimal_txt = decimal_txt.rstrip("0")
    if not decimal_txt:
        return numero_por_extenso(int(quantizado))
    inteiro = int(inteiro_txt or "0")
    if len(decimal_txt) <= 2 and not decimal_txt.startswith("0"):
        decimal = numero_por_extenso(int(decimal_txt))
    else:
        decimal = " ".join(numero_por_extenso(int(ch)) for ch in decimal_txt)
    return f"{numero_por_extenso(inteiro)} virgula {decimal}"


def _parse_decimal_guess(texto: str) -> Decimal | None:
    bruto = (texto or "").strip()
    if not bruto:
        return None
    bruto = bruto.replace(" ", "")
    bruto = re.sub(r"[^0-9,.\-]", "", bruto)
    if not bruto:
        return None

    if "," in bruto and "." in bruto:
        decimal_sep = "," if bruto.rfind(",") > bruto.rfind(".") else "."
        thousands_sep = "." if decimal_sep == "," else ","
        bruto = bruto.replace(thousands_sep, "")
        bruto = bruto.replace(decimal_sep, ".")
    elif "," in bruto:
        if re.search(r",\d{1,4}$", bruto):
            bruto = bruto.replace(".", "")
            bruto = bruto.replace(",", ".")
        else:
            bruto = bruto.replace(",", "")
    elif "." in bruto:
        if not re.search(r"\.\d{1,4}$", bruto):
            bruto = bruto.replace(".", "")

    try:
        return Decimal(bruto)
    except InvalidOperation:
        return None


def moeda_por_extenso(valor: Decimal | float | int | str, moeda: str = "BRL") -> str:
    numero = _parse_decimal_guess(str(valor)) if not isinstance(valor, Decimal) else valor
    if numero is None:
        return str(valor)

    moeda_key = moeda.upper()
    singular, plural = _MOEDAS.get(moeda_key, ("unidade", "unidades"))
    total = numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    inteiro = int(total)
    centavos = int((total - Decimal(inteiro)).copy_abs() * 100)

    partes: list[str] = []
    nome_principal = singular if abs(inteiro) == 1 else plural
    if inteiro != 0 or centavos == 0:
        partes.append(f"{numero_por_extenso(abs(inteiro))} {nome_principal}")
    if centavos:
        nome_centavos = "centavo" if centavos == 1 else "centavos"
        partes.append(f"{numero_por_extenso(centavos)} {nome_centavos}")

    saida = _juntar_partes(partes) or f"zero {plural}"
    if total < 0:
        return "menos " + saida
    return saida


def temperatura_por_extenso(valor: Decimal | float | int | str) -> str:
    numero = _parse_decimal_guess(str(valor)) if not isinstance(valor, Decimal) else valor
    if numero is None:
        return str(valor)
    if numero == numero.to_integral():
        base = numero_por_extenso(int(numero))
    else:
        base = numero_decimal_por_extenso(numero)
    return f"{base} graus"


def percentual_por_extenso(valor: Decimal | float | int | str) -> str:
    numero = _parse_decimal_guess(str(valor)) if not isinstance(valor, Decimal) else valor
    if numero is None:
        return str(valor)
    if numero == numero.to_integral():
        base = numero_por_extenso(int(numero))
    else:
        base = numero_decimal_por_extenso(numero)
    return f"{base} por cento"


def _periodo_do_dia(hora: int) -> str:
    if 0 <= hora < 6:
        return "madrugada"
    if hora < 12:
        return "manha"
    if hora < 19:
        return "tarde"
    return "noite"


def hora_por_extenso(texto: str) -> str:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", (texto or "").strip())
    if not match:
        return texto

    hora = int(match.group(1))
    minuto = int(match.group(2))
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        return texto

    periodo = _PERIODOS[_periodo_do_dia(hora)]
    if hora == 0:
        base = "meia-noite"
    elif hora == 12:
        base = "meio-dia"
    else:
        base = numero_por_extenso(hora % 12 or 12)

    if minuto == 0:
        if base in {"meia-noite", "meio-dia"}:
            return f"{base} em ponto"
        return f"{base} em ponto {periodo}"
    if minuto == 30:
        if base in {"meia-noite", "meio-dia"}:
            return f"{base} e meia"
        return f"{base} e meia {periodo}"
    if base in {"meia-noite", "meio-dia"}:
        return f"{base} e {numero_por_extenso(minuto)}"
    return f"{base} e {numero_por_extenso(minuto)} {periodo}"


def data_por_extenso(texto: str) -> str:
    bruto = (texto or "").strip()
    if not bruto:
        return bruto

    candidatos = (
        ("%d/%m/%Y", bruto),
        ("%d/%m/%y", bruto),
        ("%Y-%m-%d", bruto[:10]),
    )
    dt = None
    for formato, valor in candidatos:
        try:
            dt = datetime.strptime(valor, formato)
            break
        except ValueError:
            continue
    if dt is None:
        return texto

    dia = "primeiro" if dt.day == 1 else numero_por_extenso(dt.day)
    mes = _MESES.get(dt.month, str(dt.month))
    ano = numero_por_extenso(dt.year)
    return f"{dia} de {mes} de {ano}"


def timestamp_por_extenso(texto: str) -> str:
    bruto = (texto or "").strip()
    if not bruto:
        return bruto
    try:
        dt = datetime.fromisoformat(bruto.replace("Z", "+00:00"))
    except ValueError:
        return texto
    return f"{data_por_extenso(dt.strftime('%Y-%m-%d'))}, {hora_por_extenso(dt.strftime('%H:%M'))}"


def coordenadas_por_extenso(
    latitude: Decimal | float | int | str, longitude: Decimal | float | int | str
) -> str:
    lat = _parse_decimal_guess(str(latitude))
    lon = _parse_decimal_guess(str(longitude))
    if lat is None or lon is None:
        return f"{latitude}, {longitude}"
    lat_dir = "sul" if lat < 0 else "norte"
    lon_dir = "oeste" if lon < 0 else "leste"
    return (
        f"latitude {numero_decimal_por_extenso(abs(lat).quantize(Decimal('0.0001')))} {lat_dir}, "
        f"longitude {numero_decimal_por_extenso(abs(lon).quantize(Decimal('0.0001')))} {lon_dir}"
    )


def preparar_texto_para_fala(texto: str) -> str:
    saida = (texto or "").strip()
    if not saida:
        return ""

    saida = re.sub(r"https?://\S+", "o link esta no chat", saida)
    saida = re.sub(r"\[[^\]]*\]", " ", saida)
    saida = re.sub(r"[\U00010000-\U0010ffff]", " ", saida)

    saida = re.sub(
        r"\b(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}(?::\d{2})?(?:Z|[+\-]\d{2}:\d{2})?)\b",
        lambda m: timestamp_por_extenso(m.group(1)),
        saida,
    )
    saida = re.sub(
        r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
        lambda m: data_por_extenso(m.group(1)),
        saida,
    )
    saida = re.sub(
        r"\b(\d{4}-\d{2}-\d{2})\b",
        lambda m: data_por_extenso(m.group(1)),
        saida,
    )
    saida = re.sub(
        r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b",
        lambda m: hora_por_extenso(m.group(1)),
        saida,
    )

    padroes_moeda = (
        (r"R\$\s*([0-9]+(?:[.,][0-9]+)*)", "BRL"),
        (r"US\$\s*([0-9]+(?:[.,][0-9]+)*)", "USD"),
        (r"€\s*([0-9]+(?:[.,][0-9]+)*)", "EUR"),
        (r"\bBRL\s*([0-9]+(?:[.,][0-9]+)*)", "BRL"),
        (r"\bUSD\s*([0-9]+(?:[.,][0-9]+)*)", "USD"),
        (r"\bEUR\s*([0-9]+(?:[.,][0-9]+)*)", "EUR"),
    )
    for padrao, moeda in padroes_moeda:
        saida = re.sub(
            padrao,
            lambda m, moeda=moeda: moeda_por_extenso(m.group(1), moeda=moeda),
            saida,
        )

    saida = re.sub(
        r"(-?\d+(?:[.,]\d+)?)\s*°\s*C\b",
        lambda m: temperatura_por_extenso(m.group(1)),
        saida,
        flags=re.IGNORECASE,
    )
    saida = re.sub(
        r"(-?\d+(?:[.,]\d+)?)\s*%",
        lambda m: percentual_por_extenso(m.group(1)),
        saida,
    )

    saida = saida.replace("//", ", ")
    saida = saida.replace("...", ".")
    saida = re.sub(r"\s+", " ", saida).strip(" ,.-")
    return saida
