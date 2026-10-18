"""Focused Gate-1 corruption and provenance tests; no large graph or GPU."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from primekg_repurposing.cli import main
from primekg_repurposing.provenance import VerificationState, validate


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


class ProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        shutil.copytree(FIXTURES / "data", self.data)
        self.registry = self.root / "registry.json"
        shutil.copyfile(FIXTURES / "registry.json", self.registry)

    def report(self) -> dict:
        return validate(self.registry, self.data, "SMOKE")

    def state(self, report: dict, artifact: str) -> str:
        return next(item for item in report["artifacts"] if item["artifact_id"] == artifact)["verification_state"]

    def fields(self, report: dict) -> set[str]:
        return {finding["field"] for finding in report["failures"]}

    def mutate(self, logical: str, old: str, new: str) -> None:
        path = self.data / logical
        content = path.read_text(encoding="utf-8")
        self.assertIn(old, content)
        path.write_text(content.replace(old, new, 1), encoding="utf-8")

    def test_correct_sha_passes(self) -> None:
        report = self.report()
        self.assertEqual(self.state(report, "benchmark/p1_v0_candidate_drugs.csv"), VerificationState.FOUND_AND_VERIFIED.value)
        self.assertFalse(report["required_failure"])

    def test_modified_file_fails_sha(self) -> None:
        self.mutate("benchmark/p1_v0_candidate_drugs.csv", "Drug one", "Other one")
        report = self.report()
        self.assertEqual(self.state(report, "benchmark/p1_v0_candidate_drugs.csv"), VerificationState.FOUND_HASH_MISMATCH.value)
        self.assertIn("sha256", self.fields(report))

    def test_wrong_candidate_count_fails(self) -> None:
        self.mutate("benchmark/p1_v0_candidate_drugs.csv", "D2,Drug two\n", "")
        self.assertIn("row_count", self.fields(self.report()))

    def test_wrong_disease_count_fails(self) -> None:
        self.mutate("benchmark/p1_v0_primary_diseases.csv", "Y,1\n", "")
        self.assertIn("row_count", self.fields(self.report()))

    def test_wrong_truth_pair_count_fails(self) -> None:
        self.mutate("benchmark/p1_v0_primary_truth.csv", "Y,D2,CLEAN_INDICATION\n", "")
        self.assertIn("row_count", self.fields(self.report()))

    def test_candidate_order_fails(self) -> None:
        path = self.data / "benchmark/p1_v0_candidate_drugs.csv"
        path.write_text("drug_id,drug_name\nD2,Drug two\nD1,Drug one\n", encoding="utf-8")
        report = self.report()
        self.assertIn("axis.candidates.sha256", self.fields(report))
        self.assertEqual(next(item for item in report["artifacts"] if item["artifact_id"] == "benchmark/p1_v0_candidate_drugs.csv")["axis_state"], "FAIL")

    def test_disease_order_fails(self) -> None:
        path = self.data / "benchmark/p1_v0_primary_diseases.csv"
        path.write_text("disease_id,oof_fold\nY,1\nX,0\n", encoding="utf-8")
        report = self.report()
        self.assertIn("axis.diseases.sha256", self.fields(report))

    def test_matrix_disease_axis_fails(self) -> None:
        path = self.data / "reference_results/expert_matrix.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join([lines[0], lines[2], lines[1]]) + "\n", encoding="utf-8")
        self.assertIn("axis.diseases.order", self.fields(self.report()))

    def test_matrix_seed_identity_fails(self) -> None:
        self.mutate("reference_results/expert_matrix.csv", "E1_FIXTURE,0,X", "E1_FIXTURE,9,X")
        self.assertIn("seed", self.fields(self.report()))

    def test_missing_required_column_fails(self) -> None:
        self.mutate("benchmark/p1_v0_candidate_drugs.csv", "drug_id,drug_name", "drug_id,name")
        self.assertIn("column.drug_name", self.fields(self.report()))

    def test_external_registration_is_not_local(self) -> None:
        report = self.report()
        self.assertEqual(self.state(report, "external/checkpoint.pt"), VerificationState.REGISTERED_EXTERNAL_NOT_LOCAL.value)
        self.assertNotIn("external/checkpoint.pt", {finding["artifact_id"] for finding in report["failures"]})

    def test_unknown_hash_remains_unknown(self) -> None:
        report = self.report()
        item = next(item for item in report["artifacts"] if item["artifact_id"] == "unknown.bin")
        self.assertEqual(item["verification_state"], VerificationState.UNKNOWN_HASH.value)
        self.assertEqual(item["hash_state"], "UNKNOWN")

    def test_wrong_benchmark_id_fails(self) -> None:
        self.mutate("benchmark/p1_v0_benchmark_manifest.json", "P1_TRACK_A_PRIMEKG_V0_FIXTURE", "WRONG_BENCHMARK")
        self.assertIn("benchmark_id", self.fields(self.report()))

    def test_evaluator_version_mismatch_fails(self) -> None:
        self.mutate("benchmark/p1_v0_evaluator_config_v1_1_tiesafe.json", "1.1_tiesafe", "1.0")
        self.assertIn("evaluator_version", self.fields(self.report()))

    def test_missing_required_file_fails_and_cli_exits_nonzero(self) -> None:
        (self.data / "benchmark/p1_v0_primary_truth.csv").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["validate", "--tier", "smoke", "--registry", str(self.registry), "--data-root", str(self.data)])
        self.assertEqual(code, 1)
        self.assertEqual(self.state(self.report(), "benchmark/p1_v0_primary_truth.csv"), VerificationState.MISSING_REQUIRED.value)

    def test_explicit_data_root_overrides_environment(self) -> None:
        with patch.dict(os.environ, {"PRIMEKG_DATA_ROOT": str(self.root / "nonexistent")}):
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["validate", "--tier", "smoke", "--registry", str(self.registry), "--data-root", str(self.data)])
        self.assertEqual(code, 0)

    def test_raw_kg_is_streamed_and_checks_required_columns(self) -> None:
        import hashlib

        raw = self.data / "raw/kg.csv"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text("relation,x_id,x_type,y_id,y_type\nindication,D1,drug,X,disease\n", encoding="utf-8")
        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        registry["artifacts"].append({
            "artifact_id": "raw/kg.csv", "filename": "kg.csv", "semantic_role": "raw fixture",
            "provenance_class": "RAW_EXTERNAL_INPUT", "expected_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "expected_size": raw.stat().st_size, "logical_path": "raw/kg.csv", "location": "bundled_local",
            "producer": "test fixture", "dependencies": [], "required_for": ["SMOKE"],
            "schema": {"type": "csv", "required_columns": ["relation", "x_id", "x_type", "y_id", "y_type"]}, "expected_rows": 1,
        })
        self.registry.write_text(json.dumps(registry), encoding="utf-8")
        self.assertEqual(self.state(self.report(), "raw/kg.csv"), VerificationState.FOUND_AND_VERIFIED.value)
        self.mutate("raw/kg.csv", "y_type", "wrong_type")
        self.assertIn("column.y_type", self.fields(self.report()))

    def test_score_tensor_candidate_axis_fails_when_numpy_available(self) -> None:
        try:
            import numpy as np
        except ImportError:
            self.skipTest("optional NumPy is not installed")
        path = self.data / "external/scores.npz"
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, scores=np.zeros((2, 2)), disease_ids=np.asarray(["X", "Y"]), drug_ids=np.asarray(["D2", "D1"]))
        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        registry["artifacts"].append({
            "artifact_id": "external/scores.npz", "filename": "scores.npz", "semantic_role": "score fixture",
            "provenance_class": "GENERATED_DERIVED_ARTIFACT", "expected_sha256": None, "expected_size": None,
            "logical_path": "external/scores.npz", "location": "bundled_local", "producer": "test fixture",
            "dependencies": [], "required_for": ["SMOKE"],
            "schema": {"type": "npz_score", "required_arrays": ["scores", "disease_ids", "drug_ids"], "expected_shape": [2, 2], "disease_axis": "diseases", "candidate_axis": "candidates"},
        })
        self.registry.write_text(json.dumps(registry), encoding="utf-8")
        self.assertIn("axis.candidates.order", self.fields(self.report()))


if __name__ == "__main__":
    unittest.main()
