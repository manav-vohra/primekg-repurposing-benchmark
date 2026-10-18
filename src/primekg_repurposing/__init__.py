"""Clean PrimeKG provenance infrastructure. Scientific models are added later."""

from .provenance import ProvenanceClass, VerificationState, validate

__all__ = ["ProvenanceClass", "VerificationState", "validate"]
