"""Read-only Gate 6C-A input checks; no scores, aggregation, fitting or training.

Run from an installed checkout: python scripts/gate6c_audit.py
Outputs are new audit reports, never frozen reference files.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

from primekg_repurposing.benchmark import load_frozen_benchmark, validate_frozen_semantics
from primekg_repurposing.evaluation import IGNORED, load_frozen_evaluator
from primekg_repurposing.provenance import axis_sha256, sha256_file, validate

ROOT = Path(__file__).resolve().parents[1]
SPECS = [
    ("p1_e1_expert_matrix_v1_1_tiesafe.csv", "E1_WEIGHTED_GENE_COSINE", 0, 504),
    ("p1_e2_expert_matrix_v1_1_tiesafe.csv", "E2_DISEASE_PROFILE_LABEL_TRANSFER", 0, 712),
    *[(f"p1_e3_complex_seed{s}_expert_matrix.csv", "E3_COMPLEX_KGE", s, 736) for s in range(3)],
    *[(f"p1_e4_rgcn_seed{s}_expert_matrix.csv", "E4_RGCN_LINK_PREDICTION", s, 736) for s in range(3)],
]


def check_rows(rows, evaluator, disease_folds, expert, seed, legal_counts):
    """Check matrix contracts independently of already verified file hashes."""
    if tuple(r["disease_id"] for r in rows) != evaluator.disease_ids:
        raise ValueError("matrix disease axis identity/order mismatch")
    statuses = Counter()
    zero_metrics = ["primary_utility", "MRR"] + [
        f"{metric}@{k}" for k in evaluator.k_values
        for metric in ("Recall", "Hit", "Contra", "ContraRate")
    ]
    unit_metrics = ["MRR"] + [f"{metric}@{k}" for k in evaluator.k_values for metric in ("Recall", "Hit", "ContraRate")]
    for row in rows:
        if (row["benchmark_id"], row["evaluator_version"], row["expert_id"], row["expert_version"], row["seed"], row["primary_utility_name"]) != (
            evaluator.benchmark_id, evaluator.version, expert, "1.0", str(seed), "Recall@50"
        ):
            raise ValueError("matrix expert/seed/evaluation identity mismatch")
        disease = row["disease_id"]
        if int(row["fold"]) != disease_folds[disease]:
            raise ValueError("matrix fold mismatch")
        if row["applicable"] not in ("True", "False"):
            raise ValueError("matrix applicability is not explicit boolean")
        applicable = row["applicable"] == "True"
        if (row["status"] == "OK") != applicable or (not applicable and not row["status"].startswith("ABSTAIN_")):
            raise ValueError("matrix status/applicability contradiction")
        statuses[row["status"]] += 1
        for metric in unit_metrics:
            value = float(row[metric])
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("matrix metric outside finite unit interval")
        if float(row["primary_utility"]) != float(row["Recall@50"]):
            raise ValueError("primary utility differs from Recall@50")
        if not applicable:
            if any(float(row[m]) != 0 for m in zero_metrics):
                raise ValueError("abstention has nonzero metric")
            # Historical CSV serialization represents missing NaN ranks as blanks.
            if any(row[m] != "" and not math.isnan(float(row[m])) for m in ("first_hit_rank", "first_contra_rank")):
                raise ValueError("abstention has non-NaN first-event rank")
        roles = Counter(evaluator.roles[disease].values())
        expected_counts = {
            "n_clean_positives": roles["CLEAN_INDICATION"],
            "n_ignored_candidates": sum(roles[r] for r in IGNORED),
            "n_contraindications": roles["CONTRAINDICATION_ONLY"],
            "n_scored_candidates": len(evaluator.candidate_ids) - sum(roles[r] for r in IGNORED),
            "training_clean_pairs_fold": legal_counts[int(row["fold"])],
        }
        for column, expected in expected_counts.items():
            if column in row and int(row[column]) != expected:
                raise ValueError(f"matrix {column} mismatch")
    return dict(statuses)


def audit_inputs(root=ROOT):
    frozen = root / "artifacts/frozen"
    registry_path = root / "artifacts/registry.json"
    registry = json.loads(registry_path.read_text())
    gate1 = validate(registry_path, frozen, "REFERENCE")
    if gate1["required_failure"]:
        raise ValueError("Gate-1 reference validation failed")
    benchmark = load_frozen_benchmark(registry_path, frozen, gate1)
    semantics = validate_frozen_semantics(benchmark)
    if semantics["status"] != "PASS":
        raise ValueError("frozen benchmark semantic validation failed")
    evaluator, evaluation_contract = load_frozen_evaluator(registry_path, frozen)
    folds = dict(benchmark.disease_folds)
    legal = {fold: len(benchmark.mask(fold).legal_clean_pairs) for fold in range(8)}
    by_id = {a["artifact_id"]: a for a in registry["artifacts"]}
    results = []
    groups = {}
    for filename, expert, seed, expected_applicable in SPECS:
        artifact_id = "reference_results/" + filename
        path = frozen / artifact_id
        item = by_id[artifact_id]
        if sha256_file(path) != item["expected_sha256"]:
            raise ValueError(f"matrix hash mismatch: {artifact_id}")
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        statuses = check_rows(rows, evaluator, folds, expert, seed, legal)
        if statuses.get("OK", 0) != expected_applicable:
            raise ValueError("matrix applicability census mismatch")
        signature = [(r["status"], r["applicable"]) for r in rows]
        if expert in groups and groups[expert] != signature:
            raise ValueError("status/applicability differs across seeds")
        groups[expert] = signature
        results.append({
            "artifact_id": artifact_id, "sha256": item["expected_sha256"],
            "hash_classification": "FROZEN_REGISTRY_REFERENCE", "expert_id": expert,
            "seed": seed, "rows": len(rows), "disease_axis": "PASS", "folds": "PASS",
            "metadata": "PASS", "role_counts_where_present": "PASS",
            "status_counts": statuses, "abstention_metrics": "PASS",
            "matrix_candidate_axis": "NOT_STORED_IN_METRIC_CSV",
        })
    no_expert = sum(all(signature[i][1] == "False" for signature in groups.values()) for i in range(len(evaluator.disease_ids)))
    if no_expert != 2:
        raise ValueError("no-applicable-expert census mismatch")
    # Report integrity/counts without duplicating row-level graph identifiers.
    semantics_summary = {**semantics, "folds": [
        {key: value for key, value in fold.items() if key not in ("target_disease_ids", "buffer_disease_ids")}
        for fold in semantics["folds"]
    ]}
    return {
        "gate": "PHASE_2_GATE_6C_A_INPUT_VALIDATION", "status": "PASS",
        "scope": "Input contracts only; no portfolio means, SBS/VBS, bootstrap, routing, or training executed",
        "registry_sha256": sha256_file(registry_path), "gate1_summary": gate1["summary"],
        "gate1_overall": gate1["overall"],
        "candidate_axis": {"count": len(evaluator.candidate_ids), "sha256": axis_sha256(list(evaluator.candidate_ids)), "status": "PASS"},
        "disease_axis": {"count": len(evaluator.disease_ids), "sha256": axis_sha256(list(evaluator.disease_ids)), "status": "PASS"},
        "evaluation_contract": evaluation_contract, "benchmark_semantics": semantics_summary,
        "matrices": results, "seed_sets": {"E1": [0], "E2": [0], "E3": [0, 1, 2], "E4": [0, 1, 2]},
        "seed_aggregation_executed": False, "no_applicable_expert_count": no_expert,
        "limitations": [
            "Metric CSVs do not contain the ordered drug score axis; exact NPZ axis verification is historical Gate-3/4/5/6A evidence, not a fresh score-file check.",
            "Statuses are validated against frozen metadata; biological applicability causation is not independently re-derived without raw inputs.",
            "Raw graph completeness/leakage re-enumeration is not possible from frozen quarantine alone.",
        ],
    }


if __name__ == "__main__":
    report = audit_inputs()
    path = ROOT / "outputs/gate6c_input_validation.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['status']}: eight matrices; axes, folds, identities, seeds, roles, applicability and frozen masks checked")
