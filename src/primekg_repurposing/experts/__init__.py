"""Scientifically isolated expert implementations."""

from .e1_gene_similarity import E1RunResult, run_e1
from .e2_disease_transfer import E2RunResult, run_e2

__all__ = ["E1RunResult", "E2RunResult", "run_e1", "run_e2"]
