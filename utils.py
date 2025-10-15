import re
import json

TIPOS_VALIDOS = [
    "Admissão", "Dados Pessoais", "NIB", "Declaração IRS", "CV", "Registo Criminal",
    "Penhoras", "Processos Disciplinares", "Aditamentos ao Contrato de Trabalho",
    "Declarações", "Rescisão/Demissão", "Diversos", "Absentismos"
]

def normalizar_tipo_documento(valor):
    if valor in TIPOS_VALIDOS:
        return valor
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

def process_text_fields(resposta_llm):
    try:
        parsed = json.loads(resposta_llm)
    except:
        parsed = {"nome_colaborador": "", "data_documento": "", "tipo_documento": ""}
    parsed["tipo_documento"] = normalizar_tipo_documento(parsed.get("tipo_documento", ""))
    return parsed
