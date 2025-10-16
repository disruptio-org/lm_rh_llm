"""CSV aggregation helpers for Leroy Merlin HR pipeline."""

from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Iterable, Sequence

from openai import OpenAI

from .models import DocumentResult
from .prompts import AGGREGATOR_SYSTEM_MESSAGE

AGGREGATOR_MODEL = "gpt-4o-mini"

CSV_HEADER = [
    "ordem",
    "ficheiro",
    "tipo_documento",
    "data_documento",
    "nome_colaborador",
    "confidencia",
    "needs_review",
    "notas",
]


def generate_csv(results: Iterable[DocumentResult]) -> str:
    """Create a deterministic CSV string using Python's CSV writer."""

    sorted_results = sorted(results, key=lambda item: item.ordinal)
    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for result in sorted_results:
        writer.writerow(
            [
                result.ordinal,
                result.filename,
                result.document_type,
                result.document_date or "",
                result.employee_name or "",
                f"{result.confidence:.2f}",
                str(result.needs_review).lower(),
                result.notes or "",
            ]
        )
    return buffer.getvalue().strip()


def aggregate_with_model(
    client: OpenAI,
    results: Sequence[DocumentResult],
    *,
    model: str = AGGREGATOR_MODEL,
) -> str:
    """Ask an LLM to produce the CSV following the strict system prompt."""

    json_payload = json.dumps([result.model_dump() for result in results], ensure_ascii=False)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": AGGREGATOR_SYSTEM_MESSAGE},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": json_payload},
                ],
            },
        ],
        temperature=0,
    )

    return response.output_text.strip()

