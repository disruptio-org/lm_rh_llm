import re
import json
from datetime import datetime


IBAN_REGEX = re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]){11,30}\b", re.IGNORECASE)
CONNECTORES_NOME = {"DA", "DE", "DO", "DOS", "DAS", "E", "DEL", "DELLA", "DI", "DU"}
PALAVRAS_CHAVE_NOME = [
    "titular",
    "cliente",
    "beneficiário",
    "beneficiario",
    "portador",
    "colaborador",
    "funcionário",
    "funcionario",
    "trabalhador",
    "nome",
    "beneficiária",
    "beneficiaria",
]
PALAVRAS_CHAVE_NIB = [
    "iban",
    "nib",
    "número de conta",
    "numero de conta",
    "conta bancária",
    "conta bancaria",
    "comprovativo de conta",
    "comprovativo bancário",
    "comprovativo bancario",
    "entidade bancária",
    "entidade bancaria",
    "balcão",
    "balcao",
]
PALAVRAS_PROIBIDAS_NOME = {
    "DECLARAÇÃO",
    "DECLARACAO",
    "COMPROVATIVO",
    "DOCUMENTO",
    "CONTRATO",
    "TERMO",
    "PROCESSO",
    "PENHORA",
    "ADITAMENTO",
    "BANCO",
    "ENTIDADE",
    "NÚMERO",
    "NUMERO",
    "CONTA",
    "IBAN",
    "NIB",
}

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


def _texto_indica_documento_bancario(texto):
    if not isinstance(texto, str) or not texto:
        return False
    texto_lower = texto.lower()
    if any(palavra in texto_lower for palavra in PALAVRAS_CHAVE_NIB):
        return True
    for match in IBAN_REGEX.finditer(texto):
        iban = re.sub(r"\s+", "", match.group(0))
        if len(iban) >= 15 and len(iban) <= 34 and iban[:2].isalpha() and iban[2:4].isdigit():
            return True
    return False


def normalizar_tipo_documento(valor, texto_completo=""):
    if valor in TIPOS_VALIDOS:
        return valor
    if _texto_indica_documento_bancario(valor) or _texto_indica_documento_bancario(texto_completo):
        return "NIB"
    if not isinstance(valor, str):
        valor = ""
    texto = valor.lower()
    if "termo" in texto or "contrato" in texto:
        return "Admissão"
    if "curriculo" in texto or "cv" in texto:
        return "CV"
    if "criminal" in texto:
        return "Registo Criminal"
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


def _extrair_nome_de_linha(linha):
    if not isinstance(linha, str):
        return ""
    linha_limpa = linha.strip()
    if not linha_limpa or any(char.isdigit() for char in linha_limpa):
        return ""
    linha_limpa = _limpar_espacos(linha_limpa)
    palavras = [p.strip(".,;:-") for p in linha_limpa.split(" ") if p.strip(".,;:-")]
    if len(palavras) < 3:
        return ""
    palavras_maiusculas = {p.upper() for p in palavras}
    if palavras_maiusculas & PALAVRAS_PROIBIDAS_NOME:
        return ""
    palavras_validas = 0
    for palavra in palavras:
        palavra_upper = palavra.upper()
        if palavra_upper in CONNECTORES_NOME:
            continue
        if re.fullmatch(r"[A-ZÁÉÍÓÚÃÕÂÊÔÇ']{2,}", palavra_upper):
            palavras_validas += 1
            continue
        return ""
    if palavras_validas < 3:
        return ""
    return " ".join(palavras)


def _extrair_nome_por_keywords(linhas):
    for indice, linha in enumerate(linhas):
        linha_str = linha.strip()
        if not linha_str:
            continue
        linha_lower = linha_str.lower()
        for palavra in PALAVRAS_CHAVE_NOME:
            posicao = linha_lower.find(palavra)
            if posicao == -1:
                continue
            trecho = linha_str[posicao + len(palavra) :].strip(" :-\t")
            if trecho:
                nome = _extrair_nome_de_linha(trecho)
                if nome:
                    return nome
            if indice + 1 < len(linhas):
                nome = _extrair_nome_de_linha(linhas[indice + 1])
                if nome:
                    return nome
    return ""


def _extrair_nome_maiusculas(texto):
    linhas = [linha.strip() for linha in texto.splitlines()]
    for linha in linhas:
        nome = _extrair_nome_de_linha(linha)
        if nome:
            return nome
    return ""


def normalizar_nome(valor):
    nome = _limpar_espacos(valor)
    if not nome:
        return ""
    partes = [p for p in nome.split(" ") if p]
    if len(partes) < 2:
        return ""
    return " ".join(partes)


def encontrar_nome_em_texto(texto):
    if not isinstance(texto, str) or not texto.strip():
        return ""
    linhas = texto.splitlines()
    nome = _extrair_nome_por_keywords(linhas)
    if nome:
        return nome
    return _extrair_nome_maiusculas(texto)


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

    match_num = re.search(r"(\d{1,2})[\.\/-](\d{1,2})[\.\/-](\d{4})", valor_limpo)
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


def process_text_fields(resposta_llm, texto_original=""):
    parsed = extrair_json(resposta_llm)

    nome = normalizar_nome(parsed.get("nome_colaborador", ""))
    if not nome and texto_original:
        nome_fallback = encontrar_nome_em_texto(texto_original)
        if nome_fallback:
            nome_normalizado = normalizar_nome(nome_fallback)
            nome = nome_normalizado if nome_normalizado else _limpar_espacos(nome_fallback)
    data = normalizar_data(parsed.get("data_documento", ""))
    tipo = normalizar_tipo_documento(parsed.get("tipo_documento", ""), texto_original)

    return {
        "nome_colaborador": nome,
        "data_documento": data,
        "tipo_documento": tipo,
    }
