"""Typer-based command line interface for the HR document workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import typer
from dotenv import load_dotenv
from openai import OpenAI

from .aggregator import aggregate_with_model, generate_csv
from .classifier import classify_document
from .models import DocumentRequest, DocumentResult

app = typer.Typer(help="Ferramentas E2E para classificação e extração de documentos RH")


def _load_document_payload(path: Path) -> List[dict]:
    if not path.exists():
        raise typer.BadParameter(f"Input file {path} does not exist")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - user input
        raise typer.BadParameter(f"Could not parse JSON payload: {exc}") from exc


@app.command()
def classify(
    payload: Path = typer.Argument(..., help="JSON file with document requests"),
    document_type: List[str] = typer.Option(
        None,
        "--document-type",
        help="Valid document types (can be provided multiple times).",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help="Path to write the JSON results (defaults to stdout)",
    ),
    model: str = typer.Option("gpt-4o", help="Primary model used for classification"),
    fallback_model: Optional[str] = typer.Option(
        "o3-mini", help="Optional fallback model when confidence is too low"
    ),
    min_confidence: float = typer.Option(
        0.70,
        help="Confidence threshold that triggers the fallback model",
        min=0.0,
        max=1.0,
    ),
):
    """Classify a batch of documents and return the structured JSON outputs."""

    load_dotenv()
    client = OpenAI()

    payload_data = _load_document_payload(payload)
    if not payload_data:
        raise typer.BadParameter("The payload JSON cannot be empty")

    if not document_type:
        raise typer.BadParameter("At least one --document-type must be provided")

    exported: List[dict] = []
    for item in payload_data:
        request = DocumentRequest(
            ordinal=item["ordinal"],
            filename=item["filename"],
            file_id=item["file_id"],
            instructions=item.get("instrucoes"),
            document_types=document_type,
        )
        result, used_model = classify_document(
            client,
            request,
            model=model,
            fallback_model=fallback_model,
            minimum_confidence=min_confidence,
        )
        payload = result.model_dump()
        payload["model"] = used_model
        exported.append(payload)

    output_data = json.dumps(exported, ensure_ascii=False, indent=2)
    if output:
        output.write_text(output_data, encoding="utf-8")
    else:
        typer.echo(output_data)


@app.command()
def aggregate(
    results_path: Path = typer.Argument(..., help="JSON file with DocumentResult payloads"),
    use_llm: bool = typer.Option(
        False, "--use-llm", help="Use the OpenAI aggregator prompt instead of local CSV"
    ),
    model: str = typer.Option("gpt-4o-mini", help="Model used when --use-llm is enabled"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help="Path to write the generated CSV (defaults to stdout)",
    ),
):
    """Create the final CSV either locally or via the aggregator prompt."""

    payload = _load_document_payload(results_path)
    results = [DocumentResult.model_validate(item) for item in payload]

    if use_llm:
        load_dotenv()
        client = OpenAI()
        csv_data = aggregate_with_model(client, results, model=model)
    else:
        csv_data = generate_csv(results)

    if output:
        output.write_text(csv_data, encoding="utf-8")
    else:
        typer.echo(csv_data)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    app()

