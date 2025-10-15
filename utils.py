import re
import json
from datetime import datetime


IBAN_REGEX = re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]){11,30}\b", re.IGNORECASE)
VALID_WORD_REGEX = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ']+(?:-[A-Za-zÀ-ÖØ-öø-ÿ']+)*$")
CONNECTORES_NOME = {"DA", "DE", "DO", "DOS", "DAS", "E", "DEL", "DELLA", "DI", "DU"}
CONNECTORES_NOME_LOWER = {c.lower() for c in CONNECTORES_NOME}
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
    "segundo outorgante",
    "outorgante",
]
PALAVRAS_CHAVE_NIB = [
    "iban",
    "nib",
    "pt50",
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
    "multibanco",
    "primeira conta do cartão",
    "primeira conta do cartao",
    "titular da conta",
    "bpi",
    "millennium",
    "santander",
    "caixa geral",
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
    "MULTIBANCO",
}

PALAVRAS_CHAVE_DATA = [
    ("assinatura", 5),
    ("assinado", 5),
    ("vigência", 4),
    ("vigencia", 4),
    ("início", 4),
    ("inicio", 4),
    ("início de vigência", 6),
    ("inicio de vigencia", 6),
    ("data", 2),
    ("emitido", 3),
    ("emissão", 3),
    ("emissao", 3),
]

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
    if "banco" in texto_lower:
        indicadores_associados = ("conta", "iban", "nib", "pt50", "multibanco")
        if any(indicador in texto_lower for indicador in indicadores_associados):
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


def _formatar_palavra_nome(parte):
    segmentos_hifen = parte.split("-")
    segmentos_resultado = []
    for segmento in segmentos_hifen:
        if not segmento:
            return ""
        sub_segmentos = segmento.split("'")
        sub_resultado = []
        for sub in sub_segmentos:
            if not sub:
                return ""
            if not sub[0].isalpha():
                return ""
            sub_formatado = sub[0].upper() + sub[1:].lower()
            sub_resultado.append(sub_formatado)
        segmentos_resultado.append("'".join(sub_resultado))
    return "-".join(segmentos_resultado)


def _formatar_partes_nome(partes):
    if not partes:
        return []
    partes_formatadas = []
    palavras_validas = 0
    for parte in partes:
        if not parte or any(char.isdigit() for char in parte):
            return []
        if not VALID_WORD_REGEX.match(parte):
            return []
        parte_sem_espacos = parte.strip()
        parte_upper = parte_sem_espacos.upper()
        if parte_upper in PALAVRAS_PROIBIDAS_NOME:
            return []
        if parte_upper in CONNECTORES_NOME:
            partes_formatadas.append(parte_sem_espacos.lower())
            continue
        palavra_formatada = _formatar_palavra_nome(parte_sem_espacos)
        if not palavra_formatada:
            return []
        if not palavra_formatada[0].isupper():
            return []
        partes_formatadas.append(palavra_formatada)
        palavras_validas += 1
    if palavras_validas < 2:
        return []
    # Evita conectores isolados no fim
    while partes_formatadas and partes_formatadas[0] in CONNECTORES_NOME_LOWER:
        partes_formatadas.pop(0)
    while partes_formatadas and partes_formatadas[-1] in CONNECTORES_NOME_LOWER:
        partes_formatadas.pop()
    if not partes_formatadas:
        return []
    return partes_formatadas


def _extrair_nome_de_linha(linha):
    if not isinstance(linha, str):
        return ""
    linha_limpa = linha.strip()
    if not linha_limpa or any(char.isdigit() for char in linha_limpa):
        return ""
    linha_limpa = _limpar_espacos(linha_limpa)
    palavras = [p.strip(".,;:-()") for p in re.split(r"\s+", linha_limpa) if p.strip(".,;:-()")]
    partes_formatadas = _formatar_partes_nome(palavras)
    if partes_formatadas:
        return " ".join(partes_formatadas)
    return ""


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
    partes = [p for p in re.split(r"\s+", nome) if p]
    partes_formatadas = _formatar_partes_nome(partes)
    if not partes_formatadas:
        return ""
    return " ".join(partes_formatadas)


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


PADROES_DATAS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{4}[\.\/-]\d{1,2}[\.\/-]\d{1,2}\b"),
    re.compile(r"\b\d{1,2}[\.\/-]\d{1,2}[\.\/-]\d{4}\b"),
    re.compile(r"\b\d{1,2}\s+de\s+[A-Za-zçÇ]+\s+de\s+\d{4}\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s+(?:de\s+)?[A-Za-zçÇ]+\s+(?:de\s+)?\d{4}\b", re.IGNORECASE),
]


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

    match_iso_alt = re.search(r"(\d{4})[\.\/-](\d{1,2})[\.\/-](\d{1,2})", valor_limpo)
    if match_iso_alt:
        ano, mes, dia = match_iso_alt.groups()
        if _validar_data(ano, mes, dia):
            return f"{int(ano):04d}-{int(mes):02d}-{int(dia):02d}"

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

    match_texto_alt = re.search(r"(\d{1,2})\s+(?:de\s+)?([a-zç]+)\s+(?:de\s+)?(\d{4})", valor_limpo)
    if match_texto_alt:
        dia, mes_texto, ano = match_texto_alt.groups()
        mes = MESES_PT.get(mes_texto)
        if mes and _validar_data(ano, mes, dia):
            return f"{int(ano):04d}-{int(mes):02d}-{int(dia):02d}"

    return ""


def _pontuar_contexto_data(texto_lower, inicio, fim):
    janela_inicio = max(0, inicio - 100)
    janela_fim = min(len(texto_lower), fim + 100)
    janela = texto_lower[janela_inicio:janela_fim]
    pontuacao = 0
    for palavra, peso in PALAVRAS_CHAVE_DATA:
        if palavra in janela:
            pontuacao += peso
    return pontuacao


def encontrar_data_em_texto(texto):
    if not isinstance(texto, str) or not texto.strip():
        return ""
    texto_lower = texto.lower()
    melhores = []
    for padrao in PADROES_DATAS:
        for match in padrao.finditer(texto):
            trecho = match.group(0)
            data_normalizada = normalizar_data(trecho)
            if not data_normalizada:
                continue
            pontuacao = _pontuar_contexto_data(texto_lower, match.start(), match.end())
            melhores.append((pontuacao, match.start(), data_normalizada))
    if not melhores:
        return ""
    melhores.sort(key=lambda item: (-item[0], item[1]))
    return melhores[0][2]


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
            if nome_normalizado:
                nome = nome_normalizado
    data = normalizar_data(parsed.get("data_documento", ""))
    if not data and texto_original:
        data = encontrar_data_em_texto(texto_original)
    tipo = normalizar_tipo_documento(parsed.get("tipo_documento", ""), texto_original)

    return {
        "nome_colaborador": nome,
        "data_documento": data,
        "tipo_documento": tipo,
    }
