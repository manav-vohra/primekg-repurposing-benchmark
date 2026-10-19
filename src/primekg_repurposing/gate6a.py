"""Gate-6A E3 preparation and validation; never launches training."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .benchmark import load_frozen_benchmark
from .experts.e3_complex import (
    COMPLEX_DIM, CORPUS_MANIFEST_SHA256, EXPECTED_FOLD_COUNTS, N_ENTITIES, N_RELATIONS,
    STAGE_A, STAGE_B, read_csv_rows, scan_raw_corpus, sha256_file, validate_checkpoint,
    validate_frozen_corpus, validate_score_archive,
)
from .provenance import validate


CHECKPOINT_IDS = {
    0: "1Ev_eMyAq-hQtvYgCAGIV0fkGw4UV_py7",
    1: "1sQ9DO0Jpxj6NVleuKEqOw7NJrsl_VUJ3",
    2: "1Oiqa6dUxzMdvUiRzyxmmj6Dj04TMHIYf",
}
SCORE_IDS = {
    0: "1QN4KxE4L5H_nixEi0zEFHc37PjqOWj4p",
    1: "19vkBSKisMdcqmnQgkoc8g4q5VKQuT55M",
    2: "1hmbIzS6CtoEvJS4qyKmjV7ZDqWnKG6ev",
}
SEED_MACRO_RECALL50 = {
    0: 0.2918345167963524,
    1: 0.30365612615190174,
    2: 0.31921361850047364,
}


def runtime_environment() -> dict[str, Any]:
    import pandas
    import scipy
    try:
        import torch
        torch_info = {"version": torch.__version__, "cuda_available": torch.cuda.is_available(),
                      "cuda_version": torch.version.cuda, "backend": "CPU" if not torch.cuda.is_available() else torch.cuda.get_device_name(0)}
    except ImportError:
        torch_info = {"version": None, "cuda_available": False, "cuda_version": None, "backend": "UNAVAILABLE"}
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "numpy": np.__version__, "pandas": pandas.__version__,
            "scipy": scipy.__version__, "pytorch": torch_info}


def historical_environment() -> dict[str, Any]:
    return {
        "python": {"classification": "UNKNOWN", "value": None},
        "numpy": {"classification": "UNKNOWN", "value": None},
        "pandas": {"classification": "UNKNOWN", "value": None},
        "pytorch": {"classification": "UNKNOWN", "value": None},
        "scipy": {"classification": "RECOVERED", "value": "used by Cell 20 evaluator; version unknown"},
        "cuda": {"classification": "RECOVERED", "value": "required and selected by Cells 20/21; version unknown"},
        "gpu": {"classification": "RECOVERED", "value": "Colab A100 explicitly required; exact model/driver unknown"},
        "determinism": {"classification": "EXACT", "value": "torch cudnn deterministic=True; benchmark=False; Python/NumPy/Torch/CUDA seeds set"},
    }


def prepare_gate6a(root: Path, raw_kg: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    frozen = root / "artifacts/frozen"
    recovered = root / "artifacts/recovered/external"
    registry = root / "artifacts/registry.json"
    gate1 = validate(registry, frozen, "REFERENCE")
    benchmark = load_frozen_benchmark(registry, frozen, gate1)
    corpus = validate_frozen_corpus(frozen, recovered, benchmark)

    raw_validation: dict[str, Any] = {"status": "NOT_REQUESTED"}
    if raw_kg is not None:
        scan = scan_raw_corpus(raw_kg)
        frozen_entities = [r["entity_key"] for r in read_csv_rows(frozen / "benchmark/p1_e3_complex_entities.csv")]
        expected_entities = set(scan.pop("base_entity_keys"))
        expected_entities.update(f"drug::{d}" for d in benchmark.candidate_ids)
        expected_entities.update(f"disease::{d}" for d, _ in benchmark.disease_folds)
        expected_entities.update(f"drug::{p.drug_id}" for p in benchmark.role_pairs if p.role.value == "CLEAN_INDICATION")
        expected_entities.update(f"disease::{p.disease_id}" for p in benchmark.role_pairs if p.role.value == "CLEAN_INDICATION")
        relation_rows = read_csv_rows(frozen / "benchmark/p1_e3_complex_relations.csv")
        expected_relation_counts = {r["relation_name"]: int(r["base_nontherapeutic_row_count"]) for r in relation_rows if r["relation_name"] != "clean_indication"}
        checks = {
            "nontherapeutic_count": scan["nontherapeutic_directed_triples"] == 8_015_236,
            "therapeutic_removed": scan["therapeutic_rows_removed"] == 85_262,
            "entity_vocabulary_exact": sorted(expected_entities) == frozen_entities,
            "relation_vocabulary_and_counts_exact": scan["relation_counts"] == expected_relation_counts,
        }
        raw_validation = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
                          "input_sha256": sha256_file(raw_kg), "input_size": raw_kg.stat().st_size,
                          "nontherapeutic_directed_triples": scan["nontherapeutic_directed_triples"],
                          "therapeutic_rows_removed": scan["therapeutic_rows_removed"]}
    else:
        cache = root / "outputs/gate6a_raw_corpus_scan.json"
        if cache.is_file():
            cached = json.loads(cache.read_text(encoding="utf-8"))
            if cached.get("status") == "PASS" and all(cached.get("checks", {}).values()):
                raw_validation = cached
                raw_validation["evidence_reused"] = "completed Gate-6A streaming scan of the hash-verified registered raw input"

    checkpoints = []
    for seed in (0, 1, 2):
        item = validate_checkpoint(recovered / f"p1_e3_complex_seed{seed}_base_pretrain.pt", seed)
        item["connected_source_id"] = CHECKPOINT_IDS[seed]
        checkpoints.append(item)

    disease_ids = [disease for disease, _ in benchmark.disease_folds]
    score_archives = []
    score_root = root / "work/gate3_scores"
    for seed in (0, 1, 2):
        item = validate_score_archive(score_root / f"p1_e3_complex_seed{seed}_scores.npz", seed, disease_ids, benchmark.candidate_ids)
        item["connected_source_id"] = SCORE_IDS[seed]
        item["macro_recall50"] = SEED_MACRO_RECALL50[seed]
        score_archives.append(item)

    matrix = read_csv_rows(frozen / "reference_results/p1_e3_complex_seed0_expert_matrix.csv")
    status_counts: dict[str, int] = {}
    for row in matrix:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    applicability = {
        "rule": "OK iff target disease has >=1 nontherapeutic base-graph edge; then finite/nonconstant score checks",
        "source": "Cell 20/21 disease_has_context from base-active entity indices; downstream frozen matrix confirms status because no separate upstream status archive survives",
        "status_counts": status_counts,
        "applicable": status_counts.get("OK", 0), "total": len(matrix),
    }
    sources = {
        "cell19": {"class": "HISTORICAL_SOURCE_WITH_DIAGNOSED_DEFECT", "sha256": "2b140c6482b7bd32a0c61354b0a005cb622bc255405f33a784ded122fd829012"},
        "cell19a": {"class": "HISTORICAL_FORENSIC_RECONCILIATION", "sha256": "5c0499aa4dc3a0e47652c7e57bc5d94e28fd194d48efbd02c9d643de6b6ad09d"},
        "cell19b": {"class": "HISTORICAL_CORRECTIVE_SOURCE", "sha256": "f2a2af19cbf5f84f88f9bb4d3b833a9f01892811e24140e92c0f0f480c874187"},
        "cell20": {"class": "AUTHORITATIVE_HISTORICAL_SOURCE", "sha256": "14712fef0cd629bda08dee271e15dde77175379281c0099f3b513a9540c1648c"},
        "cell21": {"class": "AUTHORITATIVE_HISTORICAL_SUPPORT", "sha256": "af61b4148f33029883e6e2acf425915c32091a0916259f1ad8e639662ba56224"},
    }
    implementation_files = [root / "src/primekg_repurposing/experts/e3_complex.py", root / "src/primekg_repurposing/gate6a.py"]
    environment = runtime_environment()
    prereg = {
        "gate": "PHASE_2_GATE_6B", "state": "FROZEN_BEFORE_TRAINING", "expert_id": "E3_COMPLEX_KGE",
        "implementation": {str(p.relative_to(root)).replace("\\", "/"): sha256_file(p) for p in implementation_files},
        "historical_sources": sources,
        "corpus": {"manifest_sha256": CORPUS_MANIFEST_SHA256, "base_sha256": corpus["base_sha256"],
                   "clean_sha256": corpus["clean_sha256"], "entity_mapping_sha256": corpus["entity_sha256"],
                   "relation_mapping_sha256": corpus["relation_sha256"], "fold_manifest_sha256": corpus["fold_manifest_sha256"]},
        "benchmark": {"id": benchmark.benchmark_id, "masking": benchmark.protocol.value,
                      "masking_implementation": "FrozenBenchmark.mask", "evaluator": "1.1_tiesafe"},
        "seeds": [0, 1, 2], "model": {"family": "ComplEx", "dimension": COMPLEX_DIM,
            "entities": N_ENTITIES, "relations": N_RELATIONS, "dtype": "torch.float32",
            "score": "sum(hr*rr*tr + hi*rr*ti + hr*ri*ti - hi*ri*tr)",
            "normalization": None, "explicit_regularization": None},
        "stage_a": STAGE_A, "stage_b": STAGE_B,
        "stage_a_checkpoints": [{k: c[k] for k in ("seed", "sha256", "hash_classification", "size", "connected_source_id")} for c in checkpoints],
        "axes": {"candidate_count": 7957, "candidate_order": "p1_v0_candidate_drugs.csv",
                 "disease_count": 738, "disease_order": "p1_v0_primary_diseases.csv",
                 "orientation": "candidate drug head -> clean_indication -> primary disease tail",
                 "score_dtype": "float32"},
        "reference_score_archives": [{k: s[k] for k in ("seed", "sha256", "hash_classification", "size", "connected_source_id", "macro_recall50")} for s in score_archives],
        "runtime_environment": environment,
        "comparison_fields": ["score_shape", "axis_identity", "dtype", "finite_count", "unequal_value_count", "max_absolute_difference", "per_metric_max_absolute_difference", "macro_recall50_absolute_difference"],
        "pass_tolerance": None,
        "pass_tolerance_policy": "No tolerance preregistered; report raw fidelity first and justify any scientific-equivalence tolerance from observed behavior/provenance.",
        "explicit_non_actions": ["no full Stage-A pretraining", "no Stage-B training", "no E4", "no SBS/VBS/oracle/routing analysis", "no seed selection", "no raw-score averaging"],
    }
    overall = all((corpus["status"] == "PASS", raw_validation["status"] in {"PASS", "NOT_REQUESTED"},
                   all(c["strict_load"] and c["probe_finite"] and c["probe_bitwise_equal"] for c in checkpoints),
                   all(s["status"] == "PASS" for s in score_archives), applicability["applicable"] == 736))
    report = {
        "gate": "PHASE_2_GATE_6A", "overall_status": "PASS" if overall else "FAIL",
        "training_launched": False, "sources": sources, "corpus": corpus, "raw_reconstruction": raw_validation,
        "model": prereg["model"], "stage_a": STAGE_A, "stage_b": STAGE_B,
        "checkpoint_validation": checkpoints, "score_archives": score_archives,
        "applicability": applicability, "historical_environment": historical_environment(),
        "runtime_environment": environment, "gate6b_preregistration_complete": True,
        "unresolved_ambiguity": ["Historical Python/package/CUDA/driver versions and exact A100 SKU were not preserved."],
    }
    return report, prereg


def write_json(value: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
