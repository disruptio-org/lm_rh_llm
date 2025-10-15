import re
import json
from datetime import datetime

# --------------------
# Constantes e regras
# --------------------
TIPOS_VALIDOS = [
    "Admissão",
    "Dados Pessoais",
    "NIB",
    "Declaração IRS",
    "CV",
    "Registo Criminal",
    "Penhoras",
    "Processos Disciplinares",
    "Aditamentos ao Contrato de Trabalho",
    "Declarações",
    "Rescisão/Demissão",
    "Diversos",
    "Absentismos",
]


def normalizar_tipo_documento(valor):
    if valor in TIPOS_VALIDOS:
        return valor
    if not isinstance(valor, str):
        valor = ""
    texto = valor.lower()
    if "termo" in texto or "contrato" in texto:
        return "Admissão"
    if "curriculo" in texto or "cv" in texto:
        return "CV"
    if "criminal" in texto:
        return "Registo Criminal"
    if "iban" in texto or "nib" in texto:
        return "NIB"
    if "irs" in texto:
        return "Declaração IRS"
    if "penhor" in texto:
        return "Penhoras"
    if "disciplina" in texto:
        return "Processos Disciplinares"
    if "aditamento" in texto:
        return "Aditamentos ao Contrato de Trabalho"
    if "absent" in texto or "baixa" in texto:
        return "Absentismos"
    if "pessoal" in texto:
        return "Dados Pessoais"
    if "rescis" in texto or "demiss" in texto:
        return "Rescisão/Demissão"
    if "declara" in texto:
        return "Declarações"
    return "Diversos"


def _limpar_espacos(valor):
    if not isinstance(valor, str):
        return ""
    return re.sub(r"\s+", " ", valor).strip()


def normalizar_nome(valor):
    nome = _limpar_espacos(valor)
    if not nome:
        return ""
    partes = [p for p in nome.split(" ") if p]
    if len(partes) < 2:
        return ""
    return " ".join(partes)


MESES_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def _validar_data(ano, mes, dia):
    try:
        datetime(int(ano), int(mes), int(dia))
        return True
    except ValueError:
        return False


def normalizar_data(valor):
    valor_limpo = _limpar_espacos(valor).lower()
    if not valor_limpo:
        return ""

    match_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", valor_limpo)
    if match_iso and _validar_data(*match_iso.groups()):
        return f"{match_iso.group(1)}-{match_iso.group(2)}-{match_iso.group(3)}"

    match_num = re.search(r"(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})", valor_limpo)
    if match_num:
        dia, mes, ano = match_num.groups()
        if _validar_data(ano, mes, dia):
            return f"{int(ano):04d}-{int(mes):02d}-{int(dia):02d}"

    match_texto = re.search(r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})", valor_limpo)
    if match_texto:
        dia, mes_texto, ano = match_texto.groups()
        mes = MESES_PT.get(mes_texto)
        if mes and _validar_data(ano, mes, dia):
            return f"{int(ano):04d}-{int(mes):02d}-{int(dia):02d}"

    return ""


def extrair_json(texto):
    if not isinstance(texto, str):
        return {}
    texto = texto.strip()
    if not texto:
        return {}

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return {}


def process_text_fields(resposta_llm):
    parsed = extrair_json(resposta_llm)

    nome = normalizar_nome(parsed.get("nome_colaborador", ""))
    data = normalizar_data(parsed.get("data_documento", ""))
    tipo = normalizar_tipo_documento(parsed.get("tipo_documento", ""))

    return {
        "nome_colaborador": nome,
        "data_documento": data,
        "tipo_documento": tipo,
    }
