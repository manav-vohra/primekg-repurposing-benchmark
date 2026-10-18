"""Gate 2B small-graph tests; canonical full-local test is opt-in."""

from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from primekg_repurposing.reconstruction import (
    classify_role,
    compare_artifacts,
    derive_buffers,
    make_fold_assignment,
    reconstruct,
    verified_raw_path,
)

FIELDS = ["relation", "display_relation", "x_id", "x_type", "x_name", "x_source", "y_id", "y_type", "y_name", "y_source"]
ROOT = Path(__file__).resolve().parents[1]
LONG_ID = "disease_" + "composite_" * 20


def edge(relation, x_id, x_type, y_id, y_type, x_name=None, y_name=None):
    return {"relation": relation, "display_relation": relation, "x_id": x_id, "x_type": x_type, "x_name": x_name or x_id, "x_source": "fixture", "y_id": y_id, "y_type": y_type, "y_name": y_name or y_id, "y_source": "fixture"}


def reciprocal(relation, drug, disease):
    return [edge(relation, drug, "drug", disease, "disease"), edge(relation, disease, "disease", drug, "drug")]


def fixture_rows():
    rows = []
    for disease in (LONG_ID, "d2"):
        for drug in ("DB1", "DB2", "DB3"):
            rows += reciprocal("indication", drug, disease)
    rows += reciprocal("indication", "DB4", "d2")
    rows += reciprocal("contraindication", "DB4", "d2")
    rows += reciprocal("contraindication", "DB4", LONG_ID)
    rows += reciprocal("off-label use", "DB4", LONG_ID)
    rows += reciprocal("off-label use", "DB5", "d2")
    rows += reciprocal("contraindication", "DB6", "d2")
    rows += [edge("disease_disease", LONG_ID, "disease", "d2", "disease"), edge("disease_disease", "d2", "disease", LONG_ID, "disease")]
    rows += [edge("drug_protein", "DB7", "drug", "P1", "gene/protein"), edge("drug_protein", "P1", "gene/protein", "DB7", "drug")]
    rows += [edge("disease_protein", LONG_ID, "disease", "P1", "gene/protein"), edge("disease_protein", "P1", "gene/protein", LONG_ID, "disease")]
    return rows


class RoleAndFoldTests(unittest.TestCase):
    def test_role_classifier_all_observed_classes(self):
        cases = {
            ("indication",): "CLEAN_INDICATION",
            ("indication", "contraindication"): "AMBIGUOUS_INDICATION",
            ("contraindication",): "CONTRAINDICATION_ONLY",
            ("off-label use",): "OFFLABEL_ONLY",
            ("contraindication", "off-label use"): "CONFLICTING_NONINDICATION",
        }
        for labels, expected in cases.items():
            self.assertEqual(classify_role(labels), expected)

    def test_unobserved_has_no_negative_role(self):
        with self.assertRaises(ValueError):
            classify_role(())

    def test_deterministic_seeded_fold_assignment(self):
        import pandas as pd

        frame = pd.DataFrame({"disease_id": [f"d{i}" for i in range(40)], "stratum": ["a"] * 40})
        self.assertEqual(make_fold_assignment(frame, 8, 42), make_fold_assignment(frame, 8, 42))
        self.assertNotEqual(make_fold_assignment(frame, 8, 42), make_fold_assignment(frame, 8, 43))

    def test_direct_ontology_buffer_union(self):
        self.assertEqual(derive_buffers({"a", "b"}, {"a": {"b", "c"}, "b": {"a", "c", "d"}}), {"c", "d"})
        self.assertEqual(derive_buffers({"a"}, {"a": {"a"}}), set())

    def test_full_composite_identifier_in_folds(self):
        import pandas as pd

        assignment = make_fold_assignment(pd.DataFrame({"disease_id": [LONG_ID, "d2"], "stratum": ["a", "a"]}), 2, 42)
        self.assertIn(LONG_ID, assignment)
        self.assertGreater(len(LONG_ID), 128)


class TinyProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.raw = cls.root / "kg.csv"
        with cls.raw.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(fixture_rows())
        cls.generated = cls.root / "generated"
        cls.result = reconstruct(cls.raw, cls.generated)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def csv_rows(cls, filename):
        with (cls.generated / filename).open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_reciprocal_therapeutic_pair_canonicalization(self):
        self.assertEqual(self.result["therapeutic_canonical_pairs"], {"indication": 7, "contraindication": 3, "off-label use": 2})

    def test_all_five_pair_roles(self):
        roles = {(row["drug_id"], row["disease_id"]): row["evaluation_role"] for row in self.csv_rows("p1_v0_primary_eval_roles.csv")}
        self.assertEqual(roles[("DB1", LONG_ID)], "CLEAN_INDICATION")
        self.assertEqual(roles[("DB4", "d2")], "AMBIGUOUS_INDICATION")
        self.assertEqual(roles[("DB4", LONG_ID)], "CONFLICTING_NONINDICATION")
        self.assertEqual(roles[("DB5", "d2")], "OFFLABEL_ONLY")
        self.assertEqual(roles[("DB6", "d2")], "CONTRAINDICATION_ONLY")
        self.assertNotIn(("DB7", "d2"), roles)

    def test_candidate_eligibility_is_prelabel(self):
        candidates = self.csv_rows("p1_v0_candidate_drugs.csv")
        self.assertIn("DB7", [row["drug_id"] for row in candidates])
        self.assertEqual(self.result["candidate_universes"], {"U0": 7, "U1": 1, "U2": 1})

    def test_primary_diseases_derive_from_three_clean_pairs(self):
        self.assertEqual(self.result["primary_diseases"], 2)
        self.assertEqual(self.result["primary_truth"], 6)
        self.assertEqual({row["disease_id"] for row in self.csv_rows("p1_v0_primary_diseases.csv")}, {LONG_ID, "d2"})

    def test_ontology_quarantine_and_clean_masking(self):
        rows = self.csv_rows("p1_v0_k8_quarantine_manifest.csv")
        folds = self.csv_rows("p1_v0_fold_summary.csv")
        for row in folds:
            if row["target_diseases"] == "1":
                self.assertEqual(row["buffer_diseases"], "1")
                self.assertEqual(row["clean_training_pairs_remaining"], "0")
                self.assertEqual(row["direct_ontology_leaks"], "0")
        self.assertTrue(any(row["role"] == "BUFFER" and row["disease_id"] == LONG_ID for row in rows))

    def test_nontherapeutic_structure_retained(self):
        self.assertEqual(self.result["census"]["relation_counts"]["disease_disease"], 2)
        self.assertEqual(self.result["census"]["relation_counts"]["disease_protein"], 2)
        self.assertEqual(self.result["census"]["relation_counts"]["drug_protein"], 2)

    def test_long_id_preserved_through_generated_outputs(self):
        self.assertIn(LONG_ID, {row["disease_id"] for row in self.csv_rows("p1_v0_primary_truth.csv")})

    def test_injected_graph_change_changes_reconstruction(self):
        modified = self.root / "mutated.csv"
        with modified.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows([row for row in fixture_rows() if row["relation"] != "disease_disease"])
        result = reconstruct(modified, self.root / "mutated")
        self.assertNotEqual(result["buffer_sizes"], self.result["buffer_sizes"])


class RawIntegrityTests(unittest.TestCase):
    def test_missing_raw_is_reported_before_processing(self):
        raw, report = verified_raw_path(ROOT / "artifacts/registry.json", Path("missing-data-root"))
        self.assertIsNone(raw)
        self.assertEqual(report["status"], "MISSING_RAW_INPUT")

    def test_wrong_hash_is_rejected_before_processing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "kg.csv"
            path.write_text("not PrimeKG", encoding="utf-8")
            raw, report = verified_raw_path(ROOT / "artifacts/registry.json", Path(directory), path)
            self.assertIsNone(raw)
            self.assertEqual(report["status"], "RAW_HASH_MISMATCH")


class EquivalenceComparatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.generated = Path(self.temp.name)
        frozen = ROOT / "artifacts/frozen"
        for filename in ("p1_v0_candidate_drugs.csv", "p1_v0_primary_diseases.csv", "p1_v0_primary_eval_roles.csv", "p1_v0_primary_truth.csv", "p1_v0_k8_quarantine_manifest.csv", "p1_v0_fold_summary.csv", "p1_v0_benchmark_manifest.json"):
            shutil.copyfile(frozen / "benchmark" / filename, self.generated / filename)
        shutil.copyfile(frozen / "recovered_contracts/p1_primary_metric_policy.json", self.generated / "p1_primary_metric_policy.json")

    def tearDown(self):
        self.temp.cleanup()

    def compare(self):
        return compare_artifacts(self.generated, ROOT / "artifacts/frozen", ROOT / "artifacts/registry.json")

    def test_exact_reference_copy_matches(self):
        self.assertTrue(all(item["hash_equivalence"] and item["semantic_equivalence"] for item in self.compare()))

    def test_candidate_axis_corruption_is_scientific_difference(self):
        path = self.generated / "p1_v0_candidate_drugs.csv"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("DB00001", "DBXXXXX", 1), encoding="utf-8")
        item = self.compare()[0]
        self.assertFalse(item["ordered_keys_match"])
        self.assertFalse(item["semantic_equivalence"])
        self.assertEqual(item["first_ordered_mismatch"]["row"], 0)

    def test_disease_axis_corruption_is_scientific_difference(self):
        path = self.generated / "p1_v0_primary_diseases.csv"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("10198", "WRONG", 1), encoding="utf-8")
        item = self.compare()[1]
        self.assertFalse(item["ordered_keys_match"])
        self.assertFalse(item["semantic_equivalence"])

    def test_candidate_order_difference_is_scientific_axis_failure(self):
        path = self.generated / "p1_v0_candidate_drugs.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        lines[1], lines[2] = lines[2], lines[1]
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
        item = self.compare()[0]
        self.assertFalse(item["hash_equivalence"])
        self.assertTrue(item["unordered_content_equivalence"])
        self.assertFalse(item["semantic_equivalence"])
        self.assertFalse(item["ordered_keys_match"])

    def test_json_environment_difference_is_isolated(self):
        path = self.generated / "p1_v0_benchmark_manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["software_environment"]["python"] = "fixture-version"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(manifest, indent=2))
        item = self.compare()[6]
        self.assertEqual(item["classification"], "ENVIRONMENT_METADATA_ONLY_DIFFERENCE")
        self.assertTrue(item["historical_environment_normalized_hash_equivalence"])


@unittest.skipUnless(os.environ.get("PRIMEKG_FULL_LOCAL_RAW"), "requires exact raw PrimeKG; never ordinary CI")
class FullLocalEquivalenceTests(unittest.TestCase):
    def test_canonical_seed_axes_counts_and_hashes(self):
        from primekg_repurposing.reconstruction import compare_artifacts, validate_reconstruction_counts

        raw, report = verified_raw_path(ROOT / "artifacts/registry.json", ROOT / "artifacts/frozen", Path(os.environ["PRIMEKG_FULL_LOCAL_RAW"]))
        self.assertEqual(report["status"], "VERIFIED")
        with tempfile.TemporaryDirectory() as directory:
            result = reconstruct(raw, Path(directory))
            self.assertTrue(all(x["pass"] for x in validate_reconstruction_counts(result, ROOT / "artifacts/registry.json", ROOT / "artifacts/frozen")))
            artifacts = compare_artifacts(Path(directory), ROOT / "artifacts/frozen", ROOT / "artifacts/registry.json")
            self.assertTrue(all(x["semantic_equivalence"] for x in artifacts))
            self.assertTrue(all(x["hash_equivalence"] for x in artifacts if x["artifact"].endswith(".csv")))
            self.assertEqual(result["legal_clean_counts"], [6856, 6828, 6990, 7119, 6871, 7183, 7091, 6827])


if __name__ == "__main__":
    unittest.main()
