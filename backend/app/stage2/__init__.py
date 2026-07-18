"""Stage 2 — patient data structuring (contract: docs/stage-interface-contract.yaml).

Raw FHIR-shaped source record → PatientCaseBundle: normalized, addressable,
provenance-carrying facts plus mechanical presence/staleness. No clinical
judgment; the word "gap" never appears here. See `to_bundle`.
"""
from .adapter import to_bundle
from .bundle import PatientCaseBundle

__all__ = ["to_bundle", "PatientCaseBundle"]
