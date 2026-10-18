"""Frozen v1.1 tie-safe evaluator, independent of all expert algorithms.

Historical lineage: Cell 16; evaluator configuration and metric policy are
hash-verified frozen inputs. Expert matrices are comparison targets only, with
status/applicability metadata admitted when no upstream status archive exists.
"""

from __future__ import annotations

import csv
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .benchmark import FrozenBenchmark, load_frozen_benchmark
from .provenance import load_registry, sha256_file, validate
from .score_archive import load_score_archive


SCORE_TO_MATRIX = {
    "external/p1_e1_weighted_gene_cosine_scores.npz": "reference_results/p1_e1_expert_matrix_v1_1_tiesafe.csv",
    "external/p1_e2_disease_profile_label_transfer_scores.npz": "reference_results/p1_e2_expert_matrix_v1_1_tiesafe.csv",
    **{f"external/p1_e3_complex_seed{s}_scores.npz": f"reference_results/p1_e3_complex_seed{s}_expert_matrix.csv" for s in range(3)},
    **{f"external/p1_e4_rgcn_seed{s}_scores.npz": f"reference_results/p1_e4_rgcn_seed{s}_expert_matrix.csv" for s in range(3)},
}
IGNORED = frozenset({"AMBIGUOUS_INDICATION", "OFFLABEL_ONLY", "CONFLICTING_NONINDICATION"})


@dataclass(frozen=True)
class ExpertScoreResult:
    expert_id: str
    expert_version: str
    disease_id: str
    candidate_ids: tuple[str, ...]
    scores: Sequence[float]
    applicable: bool
    abstention_reason: str | None = None
    seed: int | None = None
    provenance: str | None = None
    benchmark_id: str | None = None
    deterministic: bool | None = None
    metadata: dict[str, Any] | Mapping[str, Any] | None = None


def expected_first_rank_and_mrr(group_size: int, positive_count: int, offset: int) -> tuple[float, float]:
    """Cell 16: minimum positive position distribution in first positive tie."""
    m, p, offset = int(group_size), int(positive_count), int(offset)
    if m < 1 or not 1 <= p <= m or offset < 0:
        raise ValueError("invalid first-positive tie parameters")
    expected_rank = offset + (m + 1) / (p + 1)
    probability = p / m  # P(minimum position = 1)
    expected_reciprocal = 0.0
    probability_sum = 0.0
    for j in range(1, m - p + 2):
        if j > 1:
            previous_j = j - 1
            probability *= (m - previous_j - p + 1) / (m - previous_j)
        expected_reciprocal += probability / (offset + j)
        probability_sum += probability
    if not math.isclose(probability_sum, 1.0, rel_tol=1e-8, abs_tol=1e-8):
        raise ArithmeticError("first-positive probability failed to normalize")
    return float(expected_rank), float(expected_reciprocal)


def hit_probability_in_tie(size: int, positives: int, slots: int) -> float:
    """Exact hypergeometric P(at least one positive), without sampling."""
    if not 0 <= positives <= size or not 0 <= slots <= size:
        raise ValueError("invalid tie sampling parameters")
    if positives == 0 or slots == 0:
        return 0.0
    if slots > size - positives:
        return 1.0
    no_positive = 1.0
    for j in range(slots):
        no_positive *= (size - positives - j) / (size - j)
    return float(1.0 - no_positive)


class TieSafeEvaluator:
    """Evaluate one disease against the canonical drug axis and role policy."""

    def __init__(self, benchmark_id: str, version: str, candidate_ids: Sequence[str], disease_ids: Sequence[str], roles: dict[str, dict[str, str]], k_values: Sequence[int] = (10, 50, 100)):
        self.benchmark_id = benchmark_id
        self.version = version
        self.candidate_ids = tuple(candidate_ids)
        self.disease_ids = tuple(disease_ids)
        self.disease_set = frozenset(disease_ids)
        self.roles = roles
        self.k_values = tuple(int(k) for k in k_values)
        if not self.candidate_ids or len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("candidate axis empty or duplicated")
        if not self.disease_ids or len(set(self.disease_ids)) != len(self.disease_ids):
            raise ValueError("disease axis empty or duplicated")
        if not self.k_values or any(k <= 0 for k in self.k_values) or len(set(self.k_values)) != len(self.k_values):
            raise ValueError("invalid K values")
        if any(role not in IGNORED | {"CLEAN_INDICATION", "CONTRAINDICATION_ONLY"} for disease in roles.values() for role in disease.values()):
            raise ValueError("unexpected evaluation role")

    def evaluate(self, result: ExpertScoreResult, *, benchmark_id: str | None = None, evaluator_version: str | None = None) -> dict[str, float]:
        import numpy as np

        if benchmark_id is not None and benchmark_id != self.benchmark_id:
            raise ValueError("benchmark ID mismatch")
        if evaluator_version is not None and evaluator_version != self.version:
            raise ValueError("evaluator version mismatch")
        if result.disease_id not in self.disease_set:
            raise ValueError("disease ID outside primary axis")
        if len(result.candidate_ids) != len(set(result.candidate_ids)):
            raise ValueError("duplicate candidate ID")
        if result.candidate_ids != self.candidate_ids:
            raise ValueError("candidate axis identity/order mismatch")
        if len(result.scores) != len(self.candidate_ids):
            raise ValueError("score vector length mismatch")
        scores = np.asarray(result.scores, dtype=np.float32)
        if scores.ndim != 1 or np.isnan(scores).any():
            # Cell 16 defines exact ordering but does not define NaN ordering.
            # Reject rather than silently inventing one. +/-inf remain ordered.
            raise ValueError("score vector must be one-dimensional and NaN-free")
        if result.applicable and result.abstention_reason is not None:
            raise ValueError("applicable result cannot have abstention reason")
        if not result.applicable:
            if not result.abstention_reason:
                raise ValueError("explicit abstention requires a reason")
            metrics = {"MRR": 0.0, "first_hit_rank": math.nan, "first_contra_rank": math.nan}
            for k in self.k_values:
                metrics.update({f"Recall@{k}": 0.0, f"Hit@{k}": 0.0, f"Contra@{k}": 0.0, f"ContraRate@{k}": 0.0})
            metrics["primary_utility"] = metrics.get("Recall@50", 0.0)
            return metrics

        role_map = self.roles.get(result.disease_id, {})
        eligible = np.asarray([role_map.get(drug_id) not in IGNORED for drug_id in self.candidate_ids], dtype=bool)
        eligible_idx = np.flatnonzero(eligible)
        ranked = eligible_idx[np.argsort(-scores[eligible_idx], kind="mergesort")]
        ranked_scores = scores[ranked]
        positive = np.asarray([role_map.get(self.candidate_ids[i]) == "CLEAN_INDICATION" for i in ranked], dtype=np.int8)
        contra = np.asarray([role_map.get(self.candidate_ids[i]) == "CONTRAINDICATION_ONLY" for i in ranked], dtype=np.int8)
        positives_total = int(positive.sum())
        if positives_total == 0:
            # The frozen primary cohort has >=3 positives. Cell 16 asserts this.
            raise ValueError("applicable disease has no evaluable CLEAN truth")
        n = len(ranked)
        starts = np.r_[0, np.flatnonzero(ranked_scores[1:] != ranked_scores[:-1]) + 1]
        ends = np.r_[starts[1:], n]
        expected_pos = {k: 0.0 for k in self.k_values}
        expected_contra = {k: 0.0 for k in self.k_values}
        hit = {k: None for k in self.k_values}
        first_hit = mrr = first_contra = None
        positives_before = 0
        for start, end in zip(starts, ends):
            start, end = int(start), int(end)
            m = end - start
            p = int(positive[start:end].sum())
            c = int(contra[start:end].sum())
            if first_hit is None and p:
                first_hit, mrr = expected_first_rank_and_mrr(m, p, start)
            if first_contra is None and c:
                first_contra, _ = expected_first_rank_and_mrr(m, c, start)
            for k in self.k_values:
                cutoff = min(k, n)  # Small-fixture extension; frozen N > 100.
                if start >= cutoff:
                    continue
                slots = min(m, cutoff - start)
                expected_pos[k] += slots * p / m
                expected_contra[k] += slots * c / m
                if start < cutoff <= end:
                    hit[k] = 1.0 if positives_before else hit_probability_in_tie(m, p, slots)
            positives_before += p
            if end >= min(max(self.k_values), n) and first_hit is not None and (first_contra is not None or not contra.any()):
                break
        if first_hit is None or mrr is None or any(value is None for value in hit.values()):
            raise ArithmeticError("tie-safe metric unresolved")
        metrics = {"MRR": float(mrr), "first_hit_rank": float(first_hit), "first_contra_rank": float(first_contra) if first_contra is not None else math.nan}
        for k in self.k_values:
            metrics.update({f"Recall@{k}": expected_pos[k] / positives_total, f"Hit@{k}": float(hit[k]), f"Contra@{k}": expected_contra[k], f"ContraRate@{k}": expected_contra[k] / k})
        metrics["primary_utility"] = metrics.get("Recall@50", 0.0)
        return metrics


def load_frozen_evaluator(registry_path: Path, frozen_root: Path) -> tuple[TieSafeEvaluator, dict]:
    """Gate-1 hash boundary for benchmark, roles, policy and config."""
    registry = load_registry(registry_path)
    gate1 = validate(registry_path, frozen_root, "REFERENCE")
    benchmark: FrozenBenchmark = load_frozen_benchmark(registry_path, frozen_root, gate1)
    by_id = {item["artifact_id"]: item for item in registry["artifacts"]}
    def verified_json(artifact_id: str) -> dict:
        item = by_id[artifact_id]
        path = frozen_root / item["logical_path"]
        if sha256_file(path) != item["expected_sha256"]:
            raise ValueError(f"frozen evaluator input hash mismatch: {artifact_id}")
        return json.loads(path.read_text(encoding="utf-8"))
    config = verified_json("benchmark/p1_v0_evaluator_config_v1_1_tiesafe.json")
    policy = verified_json("recovered_contracts/p1_primary_metric_policy.json")
    if config["benchmark_id"] != benchmark.benchmark_id or config["evaluator_version"] != "1.1_tiesafe":
        raise ValueError("frozen evaluator identity mismatch")
    if tuple(config["ignored_before_metric_evaluation"]) != tuple(sorted(IGNORED)) or set(policy["ignored_primary_roles"]) != IGNORED:
        raise ValueError("frozen ignored-role policy mismatch")
    if config["candidate_universe"] != len(benchmark.candidate_ids) or config["primary_utility"] != "Recall@50":
        raise ValueError("frozen candidate/primary metric policy mismatch")
    if policy["primary_positive"] != "CLEAN_INDICATION" or policy["scored_but_not_true_negative_roles"] != ["CONTRAINDICATION_ONLY", "UNOBSERVED"]:
        raise ValueError("frozen label policy mismatch")
    role_path = frozen_root / "benchmark/p1_v0_primary_eval_roles.csv"
    role_item = by_id["benchmark/p1_v0_primary_eval_roles.csv"]
    if sha256_file(role_path) != role_item["expected_sha256"]:
        raise ValueError("primary evaluation roles hash mismatch")
    with role_path.open(newline="", encoding="utf-8") as handle:
        role_rows = list(csv.DictReader(handle))
    roles: dict[str, dict[str, str]] = {}
    for row in role_rows:
        disease_roles = roles.setdefault(row["disease_id"], {})
        if row["drug_id"] in disease_roles:
            raise ValueError("duplicate primary role pair")
        disease_roles[row["drug_id"]] = row["evaluation_role"]
    evaluator = TieSafeEvaluator(benchmark.benchmark_id, config["evaluator_version"], benchmark.candidate_ids, [d for d, _ in benchmark.disease_folds], roles, config["k_values"])
    if any(sum(role == "CLEAN_INDICATION" for role in roles.get(d, {}).values()) < 3 for d in evaluator.disease_ids):
        raise ValueError("frozen primary disease lacks three CLEAN positives")
    return evaluator, {"configuration": config, "metric_policy": policy, "gate1_overall": gate1["overall"]}


def reproduce_archive(score_id: str, score_path: Path, frozen_root: Path, registry_path: Path, evaluator: TieSafeEvaluator, *, tolerance: float = 1e-12) -> dict:
    """Recompute every disease metric from raw NPZ scores, then compare matrix."""
    import numpy as np

    if score_id not in SCORE_TO_MATRIX:
        raise ValueError("unregistered score archive")
    registry = load_registry(registry_path)
    by_id = {item["artifact_id"]: item for item in registry["artifacts"]}
    score_item = by_id[score_id]
    if score_item.get("expected_size") and score_path.stat().st_size != score_item["expected_size"]:
        raise ValueError("score archive size mismatch")
    observed_sha = sha256_file(score_path)
    if score_item.get("expected_sha256") and observed_sha != score_item["expected_sha256"]:
        raise ValueError("score archive hash mismatch")
    matrix_id = SCORE_TO_MATRIX[score_id]
    matrix_item = by_id[matrix_id]
    matrix_path = frozen_root / matrix_item["logical_path"]
    if sha256_file(matrix_path) != matrix_item["expected_sha256"]:
        raise ValueError("frozen expert matrix hash mismatch")
    with matrix_path.open(newline="", encoding="utf-8") as handle:
        matrix = list(csv.DictReader(handle))
    archive = load_score_archive(score_path)
    scores = np.asarray(archive.scores, dtype=np.float32)
    diseases = archive.disease_ids
    drugs = archive.drug_ids
    if scores.shape != (len(evaluator.disease_ids), len(evaluator.candidate_ids)):
        raise ValueError("score matrix shape mismatch")
    if diseases != evaluator.disease_ids or drugs != evaluator.candidate_ids:
        raise ValueError("score archive disease or candidate axis mismatch")
    if tuple(row["disease_id"] for row in matrix) != evaluator.disease_ids:
        raise ValueError("reference matrix disease axis mismatch")
    fields = ["MRR", "first_hit_rank", "first_contra_rank", *[f"{prefix}@{k}" for k in evaluator.k_values for prefix in ("Recall", "Hit", "Contra", "ContraRate")], "primary_utility"]
    max_by_field = {field: 0.0 for field in fields}
    mismatches = []
    computed_primary = []
    reference_primary = []
    status_counts: dict[str, int] = {}
    for i, row in enumerate(matrix):
        if row["benchmark_id"] != evaluator.benchmark_id or row["evaluator_version"] != evaluator.version:
            raise ValueError("reference matrix identity/version mismatch")
        applicable = row["applicable"].lower() == "true"
        status = row["status"]
        if (status == "OK") != applicable:
            raise ValueError("reference status/applicability contradiction")
        status_counts[status] = status_counts.get(status, 0) + 1
        result = ExpertScoreResult(row["expert_id"], row["expert_version"], diseases[i], drugs, scores[i], applicable, None if applicable else status, int(row["seed"]) if row["seed"] else None, score_id)
        actual = evaluator.evaluate(result, benchmark_id=row["benchmark_id"], evaluator_version=row["evaluator_version"])
        for field in fields:
            if field not in row:
                continue
            expected = float(row[field]) if row[field] else math.nan
            observed = actual[field]
            if math.isnan(expected) and math.isnan(observed):
                continue
            difference = abs(expected - observed) if math.isfinite(expected) and math.isfinite(observed) else math.inf
            max_by_field[field] = max(max_by_field[field], difference)
            if difference > tolerance and len(mismatches) < 20:
                mismatches.append({"disease_id": diseases[i], "field": field, "expected": expected, "computed": observed, "difference": difference})
        computed_primary.append(actual["Recall@50"])
        reference_primary.append(float(row["Recall@50"]))
    macro_computed = float(np.mean(computed_primary))
    macro_reference = float(np.mean(reference_primary))
    macro_difference = abs(macro_computed - macro_reference)
    return {"score_artifact_id": score_id, "score_path": str(score_path), "score_observed_sha256": observed_sha, "score_registry_sha256_status": "VERIFIED" if score_item.get("expected_sha256") else "UNKNOWN_HASH", "score_registry_size_verified": bool(score_item.get("expected_size")), "reference_matrix_artifact_id": matrix_id, "reference_matrix_sha256_verified": True, "candidate_axis_verified": True, "disease_axis_verified": True, "applicability_source": "frozen expert matrix status/applicable metadata (no separate upstream status archive)", "status_counts": status_counts, "disease_rows": len(matrix), "numeric_tolerance": tolerance, "max_absolute_difference_by_metric": max_by_field, "max_absolute_difference": max(max_by_field.values()), "first_mismatches": mismatches, "macro_recall50_computed": macro_computed, "macro_recall50_frozen_matrix": macro_reference, "macro_recall50_absolute_difference": macro_difference, "status": "PASS" if not mismatches and macro_difference <= tolerance else "FAIL"}


def evaluator_formula_self_checks() -> dict:
    """Command-surface checks, including independent tiny exhaustive rankings."""
    rank, mrr = expected_first_rank_and_mrr(4, 1, 0)
    checks = {"single_positive_four_way_tie_expected_rank": rank == 2.5, "single_positive_four_way_tie_mrr": math.isclose(mrr, (1 + 1/2 + 1/3 + 1/4) / 4, abs_tol=1e-15), "two_positive_half_block_hit": math.isclose(hit_probability_in_tie(4, 2, 2), 5/6, abs_tol=1e-15)}
    axes = ("A", "B", "C", "D")
    permutations_enumerated = 0
    for positives in ({"A"}, {"A", "B"}):
        roles = {drug: "CLEAN_INDICATION" for drug in positives}
        roles["C" if "C" not in positives else "D"] = "CONTRAINDICATION_ONLY"
        evaluator = TieSafeEvaluator("fixture", "1.1_tiesafe", axes, ("d",), {"d": roles}, (1, 2, 4))
        analytic = evaluator.evaluate(ExpertScoreResult("fixture", "0", "d", axes, (0, 0, 0, 0), True))
        rankings = list(itertools.permutations(axes))
        permutations_enumerated += len(rankings)
        for k in evaluator.k_values:
            brute_recall = sum(sum(drug in positives for drug in ranking[:k]) / len(positives) for ranking in rankings) / len(rankings)
            brute_hit = sum(any(drug in positives for drug in ranking[:k]) for ranking in rankings) / len(rankings)
            checks[f"enumerated_{len(positives)}positives_Recall@{k}"] = math.isclose(analytic[f"Recall@{k}"], brute_recall, abs_tol=1e-15)
            checks[f"enumerated_{len(positives)}positives_Hit@{k}"] = math.isclose(analytic[f"Hit@{k}"], brute_hit, abs_tol=1e-15)
        brute_first = sum(next(i + 1 for i, drug in enumerate(ranking) if drug in positives) for ranking in rankings) / len(rankings)
        brute_mrr = sum(1 / next(i + 1 for i, drug in enumerate(ranking) if drug in positives) for ranking in rankings) / len(rankings)
        checks[f"enumerated_{len(positives)}positives_first_hit"] = math.isclose(analytic["first_hit_rank"], brute_first, abs_tol=1e-15)
        checks[f"enumerated_{len(positives)}positives_MRR"] = math.isclose(analytic["MRR"], brute_mrr, abs_tol=1e-15)
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "permutations_enumerated": permutations_enumerated}
