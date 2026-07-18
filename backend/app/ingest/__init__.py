"""Ingestion: map an incoming record into a normalized TumorBoardCase.

Source-agnostic by design. Today there is one adapter (FHIR envelope, Abridge's
contract). To support a new source, add an adapter that returns a TumorBoardCase
and register it here — nothing downstream changes.
"""
from __future__ import annotations

from ..case_schema import TumorBoardCase
from . import fhir_adapter


def ingest(record: dict) -> TumorBoardCase:
    """Detect the source shape and dispatch to the right adapter."""
    if fhir_adapter.can_handle(record):
        return fhir_adapter.from_record(record)
    # Fallback: preserve whatever we got so nothing is silently dropped.
    return TumorBoardCase(case_id=record.get("id"), unmapped=[record])
