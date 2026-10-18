"""Gate-5 orchestration for deterministic fold-legal E2 equivalence."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from .benchmark import load_frozen_benchmark
from .evaluation import load_frozen_evaluator, reproduce_archive
from .experts.e1_gene_similarity import compare_scores, evaluate_against_frozen
from .experts.e2_disease_transfer import (
    extract_disease_feature_corpus,
    prepare_e2_from_corpus,
    save_score_archive,
    score_e2_prepared,
)
from .provenance import load_registry, sha256_file, validate
from .reconstruction import verified_raw_path
from .score_archive import load_score_archive


E2_SCORE_ID = "external/p1_e2_disease_profile_label_transfer_scores.npz"
E2_MATRIX_ID = "reference_results/p1_e2_expert_matrix_v1_1_tiesafe.csv"
E2_SOURCE_ID = "source/authoritative/E2_authoritative.py"
EXPECTED_FOLD_COUNTS = (6856, 6828, 6990, 7119, 6871, 7183, 7091, 6827)


def _commit_identity(root: Path) -> tuple[str | None, str]:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None, "UNAVAILABLE_NOT_GIT_CHECKOUT"
    return value, "RECORDED"


def _sparse_bitwise_equal(left, right) -> bool:
    import numpy as np

    return (
        left.shape == right.shape
        and left.dtype == right.dtype
        and np.array_equal(left.indptr, right.indptr)
        and np.array_equal(left.indices, right.indices)
        and np.array_equal(left.data, right.data)
    )


def reproduce_e2_gate5(
    *,
    root: Path,
    registry_path: Path,
    frozen_root: Path,
    raw_kg: Path | None,
    historical_score: Path,
    historical_source: Path,
    generated_score: Path,
) -> dict:
    import numpy as np

    registry = load_registry(registry_path)
    by_id = {item["artifact_id"]: item for item in registry["artifacts"]}
    score_item, source_item, matrix_item = by_id[E2_SCORE_ID], by_id[E2_SOURCE_ID], by_id[E2_MATRIX_ID]
    report: dict[str, object] = {
        "gate": "PHASE_2_GATE_5",
        "scope": "E2_DISEASE_PROFILE_LABEL_TRANSFER exact score/applicability/metric reproduction only",
        "expert_id": "E2_DISEASE_PROFILE_LABEL_TRANSFER",
        "expert_version": "1.0",
        "benchmark_id": registry["benchmark"]["id"],
        "masking_protocol": registry["benchmark"]["masking_protocol"],
        "evaluator_version": "1.1_tiesafe",
        "historical_source_reference": "Cell 17 / source/authoritative/E2_authoritative.py",
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
            raise ValueError("historical Cell-17 source hash mismatch")
        report["historical_source_sha256"] = observed_source
        commit, commit_state = _commit_identity(root)
        report["clean_implementation_commit"] = commit
        report["clean_implementation_commit_state"] = commit_state
        implementation_files = (
            "src/primekg_repurposing/experts/e2_disease_transfer.py",
            "src/primekg_repurposing/gate5.py",
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
            raise ValueError("recovered E2 score archive hash mismatch")
        if historical_size != score_item["recovery_time_observed_size"]:
            raise ValueError("recovered E2 score archive size mismatch")
        historical = load_score_archive(historical_score)
        report["historical_score_archive"] = {
            "artifact_id": E2_SCORE_ID,
            "observed_sha256": historical_hash,
            "observed_size": historical_size,
            "hash_classification": "RECOVERY_TIME_OBSERVED",
            "historical_hash_verified": False,
            "schema_arrays": ["scores", "disease_ids", "drug_ids"],
        }

        gate1 = validate(registry_path, frozen_root, "REFERENCE")
        benchmark = load_frozen_benchmark(registry_path, frozen_root, gate1)
        evaluator, evaluator_contract = load_frozen_evaluator(registry_path, frozen_root)
        report["candidate_count"] = len(benchmark.candidate_ids)
        report["disease_count"] = len(benchmark.disease_folds)

        extraction_start = time.perf_counter()
        corpus = extract_disease_feature_corpus(raw)
        extraction_end = time.perf_counter()
        first_prepared = prepare_e2_from_corpus(corpus, benchmark)
        first_prepared_end = time.perf_counter()
        second_prepared = prepare_e2_from_corpus(corpus, benchmark)
        second_prepared_end = time.perf_counter()
        first_run = score_e2_prepared(first_prepared, benchmark)
        first_score_end = time.perf_counter()
        second_run = score_e2_prepared(second_prepared, benchmark)
        second_score_end = time.perf_counter()
        profiles_identical = _sparse_bitwise_equal(first_prepared.profiles.matrix, second_prepared.profiles.matrix)
        similarity_identical = _sparse_bitwise_equal(first_prepared.similarity, second_prepared.similarity)
        scores_identical = bool(np.array_equal(first_run.scores, second_run.scores))
        applicability_identical = first_run.applicable == second_run.applicable
        report["determinism"] = {
            "repeated_profile_construction_bitwise_identical": profiles_identical,
            "repeated_similarity_bitwise_identical": similarity_identical,
            "repeated_score_computation_bitwise_identical": scores_identical,
            "repeated_applicability_identical": applicability_identical,
            "stochastic": False,
            "scientific_seed_required": False,
        }
        report["runtime_seconds"] = {
            "graph_profile_extraction": extraction_end - extraction_start,
            "first_profile_and_similarity": first_prepared_end - extraction_end,
            "repeat_profile_and_similarity": second_prepared_end - first_prepared_end,
            "first_fold_scoring": first_score_end - second_prepared_end,
            "repeat_fold_scoring": second_score_end - first_score_end,
            "total": second_score_end - extraction_start,
        }
        run = first_run
        report["applicable_count"] = int(sum(run.applicable))
        report["abstention_count"] = len(run.applicable) - int(sum(run.applicable))
        report["status_counts"] = {
            status: run.statuses.count(status) for status in sorted(set(run.statuses))
        }
        report["fold_legal_clean_counts"] = list(run.fold_legal_clean_counts)
        report["fold_legal_clean_counts_expected"] = list(EXPECTED_FOLD_COUNTS)
        report["feature_space_summary"] = {
            "all_diseases_in_idf_corpus": first_prepared.profiles.all_disease_count,
            "features": len(first_prepared.profiles.feature_ids),
            "unique_disease_feature_pairs": first_prepared.feature_pair_count,
            "relevant_primary_or_label_diseases": len(first_prepared.profiles.relevant_disease_ids),
            "global_clean_training_pairs": len(first_prepared.global_clean_pairs),
            "global_label_diseases": len(first_prepared.label_disease_ids),
            "similarity_shape": list(first_prepared.similarity.shape),
            "nonzero_similarities": int(first_prepared.similarity.nnz),
        }
        report["relation_types_used"] = list(first_prepared.relation_types)
        report["tfidf_configuration"] = {
            "term_frequency": "binary presence after pair deduplication",
            "document_count": "all PrimeKG diseases with at least one incident nontherapeutic feature",
            "idf": "ln((1 + N_all_diseases) / (1 + document_frequency)) + 1",
            "idf_dtype": "float32",
            "normalization": "L2",
            "matrix": "SciPy CSR float32",
            "similarity": "full cosine; no threshold and no top-k truncation",
            "feature_token": "relation|neighbor_type|neighbor_id",
            "direction_encoded": False,
            "ontology_features_included": "disease_disease|disease|neighbor_id",
        }
        report["label_transfer_configuration"] = {
            "positive_role": "CLEAN_INDICATION only",
            "legal_source": "Gate-2 benchmark.mask(fold).legal_clean_pairs",
            "target_and_buffer_labels_excluded_before_transfer": True,
            "formula": "sum_j(sim(q,j) * clean_label(j,drug)) / sum_j(sim(q,j))",
            "knn_cutoff": None,
            "score_dtype": "float32",
        }
        report["applicability_rule"] = [
            "ABSTAIN_NO_NONTHERAPEUTIC_PROFILE when query feature count is zero",
            "ABSTAIN_NO_SIMILAR_TRAINING_DISEASE when legal similarity nnz is zero or mass <= 0",
            "ABSTAIN_NO_TRANSFERABLE_INDICATION when positive score coverage is zero",
            "OK otherwise",
        ]
        report["score_equivalence"] = compare_scores(run, historical)

        matrix_path = frozen_root / matrix_item["logical_path"]
        if sha256_file(matrix_path) != matrix_item["expected_sha256"]:
            raise ValueError("frozen E2 matrix hash mismatch")
        evaluation = evaluate_against_frozen(run, evaluator, matrix_path)
        historical_evaluation = reproduce_archive(
            E2_SCORE_ID, historical_score, frozen_root, registry_path, evaluator
        )
        evaluation["historical_archive_gate3_status"] = historical_evaluation["status"]
        evaluation["historical_archive_gate3_max_absolute_difference"] = historical_evaluation["max_absolute_difference"]
        evaluation["evaluator_configuration_gate1_status"] = evaluator_contract["gate1_overall"]
        report["evaluator_equivalence"] = evaluation

        save_score_archive(run, generated_score)
        report["generated_score_archive"] = {
            "logical_path": "artifacts/generated/e2/p1_e2_disease_profile_label_transfer_scores_clean.npz",
            "sha256": sha256_file(generated_score),
            "size": generated_score.stat().st_size,
        }
        score_equivalence = report["score_equivalence"]
        deterministic = report["determinism"]
        repeatability_ok = all(
            deterministic[field]
            for field in (
                "repeated_profile_construction_bitwise_identical",
                "repeated_similarity_bitwise_identical",
                "repeated_score_computation_bitwise_identical",
                "repeated_applicability_identical",
            )
        ) and not deterministic["stochastic"] and not deterministic["scientific_seed_required"]
        status = (
            repeatability_ok
            and report["applicable_count"] == 712
            and report["abstention_count"] == 26
            and tuple(run.fold_legal_clean_counts) == EXPECTED_FOLD_COUNTS
            and score_equivalence["candidate_axis_identity"]
            and score_equivalence["disease_axis_identity"]
            and score_equivalence["unequal_value_count"] == 0
            and score_equivalence["nan_difference_count"] == 0
            and evaluation["applicability_exact"]
            and evaluation["macro_recall50_absolute_difference"] <= 2e-16
            and evaluation["max_absolute_disease_level_difference"] <= 2e-15
            and historical_evaluation["status"] == "PASS"
        )
        report["numeric_acceptance"] = {
            "score_requirement": "all stored float32 values exactly equal",
            "metric_tolerance": 2e-15,
            "macro_tolerance": 2e-16,
            "metric_tolerance_basis": "CSV decimal round-trip of frozen Cell-17 metrics; scores are bitwise exact",
        }
        report["overall_status"] = "PASS" if status else "FAIL"
    except (OSError, ValueError, KeyError, ArithmeticError) as exc:
        report["overall_status"] = "FAIL"
        report["error"] = str(exc)
    return report


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
