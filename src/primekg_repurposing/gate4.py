"""Gate-4 orchestration for deterministic E1 equivalence evidence."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from .evaluation import load_frozen_evaluator, reproduce_archive
from .experts.e1_gene_similarity import (
    compare_scores,
    evaluate_against_frozen,
    extract_gene_profiles,
    package_run,
    prepare_profiles,
    save_score_archive,
    score_prepared_profiles,
)
from .provenance import load_registry, sha256_file
from .reconstruction import verified_raw_path
from .score_archive import load_score_archive


E1_SCORE_ID = "external/p1_e1_weighted_gene_cosine_scores.npz"
E1_MATRIX_ID = "reference_results/p1_e1_expert_matrix_v1_1_tiesafe.csv"
E1_SOURCE_ID = "source/authoritative/E1_authoritative.py"


def _commit_identity(root: Path) -> tuple[str | None, str]:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None, "UNAVAILABLE_NOT_GIT_CHECKOUT"
    return value, "RECORDED"


def reproduce_e1_gate4(
    *,
    root: Path,
    registry_path: Path,
    frozen_root: Path,
    raw_kg: Path | None,
    historical_score: Path,
    historical_source: Path,
    generated_score: Path,
) -> dict:
    """Run the sole Gate-4 workflow and return a machine-readable report."""
    import numpy as np

    registry = load_registry(registry_path)
    by_id = {item["artifact_id"]: item for item in registry["artifacts"]}
    score_item, source_item, matrix_item = by_id[E1_SCORE_ID], by_id[E1_SOURCE_ID], by_id[E1_MATRIX_ID]
    report: dict[str, object] = {
        "gate": "PHASE_2_GATE_4",
        "scope": "E1_WEIGHTED_GENE_COSINE exact score/applicability/metric reproduction only",
        "expert_id": "E1_WEIGHTED_GENE_COSINE",
        "expert_version": "1.0",
        "benchmark_id": registry["benchmark"]["id"],
        "evaluator_version": "1.1_tiesafe",
        "historical_source_reference": "Cell 14 / source/authoritative/E1_authoritative.py",
        "historical_source_sha256": None,
        "clean_implementation_commit": None,
        "clean_implementation_commit_state": None,
        "input_primekg_sha256": None,
        "candidate_count": 0,
        "disease_count": 0,
        "applicable_count": 0,
        "abstention_count": 0,
        "historical_score_archive": {},
        "score_equivalence": {},
        "evaluator_equivalence": {},
        "determinism": {},
        "overall_status": "NOT_RUN",
    }
    try:
        observed_source = sha256_file(historical_source)
        if observed_source != source_item["expected_sha256"]:
            raise ValueError("historical Cell-14 source hash mismatch")
        report["historical_source_sha256"] = observed_source
        commit, commit_state = _commit_identity(root)
        report["clean_implementation_commit"] = commit
        report["clean_implementation_commit_state"] = commit_state
        implementation_files = (
            "src/primekg_repurposing/experts/e1_gene_similarity.py",
            "src/primekg_repurposing/gate4.py",
            "src/primekg_repurposing/score_archive.py",
        )
        report["clean_implementation_file_sha256"] = {
            logical: sha256_file(root / logical) for logical in implementation_files
        }

        raw, raw_report = verified_raw_path(registry_path, frozen_root, raw_kg)
        if raw is None:
            raise ValueError(f"registered raw PrimeKG unavailable: {raw_report['status']}")
        report["input_primekg_sha256"] = raw_report["observed_sha256"]
        report["input_primekg_size"] = raw.stat().st_size

        historical_hash = sha256_file(historical_score)
        historical_size = historical_score.stat().st_size
        if historical_hash != score_item["recovery_time_observed_sha256"]:
            raise ValueError("recovered E1 score archive hash mismatch")
        if historical_size != score_item["recovery_time_observed_size"]:
            raise ValueError("recovered E1 score archive size mismatch")
        historical = load_score_archive(historical_score)
        report["historical_score_archive"] = {
            "artifact_id": E1_SCORE_ID,
            "observed_sha256": historical_hash,
            "observed_size": historical_size,
            "hash_classification": "RECOVERY_TIME_OBSERVED",
            "historical_hash_verified": False,
            "schema_arrays": ["scores", "disease_ids", "drug_ids"],
        }

        evaluator, evaluator_contract = load_frozen_evaluator(registry_path, frozen_root)
        report["candidate_count"] = len(evaluator.candidate_ids)
        report["disease_count"] = len(evaluator.disease_ids)
        extraction_start = time.perf_counter()
        profiles = extract_gene_profiles(raw, evaluator.candidate_ids, evaluator.disease_ids)
        extraction_end = time.perf_counter()
        prepared = prepare_profiles(profiles)
        preparation_end = time.perf_counter()
        first_scores = score_prepared_profiles(prepared)
        first_end = time.perf_counter()
        second_scores = score_prepared_profiles(prepared)
        second_end = time.perf_counter()
        runtime = {
            "graph_extraction": extraction_end - extraction_start,
            "profile_preparation": preparation_end - extraction_end,
            "first_score_matrix": first_end - preparation_end,
            "repeat_score_matrix": second_end - first_end,
            "total": second_end - extraction_start,
        }
        run = package_run(prepared, first_scores, benchmark_id=evaluator.benchmark_id, runtime_seconds=runtime)
        repeat_identical = bool(np.array_equal(first_scores, second_scores))
        report["determinism"] = {
            "repeated_score_computation_bitwise_identical": repeat_identical,
            "stochastic": False,
            "scientific_seed_required": False,
        }
        report["applicable_count"] = int(sum(run.applicable))
        report["abstention_count"] = len(run.applicable) - int(sum(run.applicable))
        report["information_contract"] = {
            "relations_consumed": ["disease_protein", "drug_protein"],
            "therapeutic_labels_consumed": False,
            "disease_ontology_consumed": False,
            "reciprocal_duplicates": "canonical pair set",
            "drug_degree_scope": "frozen candidate drugs only",
            "disease_degree_scope": "all PrimeKG diseases",
            "profile_values": "binary",
            "score_dtype": "float32",
            "applicability_rule": "disease_gene_count > 0 and positive_candidate_count > 0",
        }
        report["profile_counts"] = dict(run.metadata)
        report["score_equivalence"] = compare_scores(run, historical)

        matrix_path = frozen_root / matrix_item["logical_path"]
        if sha256_file(matrix_path) != matrix_item["expected_sha256"]:
            raise ValueError("frozen E1 matrix hash mismatch")
        evaluation = evaluate_against_frozen(run, evaluator, matrix_path)
        historical_evaluation = reproduce_archive(
            E1_SCORE_ID, historical_score, frozen_root, registry_path, evaluator
        )
        evaluation["historical_archive_gate3_status"] = historical_evaluation["status"]
        evaluation["historical_archive_gate3_max_absolute_difference"] = historical_evaluation["max_absolute_difference"]
        evaluation["evaluator_configuration_gate1_status"] = evaluator_contract["gate1_overall"]
        report["evaluator_equivalence"] = evaluation

        save_score_archive(run, generated_score)
        report["generated_score_archive"] = {
            "logical_path": "artifacts/generated/e1/p1_e1_weighted_gene_cosine_scores_clean.npz",
            "sha256": sha256_file(generated_score),
            "size": generated_score.stat().st_size,
        }
        score_equivalence = report["score_equivalence"]
        status = (
            repeat_identical
            and report["applicable_count"] == 504
            and report["abstention_count"] == 234
            and score_equivalence["candidate_axis_identity"]
            and score_equivalence["disease_axis_identity"]
            and score_equivalence["unequal_value_count"] == 0
            and score_equivalence["nan_difference_count"] == 0
            and evaluation["applicability_exact"]
            and evaluation["macro_recall50_absolute_difference"] == 0.0
            and evaluation["max_absolute_disease_level_difference"] <= 2e-15
            and historical_evaluation["status"] == "PASS"
        )
        report["numeric_acceptance"] = {
            "score_requirement": "all stored float32 values exactly equal",
            "metric_tolerance": 2e-15,
            "metric_tolerance_basis": "CSV decimal round-trip of frozen Cell-16 metrics; score and macro comparisons remain exact",
        }
        report["overall_status"] = "PASS" if status else "FAIL"
    except (OSError, ValueError, KeyError, ArithmeticError) as exc:
        report["overall_status"] = "FAIL"
        report["error"] = str(exc)
    return report


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
