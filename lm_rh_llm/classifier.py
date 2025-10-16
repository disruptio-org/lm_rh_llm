"""Interface with the OpenAI Responses API for document classification."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from openai import OpenAI
from openai.types import Response
from pydantic import ValidationError

from .models import DocumentRequest, DocumentResult
from .prompts import (
    CLASSIFIER_SYSTEM_MESSAGE,
    render_classifier_json_schema,
    render_classifier_user_message,
    render_user_payload,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o"
FALLBACK_MODEL = "o3-mini"
MIN_CONFIDENCE = 0.70


class ClassificationError(RuntimeError):
    """Raised when the model response cannot be parsed."""


def classify_document(
    client: OpenAI,
    request: DocumentRequest,
    *,
    model: str = DEFAULT_MODEL,
    fallback_model: Optional[str] = FALLBACK_MODEL,
    minimum_confidence: float = MIN_CONFIDENCE,
) -> Tuple[DocumentResult, str]:
    """Classify a single document and optionally use a fallback model.

    Returns a tuple containing the resulting :class:`DocumentResult` and the
    name of the model that produced it.
    """

    primary_result = _invoke_model(client, request, model)
    LOGGER.debug("Primary model %s returned: %s", model, primary_result)

    if fallback_model and primary_result.requires_fallback(minimum_confidence):
        LOGGER.info(
            "Confidence %.2f below threshold %.2f or needs review flagged, invoking fallback %s",
            primary_result.confidence,
            minimum_confidence,
            fallback_model,
        )
        fallback_result = _invoke_model(client, request, fallback_model)
        LOGGER.debug("Fallback model %s returned: %s", fallback_model, fallback_result)
        return fallback_result, fallback_model

    return primary_result, model


def _invoke_model(client: OpenAI, request: DocumentRequest, model: str) -> DocumentResult:
    response = _create_response(client, request, model)
    return _parse_response(response)


def _create_response(client: OpenAI, request: DocumentRequest, model: str) -> Response:
    schema = render_classifier_json_schema(request.document_types)
    system_content = f"{CLASSIFIER_SYSTEM_MESSAGE}\n\nJSON Schema de saída:\n{schema}"
    user_payload = render_user_payload(
        ordinal=request.ordinal,
        filename=request.filename,
        file_id=request.file_id,
        instructions=request.instructions,
    )
    user_message = render_classifier_user_message(user_payload)

    LOGGER.info("Requesting classification for %s via %s", request.filename, model)

    return client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system_content},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_message},
                ],
                "attachments": [
                    {"file_id": request.file_id},
                ],
            },
        ],
        temperature=0,
    )


def _parse_response(response: Response) -> DocumentResult:
    try:
        raw_text = response.output_text
    except AttributeError as exc:  # pragma: no cover - defensive fallback
        raise ClassificationError("The OpenAI response does not contain text output") from exc

    payload = _extract_json_block(raw_text)
    try:
        return DocumentResult.model_validate_json(payload)
    except ValidationError as exc:
        raise ClassificationError(f"Could not validate model output: {payload}") from exc


def _extract_json_block(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove leading and trailing code fences such as ```json
        cleaned = cleaned.strip("`")  # remove all backticks to simplify
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    # Some models may prepend text like `Output:` before the JSON payload
    if cleaned and cleaned[0] != "{":
        start = cleaned.find("{")
        if start != -1:
            cleaned = cleaned[start:]
    return cleaned

