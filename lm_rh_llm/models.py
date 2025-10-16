"""Data models used by the Leroy Merlin HR LLM pipeline."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, validator


class DocumentRequest(BaseModel):
    """Input payload for classifying a single document."""

    ordinal: int = Field(..., description="Sequential document identifier")
    filename: str = Field(..., description="Human friendly filename")
    file_id: str = Field(..., description="OpenAI file identifier for the PDF")
    instructions: Optional[str] = Field(
        None, description="Custom user instructions to append to the prompt"
    )
    document_types: List[str] = Field(
        ..., description="Enumeration of valid document types for classification"
    )

    @validator("document_types")
    def ensure_unique_doctypes(cls, value: List[str]) -> List[str]:
        ordered_unique = []
        seen = set()
        for item in value:
            normalized = item.strip()
            if not normalized:
                continue
            if normalized not in seen:
                ordered_unique.append(normalized)
                seen.add(normalized)
        if not ordered_unique:
            raise ValueError("document_types cannot be empty")
        return ordered_unique


class DocumentResult(BaseModel):
    """Structured output returned by the model."""

    ordinal: int
    filename: str
    document_type: str
    document_date: Optional[str] = None
    employee_name: Optional[str] = None
    confidence: float
    needs_review: bool
    notes: Optional[str] = None

    @validator("confidence")
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    def requires_fallback(self, minimum_confidence: float) -> bool:
        """Return True when the response should trigger the fallback model."""

        return self.confidence < minimum_confidence or self.needs_review

