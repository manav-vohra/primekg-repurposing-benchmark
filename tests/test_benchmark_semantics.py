"""Gate 2A masking tests using frozen contracts and tiny synthetic roles."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from primekg_repurposing.benchmark import (
    FoldMask,
    FrozenBenchmark,
    GraphStructure,
    LabelState,
    MaskingProtocol,
    QuarantineEntry,
    TherapeuticPair,
    audit_fold,
    load_frozen_benchmark,
    validate_frozen_semantics,
)
from primekg_repurposing.provenance import validate


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "artifacts/registry.json"
DATA = ROOT / "artifacts/frozen"


def synthetic() -> tuple[FrozenBenchmark, str]:
    # Cell 19 truncated >128-character composite disease IDs. Cell 19A
    # localized the defect; Cell 19B repaired the corpus. Python strings here
    # retain the complete ID for membership and masking.
    long_id = "MONDO:" + "x" * 150
    roles = (
        TherapeuticPair("D1", long_id, LabelState.CLEAN_INDICATION),
        TherapeuticPair("D2", "d-buffer", LabelState.CLEAN_INDICATION),
        TherapeuticPair("D1", "d-safe", LabelState.CLEAN_INDICATION),
        TherapeuticPair("D2", "d-b", LabelState.CLEAN_INDICATION),
        TherapeuticPair("D1", "d-buffer", LabelState.CONTRAINDICATION_ONLY),
    )
    quarantine = (
        QuarantineEntry(0, long_id, "TARGET", True),
        QuarantineEntry(0, "d-buffer", "BUFFER", True),
        QuarantineEntry(1, "d-b", "TARGET", True),
    )
    summary = (
        {"fold": "0", "target_diseases": "1", "buffer_diseases": "1", "hidden_diseases_total": "2", "clean_training_pairs_remaining": "2", "therapeutic_training_pairs_remaining": "2", "direct_ontology_leaks": "0"},
        {"fold": "1", "target_diseases": "1", "buffer_diseases": "0", "hidden_diseases_total": "1", "clean_training_pairs_remaining": "3", "therapeutic_training_pairs_remaining": "4", "direct_ontology_leaks": "0"},
    )
    labels = (
        {"fold": "0", "legal_clean_indication_pairs": "2", "hidden_clean_indication_pairs": "2", "expected_legal_pairs": "2", "direct_hidden_label_leaks": "0"},
        {"fold": "1", "legal_clean_indication_pairs": "3", "hidden_clean_indication_pairs": "1", "expected_legal_pairs": "3", "direct_hidden_label_leaks": "0"},
    )
    graph = GraphStructure(
        nontherapeutic_directed_triples=5, entity_count=6, relation_count=2,
        evidence_edges=((long_id, "disease_disease", "d-buffer"), (long_id, "disease_protein", "P1")),
    )
    benchmark = FrozenBenchmark(
        benchmark_id="P1_TRACK_A_PRIMEKG_V0_FIXTURE", protocol=MaskingProtocol.CANONICAL_1HOP,
        candidate_ids=("D1", "D2"), disease_folds=((long_id, 0), ("d-b", 1)),
        role_pairs=roles, quarantine=quarantine, fold_summary=summary,
        fold_labels=labels, graph_structure=graph,
        expected={"id": "P1_TRACK_A_PRIMEKG_V0_FIXTURE", "masking_protocol": "CANONICAL_1HOP", "candidate_count": 2,
                  "primary_disease_count": 2, "folds": 2, "fold_clean_counts": [2, 3], "global_clean_pairs": 4,
                  "nontherapeutic_directed_triples": 5, "therapeutic_directed_rows_removed": 2, "raw_edge_rows": 7},
    )
    return benchmark, long_id


class FrozenSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate1_report = validate(REGISTRY, DATA, "REFERENCE")
        cls.frozen = load_frozen_benchmark(REGISTRY, DATA, cls.gate1_report)

    def test_all_eight_frozen_legal_clean_counts_match(self) -> None:
        report = validate_frozen_semantics(self.frozen)
        self.assertEqual(report["status"], "PASS", report["failures"][:3])
        self.assertEqual([fold["legal_clean_training_count"] for fold in report["folds"]], [6856, 6828, 6990, 7119, 6871, 7183, 7091, 6827])
        self.assertEqual([fold["target_count"] for fold in report["folds"]], [93, 93, 92, 92, 92, 92, 92, 92])
        self.assertEqual([fold["buffer_count"] for fold in report["folds"]], [109, 125, 83, 118, 110, 99, 120, 146])

    def test_frozen_zero_surviving_direct_exposures(self) -> None:
        report = validate_frozen_semantics(self.frozen)
        self.assertEqual(report["tested_direct_ontology_leakage_paths"], 910)
        self.assertEqual(report["surviving_direct_ontology_leakage_paths"], 0)
        self.assertTrue(report["nontherapeutic_structure_contract_preserved"])

    def test_frozen_ordering_preserved(self) -> None:
        mask = self.frozen.mask(0)
        expected = tuple(disease_id for disease_id, fold in self.frozen.disease_folds if fold == 0)
        self.assertEqual(mask.target_ids, expected)
        self.assertEqual(mask.legal_clean_pairs, tuple(pair for pair in self.frozen.role_pairs if pair.role is LabelState.CLEAN_INDICATION and pair.disease_id not in mask.hidden_ids))

    def test_frozen_target_order_corruption_fails(self) -> None:
        mask = self.frozen.mask(0)
        altered = replace(mask, target_ids=tuple(reversed(mask.target_ids)))
        self.assertIn("target_order", {finding["field"] for finding in audit_fold(self.frozen, altered)["failures"]})


class SyntheticSemanticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.benchmark, self.long_id = synthetic()
        self.mask = self.benchmark.mask(0)

    def fields(self, mask: FoldMask) -> set[str]:
        return {finding["field"] for finding in audit_fold(self.benchmark, mask)["failures"]}

    def test_target_clean_leak_detected(self) -> None:
        target_pair = self.benchmark.role_pairs[0]
        altered = replace(self.mask, legal_clean_pairs=self.mask.legal_clean_pairs + (target_pair,), legal_therapeutic_pairs=self.mask.legal_therapeutic_pairs + (target_pair,))
        self.assertIn("target_therapeutic_leakage", self.fields(altered))

    def test_buffer_clean_leak_detected(self) -> None:
        buffer_pair = self.benchmark.role_pairs[1]
        altered = replace(self.mask, legal_clean_pairs=self.mask.legal_clean_pairs + (buffer_pair,), legal_therapeutic_pairs=self.mask.legal_therapeutic_pairs + (buffer_pair,))
        self.assertIn("buffer_therapeutic_leakage", self.fields(altered))

    def test_legal_nonbuffer_training_label_remains(self) -> None:
        safe_pair = self.benchmark.role_pairs[2]
        self.assertIn(safe_pair, self.mask.legal_clean_pairs)
        self.assertIn("legal_clean_order_and_completeness", self.fields(replace(self.mask, legal_clean_pairs=tuple(pair for pair in self.mask.legal_clean_pairs if pair != safe_pair))))

    def test_u128_regression_full_identifier_and_count(self) -> None:
        self.assertGreater(len(self.long_id), 128)
        self.assertIn(self.long_id, self.mask.target_ids)
        self.assertIn(self.long_id, self.mask.hidden_ids)
        self.assertNotIn(self.benchmark.role_pairs[0], self.mask.legal_clean_pairs)
        self.assertEqual(len(self.mask.legal_clean_pairs), 2)
        self.assertEqual(validate_frozen_semantics(self.benchmark)["status"], "PASS")

    def test_wrong_fold_membership_fails(self) -> None:
        altered = replace(self.benchmark, disease_folds=((self.long_id, 1), ("d-b", 1)))
        self.assertEqual(validate_frozen_semantics(altered)["status"], "FAIL")

    def test_wrong_quarantine_membership_fails(self) -> None:
        altered_entries = list(self.benchmark.quarantine)
        altered_entries[1] = replace(altered_entries[1], disease_id="d-safe")
        altered = replace(self.benchmark, quarantine=tuple(altered_entries))
        self.assertEqual(validate_frozen_semantics(altered)["status"], "FAIL")

    def test_nontherapeutic_structure_is_same_object(self) -> None:
        self.assertIs(self.mask.graph_structure, self.benchmark.graph_structure)
        self.assertEqual(self.mask.graph_structure.evidence_edges, self.benchmark.graph_structure.evidence_edges)
        self.assertIn("nontherapeutic_structure_identity", self.fields(replace(self.mask, graph_structure=GraphStructure(0, 0, 0))))

    def test_unknown_pair_is_unlabeled_not_negative(self) -> None:
        self.assertEqual(self.benchmark.label_state("D2", "d-safe"), LabelState.UNKNOWN_UNLABELED)

    def test_direct_ontology_exposure_injection_is_detected(self) -> None:
        altered = replace(self.mask, hidden_ids=frozenset({self.long_id}))
        report = audit_fold(self.benchmark, altered)
        self.assertEqual(report["surviving_direct_ontology_leakage_paths"], 1)
        self.assertIn("direct_ontology_leakage", {finding["field"] for finding in report["failures"]})

    def test_other_protocols_recognized_but_deferred(self) -> None:
        for protocol in (MaskingProtocol.TARGET_ONLY, MaskingProtocol.STRICT_2HOP):
            with self.subTest(protocol=protocol):
                with self.assertRaises(NotImplementedError):
                    replace(self.benchmark, protocol=protocol).mask(0)


class Gate1BoundaryTests(unittest.TestCase):
    def test_mutated_quarantine_and_disease_order_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / "frozen"
            shutil.copytree(DATA, data)
            for logical, old, new in (
                ("benchmark/p1_v0_k8_quarantine_manifest.csv", ",BUFFER,True", ",TARGET,True"),
                ("benchmark/p1_v0_primary_diseases.csv", "10198,3", "99999,3"),
            ):
                path = data / logical
                content = path.read_text(encoding="utf-8")
                self.assertIn(old, content)
                path.write_text(content.replace(old, new, 1), encoding="utf-8")
                report = validate(REGISTRY, data, "REFERENCE")
                self.assertTrue(report["required_failure"])
                with self.assertRaises(ValueError):
                    load_frozen_benchmark(REGISTRY, data, report)
                path.write_text(content, encoding="utf-8")

    def test_stale_successful_gate1_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / "frozen"
            shutil.copytree(DATA, data)
            report = validate(REGISTRY, data, "REFERENCE")
            self.assertFalse(report["required_failure"])
            path = data / "benchmark/p1_v0_k8_quarantine_manifest.csv"
            path.write_text(path.read_text(encoding="utf-8").replace(",BUFFER,True", ",TARGET,True", 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                load_frozen_benchmark(REGISTRY, data, report)


if __name__ == "__main__":
    unittest.main()
