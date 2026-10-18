"""Read-only validation of frozen PrimeKG artifacts and provenance.

The registry holds expected historical facts. Reports hold observations from the
current filesystem. This module never reconstructs benchmark data or scores.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import zipfile
from collections import Counter
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .score_archive import load_score_archive


class ProvenanceClass(str, Enum):
    RAW_EXTERNAL_INPUT = "RAW_EXTERNAL_INPUT"
    HISTORICAL_SOURCE = "HISTORICAL_SOURCE"
    HISTORICAL_SOURCE_WITH_DIAGNOSED_DEFECT = "HISTORICAL_SOURCE_WITH_DIAGNOSED_DEFECT"
    HISTORICAL_FORENSIC_RECONCILIATION = "HISTORICAL_FORENSIC_RECONCILIATION"
    HISTORICAL_CORRECTIVE_SOURCE = "HISTORICAL_CORRECTIVE_SOURCE"
    FROZEN_BENCHMARK_ARTIFACT = "FROZEN_BENCHMARK_ARTIFACT"
    FROZEN_REFERENCE_RESULT = "FROZEN_REFERENCE_RESULT"
    FROZEN_MODEL_ARTIFACT = "FROZEN_MODEL_ARTIFACT"
    RECOVERED_HISTORICAL_ARTIFACT = "RECOVERED_HISTORICAL_ARTIFACT"
    RECONSTRUCTED_HISTORICAL_SNAPSHOT = "RECONSTRUCTED_HISTORICAL_SNAPSHOT"
    CLEAN_REIMPLEMENTATION_OUTPUT = "CLEAN_REIMPLEMENTATION_OUTPUT"
    GENERATED_DERIVED_ARTIFACT = "GENERATED_DERIVED_ARTIFACT"
    FOUND_EXTERNAL_NOT_BUNDLED = "FOUND_EXTERNAL_NOT_BUNDLED"


class VerificationState(str, Enum):
    FOUND_AND_VERIFIED = "FOUND_AND_VERIFIED"
    FOUND_HASH_MISMATCH = "FOUND_HASH_MISMATCH"
    REGISTERED_EXTERNAL_NOT_LOCAL = "REGISTERED_EXTERNAL_NOT_LOCAL"
    UNKNOWN_HASH = "UNKNOWN_HASH"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    FOUND_VALIDATION_FAILURE = "FOUND_VALIDATION_FAILURE"


FAIL_STATES = {
    VerificationState.FOUND_HASH_MISMATCH.value,
    VerificationState.MISSING_REQUIRED.value,
    VerificationState.FOUND_VALIDATION_FAILURE.value,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def axis_sha256(values: list[str]) -> str:
    return hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest()


def _issue(artifact_id: str, field: str, expected: Any, observed: Any, severity: str = "ERROR") -> dict:
    return {"artifact_id": artifact_id, "field": field, "expected": expected, "observed": observed, "severity": severity}


def _safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe logical path: {value!r}")
    return path


def load_registry(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("benchmark"), dict) or not isinstance(data.get("artifacts"), list):
        raise ValueError("registry needs benchmark and artifacts")
    ids = [item["artifact_id"] for item in data["artifacts"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate artifact IDs")
    for item in data["artifacts"]:
        ProvenanceClass(item["provenance_class"])
        sha = item.get("expected_sha256")
        if sha is not None and not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError(f"invalid expected SHA-256: {item['artifact_id']}")
        if item.get("logical_path"):
            _safe_relative(item["logical_path"])
        for dependency in item.get("dependencies", []):
            if dependency not in ids:
                raise ValueError(f"unknown dependency {dependency} of {item['artifact_id']}")
    graph = {item["artifact_id"]: item.get("dependencies", []) for item in data["artifacts"]}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError(f"dependency cycle at {node}")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    return data


def _json_field(data: Any, dotted: str) -> Any:
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _read_csv(path: Path, item: dict, benchmark: dict, expected_axes: dict[str, list[str]]) -> tuple[list[dict], list[dict], str, str]:
    failures: list[dict] = []
    rows: list[dict] = []
    artifact_id = item["artifact_id"]
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        required = item["schema"].get("required_columns", [])
        for column in required:
            if column not in columns:
                failures.append(_issue(artifact_id, f"column.{column}", "present", "missing"))
        if failures:
            return rows, failures, "FAIL", "NOT_CHECKED"
        for row in reader:
            if None in row:
                failures.append(_issue(artifact_id, "csv_row_width", len(columns), "extra fields"))
                break
            rows.append(row)

    if item.get("expected_rows") is not None and len(rows) != item["expected_rows"]:
        failures.append(_issue(artifact_id, "row_count", item["expected_rows"], len(rows)))

    for field, expected in item.get("metadata_equals", {}).items():
        values = {row.get(field) for row in rows}
        if values != {str(expected)}:
            failures.append(_issue(artifact_id, field, expected, sorted(values, key=str)[:5]))

    axis_state = "NOT_APPLICABLE"
    if item.get("axis"):
        axis = item["axis"]
        values = [row[axis["column"]] for row in rows]
        observed = axis_sha256(values)
        axis_state = "PASS" if observed == axis["expected_sha256"] else "FAIL"
        if axis_state == "FAIL":
            failures.append(_issue(artifact_id, f"axis.{axis['name']}.sha256", axis["expected_sha256"], observed))
        if len(values) != len(set(values)):
            axis_state = "FAIL"
            failures.append(_issue(artifact_id, f"axis.{axis['name']}.uniqueness", "unique", "duplicates"))
        expected_axes[axis["name"]] = values

    if item.get("disease_axis"):
        expected = expected_axes.get("diseases")
        if expected is None:
            axis_state = "NOT_CHECKED"
        else:
            observed_values = [row[item["disease_axis"]["column"]] for row in rows]
            axis_state = "PASS" if observed_values == expected else "FAIL"
            if axis_state == "FAIL":
                mismatch = next((i for i, (a, b) in enumerate(zip(expected, observed_values)) if a != b), min(len(expected), len(observed_values)))
                failures.append(_issue(artifact_id, "axis.diseases.order", f"frozen order at row {mismatch}", observed_values[mismatch] if mismatch < len(observed_values) else "short axis"))

    return rows, failures, "FAIL" if any(f["field"].startswith(("column.", "csv_row_width")) for f in failures) else "PASS", axis_state


def _read_raw_kg(path: Path, item: dict) -> tuple[list[dict], str]:
    """Check the 982 MB CSV without retaining graph rows or deriving edges."""
    failures = []
    artifact_id = item["artifact_id"]
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        for column in item["schema"]["required_columns"]:
            if column not in columns:
                failures.append(_issue(artifact_id, f"column.{column}", "present", "missing"))
        if failures:
            return failures, "FAIL"
        count = 0
        for row in reader:
            count += 1
            if None in row:
                failures.append(_issue(artifact_id, "csv_row_width", len(columns), f"extra fields at row {count}"))
                break
    if count != item["expected_rows"]:
        failures.append(_issue(artifact_id, "row_count", item["expected_rows"], count))
    return failures, "FAIL" if failures else "PASS"


def _read_npz_score(path: Path, item: dict, expected_axes: dict[str, list[str]]) -> tuple[list[dict], str, str]:
    artifact_id = item["artifact_id"]
    try:
        import numpy as np
    except ImportError:
        return [_issue(artifact_id, "numpy", "available for local NPZ validation", "not installed")], "NOT_CHECKED", "NOT_CHECKED"
    failures = []
    try:
        archive = load_score_archive(path)
    except (OSError, ValueError) as exc:
        return [_issue(artifact_id, "npz_schema", "safe score archive", str(exc))], "FAIL", "NOT_CHECKED"
    scores = archive.scores
    expected_shape = tuple(item["schema"]["expected_shape"])
    if scores.shape != expected_shape:
        failures.append(_issue(artifact_id, "scores.shape", expected_shape, scores.shape))
    disease_ids = list(archive.disease_ids)
    drug_ids = list(archive.drug_ids)
    axis_state = "PASS"
    for name, observed in (("diseases", disease_ids), ("candidates", drug_ids)):
        expected = expected_axes.get(name)
        if expected is None:
            axis_state = "NOT_CHECKED"
        elif expected != observed:
            axis_state = "FAIL"
            failures.append(_issue(artifact_id, f"axis.{name}.order", axis_sha256(expected), axis_sha256(observed)))
    return failures, "FAIL" if any(f["field"].startswith(("array.", "scores.")) for f in failures) else "PASS", axis_state


def _file_result(item: dict, data_root: Path, benchmark: dict, expected_axes: dict[str, list[str]], required: bool) -> tuple[dict, list[dict], Any]:
    artifact_id = item["artifact_id"]
    logical = item.get("logical_path")
    result = {
        "artifact_id": artifact_id, "filename": item.get("filename"), "provenance_class": item["provenance_class"],
        "location": item["location"], "external_id": item.get("external_id"), "logical_path": logical,
        "required": required, "expected_sha256": item.get("expected_sha256"), "observed_sha256": None,
        "hash_state": "UNKNOWN" if item.get("expected_sha256") is None else "NOT_CHECKED",
        "verification_state": None, "schema_state": "NOT_CHECKED", "axis_state": "NOT_CHECKED",
        "invariant_state": "NOT_CHECKED", "expected_size": item.get("expected_size"), "observed_size": None,
        "dependencies": item.get("dependencies", []), "producer": item.get("producer"),
        "consumers": item.get("consumers", []), "safe_to_consume": False,
    }
    findings: list[dict] = []
    if logical is None:
        result["verification_state"] = VerificationState.MISSING_REQUIRED.value if required else VerificationState.REGISTERED_EXTERNAL_NOT_LOCAL.value
        if required:
            findings.append(_issue(artifact_id, "file", "local artifact", "no logical path"))
        return result, findings, None
    path = data_root / _safe_relative(logical)
    if not path.is_file():
        result["verification_state"] = VerificationState.MISSING_REQUIRED.value if required else VerificationState.REGISTERED_EXTERNAL_NOT_LOCAL.value
        if required:
            findings.append(_issue(artifact_id, "file", "present", "missing"))
        return result, findings, None
    try:
        result["observed_size"] = path.stat().st_size
        result["observed_sha256"] = sha256_file(path)
        if item.get("expected_size") is not None and result["observed_size"] != item["expected_size"]:
            findings.append(_issue(artifact_id, "size", item["expected_size"], result["observed_size"]))
        expected_hash = item.get("expected_sha256")
        if expected_hash is not None:
            result["hash_state"] = "PASS" if result["observed_sha256"] == expected_hash else "FAIL"
            if result["hash_state"] == "FAIL":
                findings.append(_issue(artifact_id, "sha256", expected_hash, result["observed_sha256"]))
        data = None
        schema = item.get("schema", {})
        if schema.get("type") == "csv" and artifact_id == "raw/kg.csv":
            errors, schema_state = _read_raw_kg(path, item)
            findings.extend(errors)
            result["schema_state"] = schema_state
            result["axis_state"] = "NOT_APPLICABLE"
        elif schema.get("type") == "csv":
            data, errors, schema_state, axis_state = _read_csv(path, item, benchmark, expected_axes)
            findings.extend(errors)
            result["schema_state"] = schema_state
            result["axis_state"] = axis_state
        elif schema.get("type") == "json":
            data = json.loads(path.read_text(encoding="utf-8"))
            result["schema_state"] = "PASS"
            for field, expected in item.get("metadata_equals", {}).items():
                observed = _json_field(data, field)
                if observed != expected:
                    findings.append(_issue(artifact_id, field, expected, observed))
                    result["schema_state"] = "FAIL"
        elif schema.get("type") == "npz_score":
            errors, schema_state, axis_state = _read_npz_score(path, item, expected_axes)
            findings.extend(errors)
            result["schema_state"] = schema_state
            result["axis_state"] = axis_state
        else:
            result["schema_state"] = "NOT_APPLICABLE"
            result["axis_state"] = "NOT_APPLICABLE"
        if result["axis_state"] == "NOT_CHECKED" and not item.get("axis") and not item.get("disease_axis") and schema.get("type") != "npz_score":
            result["axis_state"] = "NOT_APPLICABLE"
        if result["hash_state"] == "FAIL":
            result["verification_state"] = VerificationState.FOUND_HASH_MISMATCH.value
        elif any(f["severity"] == "ERROR" for f in findings):
            result["verification_state"] = VerificationState.FOUND_VALIDATION_FAILURE.value
        elif expected_hash is None:
            result["verification_state"] = VerificationState.UNKNOWN_HASH.value
        else:
            result["verification_state"] = VerificationState.FOUND_AND_VERIFIED.value
        return result, findings, data
    except (OSError, UnicodeError, csv.Error, json.JSONDecodeError, zipfile.BadZipFile, ValueError, KeyError) as exc:
        detail = str(exc).replace(str(path), logical)
        findings.append(_issue(artifact_id, "readability", "readable and parseable", f"{type(exc).__name__}: {detail}"))
        result["verification_state"] = VerificationState.FOUND_VALIDATION_FAILURE.value
        result["schema_state"] = "FAIL"
        return result, findings, None


def _cross_invariants(results: dict[str, dict], data: dict[str, Any], benchmark: dict, registry: dict) -> list[dict]:
    findings = []
    manifest = data.get("benchmark/p1_v0_benchmark_manifest.json")
    evaluator = data.get("benchmark/p1_v0_evaluator_config_v1_1_tiesafe.json")
    corpus = data.get("benchmark/p1_e3_complex_corpus_manifest.json")
    if manifest is None or evaluator is None or corpus is None:
        return [_issue("benchmark", "contracts", "all three frozen manifests", "unavailable")]
    checks = [
        ("benchmark.id", benchmark["id"], manifest.get("benchmark_id")),
        ("benchmark.candidate_count", benchmark["candidate_count"], manifest.get("task", {}).get("candidate_count")),
        ("benchmark.primary_disease_count", benchmark["primary_disease_count"], manifest.get("task", {}).get("primary_disease_count")),
        ("benchmark.truth_pairs", benchmark["primary_clean_truth_pairs"], manifest.get("task", {}).get("primary_clean_truth_pairs")),
        ("benchmark.folds", benchmark["folds"], manifest.get("oof_protocol", {}).get("k")),
        ("benchmark.split_seed", benchmark["split_seed"], manifest.get("oof_protocol", {}).get("seed")),
        ("evaluator.version", benchmark["evaluator_version"], evaluator.get("evaluator_version")),
        ("evaluator.benchmark_id", benchmark["id"], evaluator.get("benchmark_id")),
        ("corpus.entities", benchmark["e3_entities"], corpus.get("entities")),
        ("corpus.relations", benchmark["e3_relations"], corpus.get("relations")),
        ("corpus.benchmark_id", benchmark["id"], corpus.get("benchmark_id")),
        ("evaluator.candidate_universe", benchmark["candidate_count"], evaluator.get("candidate_universe")),
        ("kg.sha256", next(item["expected_sha256"] for item in registry["artifacts"] if item["artifact_id"] == "raw/kg.csv"), manifest.get("artifacts", {}).get("primekg_kg_csv", {}).get("sha256")),
    ]
    for field, expected, observed in checks:
        if expected != observed:
            findings.append(_issue("benchmark", field, expected, observed))
    for artifact_id, expected_rows in (
        ("benchmark/p1_v0_candidate_drugs.csv", benchmark["candidate_count"]),
        ("benchmark/p1_v0_primary_diseases.csv", benchmark["primary_disease_count"]),
        ("benchmark/p1_v0_primary_truth.csv", benchmark["primary_clean_truth_pairs"]),
        ("benchmark/p1_v0_fold_summary.csv", benchmark["folds"]),
        ("benchmark/p1_e3_complex_entities.csv", benchmark["e3_entities"]),
        ("benchmark/p1_e3_complex_relations.csv", benchmark["e3_relations"]),
    ):
        rows = data.get(artifact_id)
        if rows is None or len(rows) != expected_rows:
            findings.append(_issue(artifact_id, "benchmark_cardinality", expected_rows, None if rows is None else len(rows)))

    diseases = data.get("benchmark/p1_v0_primary_diseases.csv") or []
    candidates = data.get("benchmark/p1_v0_candidate_drugs.csv") or []
    disease_ids = [row["disease_id"] for row in diseases] if diseases else []
    candidate_ids = {row["drug_id"] for row in candidates} if candidates else set()
    folds = set(range(benchmark["folds"]))
    try:
        actual_folds = {int(row["oof_fold"]) for row in diseases}
        if actual_folds != folds:
            findings.append(_issue("benchmark/p1_v0_primary_diseases.csv", "oof_fold_values", sorted(folds), sorted(actual_folds)))
    except (ValueError, KeyError):
        findings.append(_issue("benchmark/p1_v0_primary_diseases.csv", "oof_fold_values", sorted(folds), "invalid"))
    for name in ("p1_v0_primary_truth.csv", "p1_v0_primary_eval_roles.csv"):
        artifact_id = f"benchmark/{name}"
        rows = data.get(artifact_id) or []
        for index, row in enumerate(rows):
            if row["disease_id"] not in disease_ids:
                findings.append(_issue(artifact_id, f"row[{index}].disease_id", "primary disease", row["disease_id"]))
                break
            if row["drug_id"] not in candidate_ids:
                findings.append(_issue(artifact_id, f"row[{index}].drug_id", "candidate drug", row["drug_id"]))
                break
    truth = data.get("benchmark/p1_v0_primary_truth.csv") or []
    if any(row["evaluation_role"] != "CLEAN_INDICATION" for row in truth):
        findings.append(_issue("benchmark/p1_v0_primary_truth.csv", "evaluation_role", "CLEAN_INDICATION", "other role present"))
    summary = data.get("benchmark/p1_v0_fold_summary.csv") or []
    if summary:
        try:
            summary_folds = [int(row["fold"]) for row in summary]
            clean_counts = [int(row["clean_training_pairs_remaining"]) for row in summary]
            targets = sum(int(row["target_diseases"]) for row in summary)
            if summary_folds != list(range(benchmark["folds"])):
                findings.append(_issue("benchmark/p1_v0_fold_summary.csv", "fold_order", list(range(benchmark["folds"])), summary_folds))
            if clean_counts != benchmark["fold_clean_counts"]:
                findings.append(_issue("benchmark/p1_v0_fold_summary.csv", "clean_training_pairs_remaining", benchmark["fold_clean_counts"], clean_counts))
            if targets != benchmark["primary_disease_count"]:
                findings.append(_issue("benchmark/p1_v0_fold_summary.csv", "sum_target_diseases", benchmark["primary_disease_count"], targets))
        except (ValueError, KeyError):
            findings.append(_issue("benchmark/p1_v0_fold_summary.csv", "fold_summary_fields", "valid integers", "invalid"))
    quarantine = data.get("benchmark/p1_v0_k8_quarantine_manifest.csv") or []
    if quarantine:
        expected_targets = {(row["oof_fold"], row["disease_id"]) for row in diseases}
        actual_targets = {(row["fold"], row["disease_id"]) for row in quarantine if row["role"] == "TARGET"}
        if actual_targets != expected_targets:
            findings.append(_issue("benchmark/p1_v0_k8_quarantine_manifest.csv", "target_fold_assignment", len(expected_targets), len(actual_targets)))
        if any(row["hide_all_therapeutic_relations"].lower() != "true" for row in quarantine):
            findings.append(_issue("benchmark/p1_v0_k8_quarantine_manifest.csv", "hide_all_therapeutic_relations", "true for every row", "false or invalid value"))
    fold_labels = data.get("recovered_contracts/p1_e3_complex_fold_label_manifest.csv") or []
    if fold_labels:
        try:
            label_folds = [int(row["fold"]) for row in fold_labels]
            legal_counts = [int(row["legal_clean_indication_pairs"]) for row in fold_labels]
            expected_legal = [int(row["expected_legal_pairs"]) for row in fold_labels]
            deltas = [int(row["delta"]) for row in fold_labels]
            leaks = [int(row["direct_hidden_label_leaks"]) for row in fold_labels]
            if label_folds != list(range(benchmark["folds"])):
                findings.append(_issue("recovered_contracts/p1_e3_complex_fold_label_manifest.csv", "fold_order", list(range(benchmark["folds"])), label_folds))
            if legal_counts != benchmark["fold_clean_counts"] or expected_legal != benchmark["fold_clean_counts"]:
                findings.append(_issue("recovered_contracts/p1_e3_complex_fold_label_manifest.csv", "legal_clean_indication_pairs", benchmark["fold_clean_counts"], legal_counts))
            if any(deltas) or any(leaks):
                findings.append(_issue("recovered_contracts/p1_e3_complex_fold_label_manifest.csv", "delta_or_direct_hidden_label_leaks", "all zero", {"delta": deltas, "leaks": leaks}))
        except (ValueError, KeyError):
            findings.append(_issue("recovered_contracts/p1_e3_complex_fold_label_manifest.csv", "fold_label_fields", "valid integers", "invalid"))
    registry_by_name = {item["filename"]: item for item in registry["artifacts"] if item.get("filename")}
    for filename, declared_hash in corpus.get("artifact_hashes", {}).items():
        item = registry_by_name.get(filename)
        observed_hash = item.get("expected_sha256") if item else None
        if observed_hash != declared_hash:
            findings.append(_issue("benchmark/p1_e3_complex_corpus_manifest.json", f"artifact_hashes.{filename}", declared_hash, observed_hash))
    entities = data.get("benchmark/p1_e3_complex_entities.csv") or []
    relations = data.get("benchmark/p1_e3_complex_relations.csv") or []
    for artifact_id, rows, column in (("benchmark/p1_e3_complex_entities.csv", entities, "entity_index"), ("benchmark/p1_e3_complex_relations.csv", relations, "relation_index")):
        try:
            if any(int(row[column]) != index for index, row in enumerate(rows)):
                findings.append(_issue(artifact_id, column, "contiguous from zero", "gap or reordering"))
        except (ValueError, KeyError):
            findings.append(_issue(artifact_id, column, "contiguous integers", "invalid"))
    return findings


def _commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=3, check=True)
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def validate(registry_path: Path, data_root: Path, tier: str = "REFERENCE") -> dict:
    """Validate one tier and return a JSON-serializable report."""
    if tier not in {"SMOKE", "REFERENCE", "FULL_LOCAL"}:
        raise ValueError(f"unknown tier {tier}")
    registry = load_registry(registry_path)
    benchmark = registry["benchmark"]
    items = registry["artifacts"]
    results: dict[str, dict] = {}
    parsed: dict[str, Any] = {}
    findings: list[dict] = []
    expected_axes: dict[str, list[str]] = {}
    # Anchor axes first, so matrix and score checks are independent of registry order.
    priority = {"benchmark/p1_v0_candidate_drugs.csv": 0, "benchmark/p1_v0_primary_diseases.csv": 1, "benchmark/p1_e3_complex_entities.csv": 2, "benchmark/p1_e3_complex_relations.csv": 3}
    ordered = sorted(items, key=lambda item: (priority.get(item["artifact_id"], 4), item["artifact_id"]))
    for item in ordered:
        required = tier in item.get("required_for", [])
        result, errors, data = _file_result(item, data_root, benchmark, expected_axes, required)
        results[item["artifact_id"]] = result
        findings.extend(errors)
        if data is not None:
            parsed[item["artifact_id"]] = data
    if tier != "SMOKE":
        invariant_findings = _cross_invariants(results, parsed, benchmark, registry)
        findings.extend(invariant_findings)
        for result in results.values():
            if result["required"] and result["verification_state"] == VerificationState.FOUND_AND_VERIFIED.value:
                result["invariant_state"] = "PASS"
        for finding in invariant_findings:
            target = results.get(finding["artifact_id"])
            if target:
                target["invariant_state"] = "FAIL"
                if target["verification_state"] == VerificationState.FOUND_AND_VERIFIED.value:
                    target["verification_state"] = VerificationState.FOUND_VALIDATION_FAILURE.value
    for result in results.values():
        result["safe_to_consume"] = (
            result["verification_state"] == VerificationState.FOUND_AND_VERIFIED.value
            and result["schema_state"] in {"PASS", "NOT_APPLICABLE"}
            and result["axis_state"] in {"PASS", "NOT_APPLICABLE"}
            and result["invariant_state"] != "FAIL"
        )
    state_counts = Counter(result["verification_state"] for result in results.values())
    required_failed = any(result["required"] and result["verification_state"] in FAIL_STATES for result in results.values())
    required_unknown = any(result["required"] and result["verification_state"] == VerificationState.UNKNOWN_HASH.value for result in results.values())
    required_not_checked = any(result["required"] and result["axis_state"] == "NOT_CHECKED" and ("axis" in next(item for item in items if item["artifact_id"] == result["artifact_id"]) or "disease_axis" in next(item for item in items if item["artifact_id"] == result["artifact_id"])) for result in results.values())
    if any(f["severity"] == "ERROR" for f in findings):
        required_failed = True
    overall = "FAIL" if required_failed else "PARTIAL" if required_unknown or required_not_checked or state_counts[VerificationState.REGISTERED_EXTERNAL_NOT_LOCAL.value] else "PASS"
    return {
        "report_version": "1.0", "registry_version": registry["registry_version"],
        "registry_observed_sha256": sha256_file(registry_path),
        "benchmark_id": benchmark["id"], "benchmark_contract": benchmark, "tier": tier,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit": _commit(registry_path.resolve().parents[1]),
        "overall": overall, "required_failure": required_failed,
        "summary": dict(state_counts), "artifacts": list(results.values()),
        "warnings": [f for f in findings if f["severity"] == "WARNING"],
        "failures": [f for f in findings if f["severity"] == "ERROR"],
    }
