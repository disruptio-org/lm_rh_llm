import os
import fitz
import pytesseract
import io
import pandas as pd
from PIL import Image
from fastapi import FastAPI
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from openai import OpenAI
from utils import process_text_fields

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PASTA_PDFS = os.getenv("PDF_FOLDER", "./pdfs")
SAIDA_CSV = "documentos_processados.csv"

client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()

def extrair_texto_pdf(path_pdf):
    texto = ""
    try:
        doc = fitz.open(path_pdf)
        for page in doc:
            texto += page.get_text()
        return texto.strip()
    except:
        return ""

def aplicar_ocr(path_pdf):
    texto_ocr = ""
    try:
        doc = fitz.open(path_pdf)
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            texto_ocr += pytesseract.image_to_string(img)
        return texto_ocr.strip()
    except:
        return ""

def chamar_openai(id_doc, texto):
    TIPOS = [
        "Admissão", "Dados Pessoais", "NIB", "Declaração IRS", "CV", "Registo Criminal",
        "Penhoras", "Processos Disciplinares", "Aditamentos ao Contrato de Trabalho",
        "Declarações", "Rescisão/Demissão", "Diversos", "Absentismos"
    ]
    lista_tipos = ", ".join(f'"{tipo}"' for tipo in TIPOS)
    prompt = f"""
Abaixo está o conteúdo de um documento PDF de Recursos Humanos. Extraia as seguintes informações:

- nome_colaborador: Nome completo do colaborador (exatamente como está no texto)
- data_documento: Data do documento no formato YYYY-MM-DD (data de assinatura ou vigência)
- tipo_documento: Classificação do documento com base estrita nos seguintes valores permitidos:
[{lista_tipos}]

Se não for possível identificar com confiança, devolve "Diversos".

---
ID: {id_doc}
Conteúdo:
{texto}
---
Resposta esperada em JSON:
{{"nome_colaborador": "...", "data_documento": "...", "tipo_documento": "..."}}.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "És um assistente para extração inteligente de documentos de RH. Segue apenas a lista de tipos permitidos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro OpenAI: {e}")
        return '{"nome_colaborador": "", "data_documento": "", "tipo_documento": ""}'

@app.post("/processar-pasta")
def processar_pasta_local():
    resultados = []
    ficheiros = sorted(os.listdir(PASTA_PDFS))

    for filename in ficheiros:
        if not filename.lower().endswith(".pdf"):
            continue

        filepath = os.path.join(PASTA_PDFS, filename)
        id_doc = os.path.splitext(filename)[0]
        print(f"📄 A processar: {id_doc}...")

        texto = extrair_texto_pdf(filepath)
        if len(texto.strip()) < 20:
            texto = aplicar_ocr(filepath)

        resposta = chamar_openai(id_doc, texto)
        dados_extraidos = process_text_fields(resposta)

        dados_extraidos["id_documento"] = id_doc
        resultados.append(dados_extraidos)

    df = pd.DataFrame(resultados, columns=["id_documento", "nome_colaborador", "data_documento", "tipo_documento"])
    df.to_csv(SAIDA_CSV, index=False, encoding="utf-8-sig")
    return FileResponse(SAIDA_CSV, filename=SAIDA_CSV)
