"""Cell-14-equivalent E1 weighted direct-gene cosine expert.

The scorer consumes only direct ``drug_protein`` and ``disease_protein``
relations.  Therapeutic labels, disease ontology, folds, and evaluator truth
never enter profile construction or scoring.
"""

from __future__ import annotations

import csv
import math
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..evaluation import ExpertScoreResult


EXPERT_ID = "E1_WEIGHTED_GENE_COSINE"
EXPERT_VERSION = "1.0"
EXPERT_FAMILY = "transparent_network"
ABSTENTION_REASON = "ABSTAIN_NO_DIRECT_GENE_PATH"
RELATIONS_USED = ("disease_protein", "drug_protein")


@dataclass(frozen=True)
class GeneProfiles:
    candidate_ids: tuple[str, ...]
    disease_ids: tuple[str, ...]
    drug_gene_pairs: frozenset[tuple[str, str]]
    primary_disease_gene_pairs: frozenset[tuple[str, str]]
    all_disease_gene_pairs: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class PreparedProfiles:
    candidate_ids: tuple[str, ...]
    disease_ids: tuple[str, ...]
    gene_ids: tuple[str, ...]
    gene_weights: object
    drug_gene_indices: tuple[tuple[int, ...], ...]
    disease_gene_indices: tuple[tuple[int, ...], ...]
    drug_gene_pair_count: int
    primary_disease_gene_pair_count: int
    all_disease_gene_pair_count: int


@dataclass(frozen=True)
class E1RunResult:
    expert_id: str
    expert_version: str
    expert_family: str
    benchmark_id: str
    candidate_ids: tuple[str, ...]
    disease_ids: tuple[str, ...]
    scores: object
    applicable: tuple[bool, ...]
    abstention_reasons: tuple[str | None, ...]
    deterministic: bool
    stochastic: bool
    seed: None
    metadata: Mapping[str, object]

    def disease_result(self, row: int) -> ExpertScoreResult:
        return ExpertScoreResult(
            expert_id=self.expert_id,
            expert_version=self.expert_version,
            disease_id=self.disease_ids[row],
            candidate_ids=self.candidate_ids,
            scores=self.scores[row],
            applicable=self.applicable[row],
            abstention_reason=self.abstention_reasons[row],
            seed=None,
            provenance="historical Cell 14; clean deterministic implementation",
            benchmark_id=self.benchmark_id,
            deterministic=True,
            metadata=self.metadata,
        )


def gene_weight(drug_degree: int, disease_degree: int):
    """Cell 14 weight, including assignment into float32 storage."""
    import numpy as np

    if drug_degree < 0 or disease_degree < 0:
        raise ValueError("gene degrees cannot be negative")
    return np.float32(1.0 / np.log2(2.0 + int(drug_degree) + int(disease_degree)))


def _edge_values(edge) -> tuple[str, str, str, str, str]:
    if isinstance(edge, Mapping):
        values = (edge["relation"], edge["x_id"], edge["x_type"], edge["y_id"], edge["y_type"])
    else:
        if len(edge) != 5:
            raise ValueError("edge must have relation, x_id, x_type, y_id, y_type")
        values = tuple(edge)
    return tuple(str(value) for value in values)  # type: ignore[return-value]


def build_gene_profiles(
    edges: Iterable[object], candidate_ids: Sequence[str], disease_ids: Sequence[str]
) -> GeneProfiles:
    """Canonicalize reciprocal direct-protein rows exactly as Cell 14."""
    candidates = tuple(str(value) for value in candidate_ids)
    diseases = tuple(str(value) for value in disease_ids)
    if len(candidates) != len(set(candidates)) or len(diseases) != len(set(diseases)):
        raise ValueError("canonical axes must contain unique IDs")
    candidate_set, disease_set = set(candidates), set(diseases)
    drug_pairs: set[tuple[str, str]] = set()
    primary_pairs: set[tuple[str, str]] = set()
    all_disease_pairs: set[tuple[str, str]] = set()
    for edge in edges:
        relation, x_id, x_type, y_id, y_type = _edge_values(edge)
        if relation == "drug_protein":
            if x_type == "drug" and y_type == "gene/protein" and x_id in candidate_set:
                drug_pairs.add((x_id, y_id))
            elif y_type == "drug" and x_type == "gene/protein" and y_id in candidate_set:
                drug_pairs.add((y_id, x_id))
        elif relation == "disease_protein":
            pair = None
            if x_type == "disease" and y_type == "gene/protein":
                pair = (x_id, y_id)
            elif y_type == "disease" and x_type == "gene/protein":
                pair = (y_id, x_id)
            if pair is not None:
                all_disease_pairs.add(pair)
                if pair[0] in disease_set:
                    primary_pairs.add(pair)
    return GeneProfiles(
        candidate_ids=candidates,
        disease_ids=diseases,
        drug_gene_pairs=frozenset(drug_pairs),
        primary_disease_gene_pairs=frozenset(primary_pairs),
        all_disease_gene_pairs=frozenset(all_disease_pairs),
    )


def extract_gene_profiles(
    raw_kg: Path,
    candidate_ids: Sequence[str],
    disease_ids: Sequence[str],
    *,
    chunksize: int = 500_000,
) -> GeneProfiles:
    """Stream only the five Cell-14 columns from exact raw PrimeKG."""
    import pandas as pd

    def selected_edges():
        usecols = ["relation", "x_id", "x_type", "y_id", "y_type"]
        for chunk in pd.read_csv(
            raw_kg, usecols=usecols, chunksize=chunksize, low_memory=False, dtype="string"
        ):
            selected = chunk.loc[chunk["relation"].isin(RELATIONS_USED), usecols]
            yield from selected.itertuples(index=False, name=None)

    return build_gene_profiles(selected_edges(), candidate_ids, disease_ids)


def prepare_profiles(profiles: GeneProfiles) -> PreparedProfiles:
    """Build sorted binary profiles and Cell-14 degree-derived weights."""
    import numpy as np

    genes = tuple(sorted(
        {gene for _, gene in profiles.drug_gene_pairs}
        | {gene for _, gene in profiles.primary_disease_gene_pairs}
    ))
    gene_index = {gene: i for i, gene in enumerate(genes)}
    candidate_index = {drug: i for i, drug in enumerate(profiles.candidate_ids)}
    disease_index = {disease: i for i, disease in enumerate(profiles.disease_ids)}
    drug_degree = Counter(gene for _, gene in profiles.drug_gene_pairs)
    disease_degree = Counter(gene for _, gene in profiles.all_disease_gene_pairs)
    weights = np.zeros(len(genes), dtype=np.float32)
    for gene, column in gene_index.items():
        weights[column] = gene_weight(drug_degree.get(gene, 0), disease_degree.get(gene, 0))
    drug_rows: list[list[int]] = [[] for _ in profiles.candidate_ids]
    for drug, gene in profiles.drug_gene_pairs:
        if gene in gene_index:
            drug_rows[candidate_index[drug]].append(gene_index[gene])
    disease_rows: list[list[int]] = [[] for _ in profiles.disease_ids]
    for disease, gene in profiles.primary_disease_gene_pairs:
        if gene in gene_index:
            disease_rows[disease_index[disease]].append(gene_index[gene])
    return PreparedProfiles(
        candidate_ids=profiles.candidate_ids,
        disease_ids=profiles.disease_ids,
        gene_ids=genes,
        gene_weights=weights,
        drug_gene_indices=tuple(tuple(sorted(row)) for row in drug_rows),
        disease_gene_indices=tuple(tuple(sorted(row)) for row in disease_rows),
        drug_gene_pair_count=len(profiles.drug_gene_pairs),
        primary_disease_gene_pair_count=len(profiles.primary_disease_gene_pairs),
        all_disease_gene_pair_count=len(profiles.all_disease_gene_pairs),
    )


def _linear_float32_sum(weights, indices: Sequence[int]):
    """Match CSR row reduction order: ascending column, float32 accumulator."""
    import numpy as np

    value = np.float32(0.0)
    for index in indices:
        value = np.float32(value + weights[index])
    return value


def score_prepared_profiles(prepared: PreparedProfiles):
    """Compute disease × candidate scores with historical float32 order."""
    import numpy as np

    weights = np.asarray(prepared.gene_weights, dtype=np.float32)
    drug_norm = np.asarray(
        [np.sqrt(_linear_float32_sum(weights, row), dtype=np.float32) for row in prepared.drug_gene_indices],
        dtype=np.float32,
    )
    disease_norm = np.asarray(
        [np.sqrt(_linear_float32_sum(weights, row), dtype=np.float32) for row in prepared.disease_gene_indices],
        dtype=np.float32,
    )
    drugs_by_gene: list[list[int]] = [[] for _ in prepared.gene_ids]
    for drug_row, gene_columns in enumerate(prepared.drug_gene_indices):
        for gene_column in gene_columns:
            drugs_by_gene[gene_column].append(drug_row)
    scores = np.zeros((len(prepared.disease_ids), len(prepared.candidate_ids)), dtype=np.float32)
    for disease_row, gene_columns in enumerate(prepared.disease_gene_indices):
        numerator = np.zeros(len(prepared.candidate_ids), dtype=np.float32)
        for gene_column in gene_columns:
            drug_rows = drugs_by_gene[gene_column]
            if drug_rows:
                numerator[drug_rows] = np.float32(numerator[drug_rows] + weights[gene_column])
        denominator = np.float32(disease_norm[disease_row] * drug_norm)
        np.divide(
            numerator,
            denominator,
            out=scores[disease_row],
            where=denominator > 0,
        )
    return scores


def package_run(
    prepared: PreparedProfiles,
    scores,
    *,
    benchmark_id: str,
    runtime_seconds: Mapping[str, float] | None = None,
) -> E1RunResult:
    import numpy as np

    matrix = np.asarray(scores)
    expected_shape = (len(prepared.disease_ids), len(prepared.candidate_ids))
    if matrix.shape != expected_shape or matrix.dtype != np.float32 or not np.isfinite(matrix).all():
        raise ValueError("E1 score matrix has invalid shape, dtype, or values")
    applicable = tuple(
        bool(prepared.disease_gene_indices[row]) and bool(np.any(matrix[row] > 0))
        for row in range(len(prepared.disease_ids))
    )
    reasons = tuple(None if value else ABSTENTION_REASON for value in applicable)
    metadata = {
        "relations_used": list(RELATIONS_USED),
        "uses_therapeutic_labels": False,
        "gene_feature_count": len(prepared.gene_ids),
        "drug_gene_pairs": prepared.drug_gene_pair_count,
        "primary_disease_gene_pairs": prepared.primary_disease_gene_pair_count,
        "all_disease_gene_pairs_for_degree": prepared.all_disease_gene_pair_count,
        "score_dtype": "float32",
        "runtime_seconds": dict(runtime_seconds or {}),
    }
    return E1RunResult(
        expert_id=EXPERT_ID,
        expert_version=EXPERT_VERSION,
        expert_family=EXPERT_FAMILY,
        benchmark_id=benchmark_id,
        candidate_ids=prepared.candidate_ids,
        disease_ids=prepared.disease_ids,
        scores=matrix,
        applicable=applicable,
        abstention_reasons=reasons,
        deterministic=True,
        stochastic=False,
        seed=None,
        metadata=metadata,
    )


def run_e1(
    raw_kg: Path,
    candidate_ids: Sequence[str],
    disease_ids: Sequence[str],
    *,
    benchmark_id: str,
) -> E1RunResult:
    start = time.perf_counter()
    profiles = extract_gene_profiles(raw_kg, candidate_ids, disease_ids)
    extraction_end = time.perf_counter()
    prepared = prepare_profiles(profiles)
    preparation_end = time.perf_counter()
    scores = score_prepared_profiles(prepared)
    scoring_end = time.perf_counter()
    return package_run(
        prepared,
        scores,
        benchmark_id=benchmark_id,
        runtime_seconds={
            "graph_extraction": extraction_end - start,
            "profile_preparation": preparation_end - extraction_end,
            "score_matrix": scoring_end - preparation_end,
            "total": scoring_end - start,
        },
    )


def save_score_archive(run: E1RunResult, path: Path) -> None:
    import numpy as np

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        scores=np.asarray(run.scores, dtype=np.float32),
        disease_ids=np.asarray(run.disease_ids, dtype=str),
        drug_ids=np.asarray(run.candidate_ids, dtype=str),
    )


def compare_scores(run: E1RunResult, historical_archive) -> dict[str, object]:
    import numpy as np

    historical = np.asarray(historical_archive.scores)
    clean = np.asarray(run.scores)
    disease_axis = tuple(historical_archive.disease_ids) == run.disease_ids
    candidate_axis = tuple(historical_archive.drug_ids) == run.candidate_ids
    if historical.shape != clean.shape:
        raise ValueError(f"historical score shape mismatch: {historical.shape} != {clean.shape}")
    if not disease_axis or not candidate_axis:
        raise ValueError("historical score archive axis identity/order mismatch")
    nan_difference = np.isnan(clean) != np.isnan(historical)
    both_nan = np.isnan(clean) & np.isnan(historical)
    unequal = (clean != historical) & ~both_nan
    finite = np.isfinite(clean) & np.isfinite(historical)
    absolute = np.abs(clean[finite].astype(np.float64) - historical[finite].astype(np.float64))
    return {
        "shape": list(clean.shape),
        "dtype_clean": str(clean.dtype),
        "dtype_historical": str(historical.dtype),
        "scores_compared": int(clean.size),
        "candidate_axis_identity": candidate_axis,
        "disease_axis_identity": disease_axis,
        "max_absolute_difference": float(absolute.max()) if absolute.size else 0.0,
        "mean_absolute_difference": float(absolute.mean()) if absolute.size else 0.0,
        "unequal_value_count": int(np.count_nonzero(unequal)),
        "nan_difference_count": int(np.count_nonzero(nan_difference)),
        "bitwise_identical": bool(np.array_equal(clean, historical, equal_nan=True)),
    }


def evaluate_against_frozen(run: E1RunResult, evaluator, matrix_path: Path) -> dict[str, object]:
    """Use the Gate-3 evaluator, then compare every frozen disease metric."""
    import numpy as np

    with Path(matrix_path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if tuple(row["disease_id"] for row in rows) != run.disease_ids:
        raise ValueError("frozen E1 matrix disease axis mismatch")
    frozen_applicable = tuple(row["applicable"].lower() == "true" for row in rows)
    fields = [
        "MRR", "first_hit_rank", "first_contra_rank",
        *[f"{prefix}@{k}" for k in evaluator.k_values for prefix in ("Recall", "Hit", "Contra", "ContraRate")],
        "primary_utility",
    ]
    max_by_field = {field: 0.0 for field in fields}
    mismatches: list[dict[str, object]] = []
    computed_primary: list[float] = []
    frozen_primary: list[float] = []
    for index, row in enumerate(rows):
        actual = evaluator.evaluate(
            run.disease_result(index),
            benchmark_id=run.benchmark_id,
            evaluator_version="1.1_tiesafe",
        )
        for field in fields:
            expected = float(row[field]) if row[field] else math.nan
            observed = float(actual[field])
            if math.isnan(expected) and math.isnan(observed):
                difference = 0.0
            elif math.isfinite(expected) and math.isfinite(observed):
                difference = abs(expected - observed)
            else:
                difference = math.inf
            max_by_field[field] = max(max_by_field[field], difference)
            if difference != 0.0 and len(mismatches) < 20:
                mismatches.append({
                    "disease_id": run.disease_ids[index], "field": field,
                    "frozen": expected, "clean": observed, "difference": difference,
                })
        computed_primary.append(float(actual["Recall@50"]))
        frozen_primary.append(float(row["Recall@50"]))
    clean_macro = float(np.mean(computed_primary))
    frozen_macro = float(np.mean(frozen_primary))
    return {
        "disease_rows": len(rows),
        "applicable_count_clean": int(sum(run.applicable)),
        "applicable_count_frozen": int(sum(frozen_applicable)),
        "applicability_agreement_count": int(sum(a == b for a, b in zip(run.applicable, frozen_applicable))),
        "applicability_exact": run.applicable == frozen_applicable,
        "max_absolute_difference_by_metric": max_by_field,
        "max_absolute_disease_level_difference": max(max_by_field.values()),
        "first_mismatches": mismatches,
        "macro_recall50_clean": clean_macro,
        "macro_recall50_frozen": frozen_macro,
        "macro_recall50_absolute_difference": abs(clean_macro - frozen_macro),
    }
