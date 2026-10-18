"""Read-only P1-v0 fold, quarantine, and label-mask semantics.

The frozen tables are inputs. This module neither constructs those tables nor
changes biological/ontology graph structure.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .provenance import load_registry


class MaskingProtocol(str, Enum):
    TARGET_ONLY = "TARGET_ONLY"
    CANONICAL_1HOP = "CANONICAL_1HOP"
    STRICT_2HOP = "STRICT_2HOP"


class LabelState(str, Enum):
    CLEAN_INDICATION = "CLEAN_INDICATION"
    AMBIGUOUS_INDICATION = "AMBIGUOUS_INDICATION"
    CONTRAINDICATION_ONLY = "CONTRAINDICATION_ONLY"
    OFFLABEL_ONLY = "OFFLABEL_ONLY"
    CONFLICTING_NONINDICATION = "CONFLICTING_NONINDICATION"
    UNKNOWN_UNLABELED = "UNKNOWN_UNLABELED"


@dataclass(frozen=True)
class TherapeuticPair:
    drug_id: str
    disease_id: str
    role: LabelState


@dataclass(frozen=True)
class QuarantineEntry:
    fold: int
    disease_id: str
    role: str
    hide_all_therapeutic_relations: bool


@dataclass(frozen=True)
class GraphStructure:
    """Identity of preserved nontherapeutic evidence; edges are optional fixtures."""

    nontherapeutic_directed_triples: int
    entity_count: int
    relation_count: int
    evidence_edges: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class FoldMask:
    fold: int
    protocol: MaskingProtocol
    target_ids: tuple[str, ...]
    buffer_ids: tuple[str, ...]
    hidden_ids: frozenset[str]
    legal_clean_pairs: tuple[TherapeuticPair, ...]
    hidden_clean_pairs: tuple[TherapeuticPair, ...]
    legal_therapeutic_pairs: tuple[TherapeuticPair, ...]
    hidden_therapeutic_pairs: tuple[TherapeuticPair, ...]
    graph_structure: GraphStructure


@dataclass(frozen=True)
class FrozenBenchmark:
    benchmark_id: str
    protocol: MaskingProtocol
    candidate_ids: tuple[str, ...]
    disease_folds: tuple[tuple[str, int], ...]
    role_pairs: tuple[TherapeuticPair, ...]
    quarantine: tuple[QuarantineEntry, ...]
    fold_summary: tuple[dict[str, str], ...]
    fold_labels: tuple[dict[str, str], ...]
    graph_structure: GraphStructure
    expected: dict[str, Any]

    def label_state(self, drug_id: str, disease_id: str) -> LabelState:
        """An absent pair is unlabeled; no binary-negative state is introduced."""
        for pair in self.role_pairs:
            if pair.drug_id == drug_id and pair.disease_id == disease_id:
                return pair.role
        return LabelState.UNKNOWN_UNLABELED

    def mask(self, fold: int) -> FoldMask:
        if self.protocol is not MaskingProtocol.CANONICAL_1HOP:
            raise NotImplementedError(f"{self.protocol.value} semantics belong to a later robustness gate")
        if fold not in range(self.expected["folds"]):
            raise ValueError(f"invalid fold {fold}")
        # Target order follows the frozen disease axis. Buffer order follows the
        # hash-verified quarantine file. Python strings retain full composite IDs.
        targets = tuple(disease_id for disease_id, assigned_fold in self.disease_folds if assigned_fold == fold)
        buffers = tuple(row.disease_id for row in self.quarantine if row.fold == fold and row.role == "BUFFER")
        hidden = frozenset(targets) | frozenset(buffers)
        legal = tuple(pair for pair in self.role_pairs if pair.disease_id not in hidden)
        excluded = tuple(pair for pair in self.role_pairs if pair.disease_id in hidden)
        return FoldMask(
            fold=fold, protocol=self.protocol, target_ids=targets, buffer_ids=buffers,
            hidden_ids=hidden,
            legal_clean_pairs=tuple(pair for pair in legal if pair.role is LabelState.CLEAN_INDICATION),
            hidden_clean_pairs=tuple(pair for pair in excluded if pair.role is LabelState.CLEAN_INDICATION),
            legal_therapeutic_pairs=legal, hidden_therapeutic_pairs=excluded,
            graph_structure=self.graph_structure,
        )


CORE_ARTIFACTS = (
    "benchmark/p1_v0_benchmark_manifest.json",
    "benchmark/p1_v0_candidate_drugs.csv",
    "benchmark/p1_v0_primary_diseases.csv",
    "benchmark/p1_v0_primary_truth.csv",
    "benchmark/therapeutic_pair_evaluation_roles.csv",
    "benchmark/p1_v0_k8_quarantine_manifest.csv",
    "benchmark/p1_v0_fold_summary.csv",
    "benchmark/p1_e3_complex_corpus_manifest.json",
    "benchmark/p1_e3_complex_entities.csv",
    "benchmark/p1_e3_complex_relations.csv",
    "recovered_contracts/p1_e3_complex_fold_label_manifest.csv",
)


def _rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return tuple(csv.DictReader(handle))


def load_frozen_benchmark(registry_path: Path, data_root: Path, gate1_report: dict) -> FrozenBenchmark:
    """Load only files Gate 1 marked safe; no bypass for local historical inputs."""
    registry = load_registry(registry_path)
    results = {row["artifact_id"]: row for row in gate1_report["artifacts"]}
    if gate1_report["benchmark_id"] != registry["benchmark"]["id"]:
        raise ValueError("Gate-1 report benchmark ID differs from registry")
    if gate1_report.get("required_failure"):
        raise ValueError("Gate-1 required validation failed")
    if gate1_report.get("registry_observed_sha256") is None:
        raise ValueError("Gate-1 report lacks registry identity")
    from .provenance import sha256_file

    if gate1_report["registry_observed_sha256"] != sha256_file(registry_path):
        raise ValueError("Gate-1 report was produced from a different registry")
    for artifact_id in CORE_ARTIFACTS:
        if not results.get(artifact_id, {}).get("safe_to_consume"):
            raise ValueError(f"Gate-1 integrity boundary rejected {artifact_id}")
    artifact_by_id = {item["artifact_id"]: item for item in registry["artifacts"]}

    def path(artifact_id: str) -> Path:
        return data_root / artifact_by_id[artifact_id]["logical_path"]

    # A report is evidence from a moment in time. Recheck core bytes before
    # consuming them so a later edit cannot reuse a stale successful report.
    for artifact_id in CORE_ARTIFACTS:
        if sha256_file(path(artifact_id)) != results[artifact_id]["observed_sha256"]:
            raise ValueError(f"Gate-1 report is stale for {artifact_id}")

    candidates = _rows(path("benchmark/p1_v0_candidate_drugs.csv"))
    diseases = _rows(path("benchmark/p1_v0_primary_diseases.csv"))
    pair_rows = _rows(path("benchmark/therapeutic_pair_evaluation_roles.csv"))
    quarantine_rows = _rows(path("benchmark/p1_v0_k8_quarantine_manifest.csv"))
    summary = _rows(path("benchmark/p1_v0_fold_summary.csv"))
    labels = _rows(path("recovered_contracts/p1_e3_complex_fold_label_manifest.csv"))
    corpus = json.loads(path("benchmark/p1_e3_complex_corpus_manifest.json").read_text(encoding="utf-8"))
    contract = registry["benchmark"]
    protocol = MaskingProtocol(contract["masking_protocol"])
    roles = tuple(TherapeuticPair(row["drug_id"], row["disease_id"], LabelState(row["evaluation_role"])) for row in pair_rows)
    quarantine = tuple(QuarantineEntry(int(row["fold"]), row["disease_id"], row["role"], row["hide_all_therapeutic_relations"].lower() == "true") for row in quarantine_rows)
    graph = GraphStructure(
        nontherapeutic_directed_triples=int(corpus["base_graph"]["nontherapeutic_directed_triples"]),
        entity_count=int(corpus["entities"]), relation_count=int(corpus["relations"]),
    )
    return FrozenBenchmark(
        benchmark_id=contract["id"], protocol=protocol,
        candidate_ids=tuple(row["drug_id"] for row in candidates),
        disease_folds=tuple((row["disease_id"], int(row["oof_fold"])) for row in diseases),
        role_pairs=roles, quarantine=quarantine, fold_summary=summary, fold_labels=labels,
        graph_structure=graph, expected=contract,
    )


def _failure(fold: int | None, field: str, expected: Any, observed: Any) -> dict:
    return {"fold": fold, "field": field, "expected": expected, "observed": observed, "severity": "ERROR"}


def audit_fold(benchmark: FrozenBenchmark, mask: FoldMask) -> dict:
    """Audit one frozen fold; an injected/altered mask fails these checks."""
    fold = mask.fold
    failures: list[dict] = []
    summary = next((row for row in benchmark.fold_summary if int(row["fold"]) == fold), None)
    labels = next((row for row in benchmark.fold_labels if int(row["fold"]) == fold), None)
    if summary is None or labels is None:
        failures.append(_failure(fold, "frozen_fold_contract", "summary and label row", "missing"))
        return {"fold": fold, "status": "FAIL", "failures": failures}
    expected_targets = tuple(disease_id for disease_id, assigned in benchmark.disease_folds if assigned == fold)
    manifest_targets = tuple(row.disease_id for row in benchmark.quarantine if row.fold == fold and row.role == "TARGET")
    manifest_buffers = tuple(row.disease_id for row in benchmark.quarantine if row.fold == fold and row.role == "BUFFER")
    if set(mask.target_ids) != set(expected_targets) or set(manifest_targets) != set(expected_targets):
        failures.append(_failure(fold, "target_membership", sorted(expected_targets), sorted(manifest_targets)))
    if mask.target_ids != expected_targets:
        failures.append(_failure(fold, "target_order", expected_targets[:5], mask.target_ids[:5]))
    if mask.buffer_ids != manifest_buffers:
        failures.append(_failure(fold, "buffer_membership_or_order", manifest_buffers[:5], mask.buffer_ids[:5]))
    if set(mask.target_ids) & set(mask.buffer_ids):
        failures.append(_failure(fold, "target_buffer_disjoint", True, False))
    expected_hidden = frozenset(mask.target_ids) | frozenset(mask.buffer_ids)
    if mask.hidden_ids != expected_hidden:
        failures.append(_failure(fold, "hidden_membership", len(expected_hidden), len(mask.hidden_ids)))
    if any(not row.hide_all_therapeutic_relations for row in benchmark.quarantine if row.fold == fold):
        failures.append(_failure(fold, "hide_all_therapeutic_relations", True, False))
    if len(set(mask.target_ids)) != len(mask.target_ids) or len(set(mask.buffer_ids)) != len(mask.buffer_ids):
        failures.append(_failure(fold, "quarantine_duplicates", 0, "present"))

    legal_set = set(mask.legal_therapeutic_pairs)
    hidden_set = set(mask.hidden_therapeutic_pairs)
    all_roles = set(benchmark.role_pairs)
    target_id_set = set(mask.target_ids)
    buffer_id_set = set(mask.buffer_ids)
    if legal_set & hidden_set or legal_set | hidden_set != all_roles:
        failures.append(_failure(fold, "therapeutic_partition", len(all_roles), len(legal_set | hidden_set)))
    target_leaks = sum(pair.disease_id in target_id_set for pair in mask.legal_therapeutic_pairs)
    buffer_leaks = sum(pair.disease_id in buffer_id_set for pair in mask.legal_therapeutic_pairs)
    if target_leaks:
        failures.append(_failure(fold, "target_therapeutic_leakage", 0, target_leaks))
    if buffer_leaks:
        failures.append(_failure(fold, "buffer_therapeutic_leakage", 0, buffer_leaks))
    expected_legal = tuple(pair for pair in benchmark.role_pairs if pair.disease_id not in expected_hidden)
    expected_clean = tuple(pair for pair in expected_legal if pair.role is LabelState.CLEAN_INDICATION)
    if mask.legal_therapeutic_pairs != expected_legal:
        failures.append(_failure(fold, "legal_therapeutic_order_and_completeness", len(expected_legal), len(mask.legal_therapeutic_pairs)))
    if mask.legal_clean_pairs != expected_clean:
        failures.append(_failure(fold, "legal_clean_order_and_completeness", len(expected_clean), len(mask.legal_clean_pairs)))
    if any(pair.role is not LabelState.CLEAN_INDICATION for pair in mask.legal_clean_pairs):
        failures.append(_failure(fold, "clean_role_only", "CLEAN_INDICATION", "other role"))
    for field, expected_value, actual in (
        ("target_count", int(summary["target_diseases"]), len(mask.target_ids)),
        ("buffer_count", int(summary["buffer_diseases"]), len(mask.buffer_ids)),
        ("hidden_count", int(summary["hidden_diseases_total"]), len(mask.hidden_ids)),
        ("legal_clean_count", benchmark.expected["fold_clean_counts"][fold], len(mask.legal_clean_pairs)),
        ("fold_summary_legal_clean", int(summary["clean_training_pairs_remaining"]), len(mask.legal_clean_pairs)),
        ("fold_label_legal_clean", int(labels["legal_clean_indication_pairs"]), len(mask.legal_clean_pairs)),
        ("fold_label_expected_legal", int(labels["expected_legal_pairs"]), len(mask.legal_clean_pairs)),
        ("legal_therapeutic_count", int(summary["therapeutic_training_pairs_remaining"]), len(mask.legal_therapeutic_pairs)),
    ):
        if expected_value != actual:
            failures.append(_failure(fold, field, expected_value, actual))
    if len(mask.hidden_clean_pairs) != int(labels["hidden_clean_indication_pairs"]):
        failures.append(_failure(fold, "hidden_clean_count", int(labels["hidden_clean_indication_pairs"]), len(mask.hidden_clean_pairs)))

    # Cell 13's adjacency was collapsed to a unique BUFFER set per fold in the
    # frozen manifest. This tests each (fold, buffered disease) exposure once;
    # it does not claim to enumerate individual target-neighbor graph edges.
    tested_exposures = len(manifest_buffers)
    surviving_exposures = len(set(manifest_buffers) - mask.hidden_ids)
    if surviving_exposures or int(summary["direct_ontology_leaks"]) != 0 or int(labels["direct_hidden_label_leaks"]) != 0:
        failures.append(_failure(fold, "direct_ontology_leakage", 0, surviving_exposures))
    graph_preserved = mask.graph_structure is benchmark.graph_structure
    if not graph_preserved:
        failures.append(_failure(fold, "nontherapeutic_structure_identity", "same frozen structure", "changed"))
    return {
        "fold": fold, "status": "PASS" if not failures else "FAIL",
        "target_count": len(mask.target_ids), "buffer_count": len(mask.buffer_ids),
        "target_disease_ids": list(mask.target_ids), "buffer_disease_ids": list(mask.buffer_ids),
        "hidden_disease_count": len(mask.hidden_ids),
        "legal_clean_training_count": len(mask.legal_clean_pairs),
        "hidden_clean_count": len(mask.hidden_clean_pairs),
        "legal_therapeutic_count": len(mask.legal_therapeutic_pairs),
        "excluded_target_clean_count": sum(pair.disease_id in target_id_set for pair in mask.hidden_clean_pairs),
        "excluded_buffer_clean_count": sum(pair.disease_id in buffer_id_set for pair in mask.hidden_clean_pairs),
        "all_remaining_legal_clean_retained": mask.legal_clean_pairs == expected_clean,
        "all_hidden_therapeutic_excluded": not (legal_set & hidden_set) and legal_set | hidden_set == all_roles and target_leaks == 0 and buffer_leaks == 0,
        "target_order_preserved": mask.target_ids == expected_targets,
        "buffer_order_preserved": mask.buffer_ids == manifest_buffers,
        "target_therapeutic_leaks": target_leaks,
        "buffer_therapeutic_leaks": buffer_leaks,
        "tested_direct_ontology_leakage_paths": tested_exposures,
        "tested_path_unit": "unique (fold, buffered direct-neighbor disease) exposure; target-neighbor edges collapsed",
        "surviving_direct_ontology_leakage_paths": surviving_exposures,
        "nontherapeutic_structure_preserved": graph_preserved,
        "nontherapeutic_directed_triples_preserved": mask.graph_structure.nontherapeutic_directed_triples,
        "failures": failures,
    }


def validate_frozen_semantics(benchmark: FrozenBenchmark) -> dict:
    """Validate frozen fold/mask understanding without deriving benchmark files."""
    failures: list[dict] = []
    expected = benchmark.expected
    if benchmark.protocol is not MaskingProtocol.CANONICAL_1HOP:
        failures.append(_failure(None, "primary_protocol", expected["masking_protocol"], benchmark.protocol.value))
    if len(benchmark.candidate_ids) != expected["candidate_count"]:
        failures.append(_failure(None, "candidate_count", expected["candidate_count"], len(benchmark.candidate_ids)))
    if len(benchmark.disease_folds) != expected["primary_disease_count"]:
        failures.append(_failure(None, "primary_disease_count", expected["primary_disease_count"], len(benchmark.disease_folds)))
    clean_count = sum(pair.role is LabelState.CLEAN_INDICATION for pair in benchmark.role_pairs)
    if clean_count != expected["global_clean_pairs"]:
        failures.append(_failure(None, "global_clean_pairs", expected["global_clean_pairs"], clean_count))
    if len({(pair.drug_id, pair.disease_id) for pair in benchmark.role_pairs}) != len(benchmark.role_pairs):
        failures.append(_failure(None, "therapeutic_pair_uniqueness", len(benchmark.role_pairs), "duplicates"))
    assigned = [disease_id for disease_id, _ in benchmark.disease_folds]
    if len(assigned) != len(set(assigned)):
        failures.append(_failure(None, "disease_fold_uniqueness", "each disease once", "duplicates"))
    folds = sorted({fold for _, fold in benchmark.disease_folds})
    if folds != list(range(expected["folds"])):
        failures.append(_failure(None, "fold_ids", list(range(expected["folds"])), folds))
    if benchmark.graph_structure.nontherapeutic_directed_triples != expected["nontherapeutic_directed_triples"]:
        failures.append(_failure(None, "nontherapeutic_structure_count", expected["nontherapeutic_directed_triples"], benchmark.graph_structure.nontherapeutic_directed_triples))
    if benchmark.graph_structure.nontherapeutic_directed_triples + expected["therapeutic_directed_rows_removed"] != expected["raw_edge_rows"]:
        failures.append(_failure(None, "graph_partition_count", expected["raw_edge_rows"], benchmark.graph_structure.nontherapeutic_directed_triples + expected["therapeutic_directed_rows_removed"]))
    fold_reports = [audit_fold(benchmark, benchmark.mask(fold)) for fold in range(expected["folds"])]
    failures.extend(failure for report in fold_reports for failure in report["failures"])
    return {
        "benchmark_id": benchmark.benchmark_id,
        "protocol_id": benchmark.protocol.value,
        "fold_count": expected["folds"],
        "unknown_pair_semantics": LabelState.UNKNOWN_UNLABELED.value,
        "nontherapeutic_graph_evidence_loaded": False,
        "nontherapeutic_structure_contract_preserved": all(report.get("nontherapeutic_structure_preserved") for report in fold_reports),
        "tested_direct_ontology_leakage_paths": sum(report.get("tested_direct_ontology_leakage_paths", 0) for report in fold_reports),
        "tested_path_unit": "unique (fold, buffered direct-neighbor disease) exposure; individual ontology edges unavailable in frozen tables",
        "surviving_direct_ontology_leakage_paths": sum(report.get("surviving_direct_ontology_leakage_paths", 0) for report in fold_reports),
        "folds": fold_reports,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "limitations": ["The frozen quarantine stores a union of direct neighbors per fold. Without the raw graph, individual target-neighbor edges and completeness of that union cannot be independently enumerated."],
    }
