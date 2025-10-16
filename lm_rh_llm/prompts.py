"""Prompt templates used by the Leroy Merlin HR document pipeline."""

from __future__ import annotations

from typing import Iterable


CLASSIFIER_SYSTEM_MESSAGE = """Você é um classificador e extrator automático de documentos de Recursos Humanos (RH) da Leroy Merlin. Sua tarefa é classificar corretamente documentos segundo os tipos da lista \"leroy_doctypes\" e extrair os campos solicitados com máxima precisão e sem inventar dados.\n\nRegras obrigatórias:\n- Use apenas os tipos de documento da enumeração fornecida (leroy_doctypes). Se não tiver certeza absoluta sobre o tipo, defina `needs_review=true`, escolha o tipo mais aproximado possível e justifique em `notes`.\n- Nunca crie ou invente informações. Se algum campo estiver ausente ou pouco claro, deixe-o em branco e aumente a nota explicativa (`notes`).\n- A data do documento (`document_date`) deve ser normalizada para o formato `YYYY-MM-DD`, mesmo que venha como \"12/02/2024\", \"12.Fev.2024\", \"12-Julho-21\", etc.\n- Para o nome do colaborador (`employee_name`), priorize cabeçalhos, etiquetas de identificação ou seções explícitas no documento. Ignore nomes em assinaturas ou em comunicações genéricas.\n- Preencha o campo `confidence` com um valor entre 0.0 e 1.0 representando sua confiança na classificação geral.\n- Marque `needs_review=true` quando:\n  - `confidence < 0.70`\n  - ou quando algum dos campos obrigatórios (`document_type`) estiver ausente ou pouco confiável\n- Produza a saída exclusivamente no formato definido pelo JSON Schema (abaixo), respeitando os tipos e enum.\n\nEvidência no documento\tdocument_type\n“IBAN”, “NIB”, “BIC”\tNIB\n“Contrato de Trabalho”, \"a termo certo\", \"tempo parcial\"\tCONTRATO_TRABALHO\n“Remuneração”, “Vencimento”, “Recibo”, \"Líquido\", \"Sub. Alimentação\"\tRECIBO_VENCIMENTO\n“Declaração de Rendimentos” ou referência a “IRS”\tIRS\n“Admissão de Colaborador”\tFICHA_ADMISSAO\nCartão de Cidadão\tCC\nRGPD, cláusulas de proteção de dados\tRGPD\nSem correspondência clara\tOUTROS ou needs_review=true\n\n⚠️ Fallback (quando confidence < 0.70 ou campos críticos ausentes)\nPrompt é o mesmo, mas modelo alterado para o3-mini ou outro LLM com maior capacidade de reasoning. Use o mesmo input, só mudando o modelo para gpt-4, o3, etc."""


CLASSIFIER_USER_MESSAGE_TEMPLATE = """{json_payload}\n\nObservação: o campo file_id é enviado junto no input do Responses API como arquivo PDF real."""


CLASSIFIER_JSON_SCHEMA_TEMPLATE = """{\n  \"type\": \"object\",\n  \"additionalProperties\": false,\n  \"properties\": {\n    \"ordinal\": { \"type\": \"integer\" },\n    \"filename\": { \"type\": \"string\" },\n    \"document_type\": {\n      \"type\": \"string\",\n      \"enum\": [{document_types}]\n    },\n    \"document_date\": { \"type\": \"string\", \"format\": \"date\" },\n    \"employee_name\": { \"type\": \"string\" },\n    \"confidence\": { \"type\": \"number\", \"minimum\": 0, \"maximum\": 1 },\n    \"needs_review\": { \"type\": \"boolean\" },\n    \"notes\": { \"type\": \"string\" }\n  },\n  \"required\": [ \"ordinal\", \"filename\", \"document_type\", \"confidence\", \"needs_review\" ]\n}\n"""


AGGREGATOR_SYSTEM_MESSAGE = """Gere exclusivamente um ficheiro CSV com os seguintes campos, neste exato cabeçalho e nesta ordem:\n\nordem;ficheiro;tipo_documento;data_documento;nome_colaborador;confidencia;needs_review;notas\n\nUse o ponto-e-vírgula `;` como separador de campos. Ordene os registos por `ordinal` ascendente. Emita apenas o conteúdo CSV, sem comentários, rodapés ou instruções."""


def render_classifier_json_schema(document_types: Iterable[str]) -> str:
    """Return the JSON schema with the dynamic `leroy_doctypes` enumeration."""

    quoted = ", ".join(f'"{doc_type}"' for doc_type in document_types)
    return CLASSIFIER_JSON_SCHEMA_TEMPLATE.format(document_types=quoted)


def render_classifier_user_message(payload: str) -> str:
    """Embed the JSON payload into the user-facing message."""

    return CLASSIFIER_USER_MESSAGE_TEMPLATE.format(json_payload=payload)


def render_user_payload(
    ordinal: int,
    filename: str,
    file_id: str,
    instructions: str | None,
) -> str:
    """Serialize the user JSON structure expected by the Responses API."""

    base = {
        "ordinal": ordinal,
        "filename": filename,
        "file_id": file_id,
        "instrucoes": instructions or "",
    }
    # We keep the JSON compact but stable to simplify prompting
    import json

    return json.dumps(base, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

