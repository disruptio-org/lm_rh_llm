"""Leroy Merlin HR document processing toolkit."""

from .models import DocumentRequest, DocumentResult
from .classifier import classify_document
from .aggregator import generate_csv

__all__ = [
    "DocumentRequest",
    "DocumentResult",
    "classify_document",
    "generate_csv",
]
