"""Gate-4 E1 unit, information-flow, axis, and full-local tests."""

from __future__ import annotations

import csv
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from primekg_repurposing.evaluation import load_frozen_evaluator, reproduce_archive
from primekg_repurposing.experts.e1_gene_similarity import (
    ABSTENTION_REASON,
    build_gene_profiles,
    compare_scores,
    gene_weight,
    package_run,
    prepare_profiles,
    save_score_archive,
    score_prepared_profiles,
)
from primekg_repurposing.score_archive import ScoreArchive, load_score_archive


ROOT = Path(__file__).resolve().parents[1]
LONG_DISEASE = "MONDO:0000001|DOID:12345678901234567890"


def edge(relation, x_id, x_type, y_id, y_type):
    return (relation, x_id, x_type, y_id, y_type)


def fixture_edges():
    return [
        edge("drug_protein", "D1", "drug", "G1", "gene/protein"),
        edge("drug_protein", "G1", "gene/protein", "D1", "drug"),
        edge("drug_protein", "D1", "drug", "G1", "gene/protein"),
        edge("drug_protein", "D2", "drug", "G2", "gene/protein"),
        edge("disease_protein", LONG_DISEASE, "disease", "G1", "gene/protein"),
        edge("disease_protein", "G1", "gene/protein", LONG_DISEASE, "disease"),
        edge("disease_protein", "OTHER", "disease", "G1", "gene/protein"),
        edge("indication", "D2", "drug", LONG_DISEASE, "disease"),
        edge("disease_disease", LONG_DISEASE, "disease", "OTHER", "disease"),
    ]


def prepared(edges=None, candidates=("D2", "D1"), diseases=("EMPTY", LONG_DISEASE)):
    return prepare_profiles(build_gene_profiles(edges or fixture_edges(), candidates, diseases))


class E1FormulaAndProfileTests(unittest.TestCase):
    def test_gene_weight_formula(self):
        expected = np.float32(1.0 / np.log2(2.0 + 3 + 5))
        self.assertEqual(gene_weight(3, 5), expected)

    def test_disease_profile_construction(self):
        profiles = build_gene_profiles(fixture_edges(), ("D1", "D2"), (LONG_DISEASE,))
        self.assertEqual(profiles.primary_disease_gene_pairs, {(LONG_DISEASE, "G1")})
        self.assertIn(("OTHER", "G1"), profiles.all_disease_gene_pairs)

    def test_drug_profile_construction(self):
        profiles = build_gene_profiles(fixture_edges(), ("D1", "D2"), (LONG_DISEASE,))
        self.assertEqual(profiles.drug_gene_pairs, {("D1", "G1"), ("D2", "G2")})

    def test_shared_gene_weighted_numerator_and_denominator(self):
        prep = prepared(candidates=("D1",), diseases=(LONG_DISEASE,))
        scores = score_prepared_profiles(prep)
        self.assertEqual(scores.dtype, np.float32)
        weight = prep.gene_weights[0]
        expected = np.float32(weight / np.float32(np.sqrt(weight) * np.sqrt(weight)))
        self.assertEqual(scores[0, 0], expected)

    def test_no_shared_genes_scores_zero(self):
        scores = score_prepared_profiles(prepared())
        self.assertEqual(scores[1, 0], np.float32(0.0))

    def test_empty_disease_profile_abstains(self):
        prep = prepared()
        run = package_run(prep, score_prepared_profiles(prep), benchmark_id="B")
        self.assertFalse(run.applicable[0])
        self.assertEqual(run.abstention_reasons[0], ABSTENTION_REASON)

    def test_empty_drug_profile_is_zero(self):
        prep = prepared(candidates=("NO_PROFILE", "D1"), diseases=(LONG_DISEASE,))
        scores = score_prepared_profiles(prep)
        self.assertEqual(scores[0, 0], 0.0)
        self.assertGreater(scores[0, 1], 0.0)

    def test_duplicate_and_reciprocal_edges_are_deduplicated(self):
        profiles = build_gene_profiles(fixture_edges(), ("D1",), (LONG_DISEASE,))
        self.assertEqual(len(profiles.drug_gene_pairs), 1)
        self.assertEqual(len(profiles.primary_disease_gene_pairs), 1)

    def test_reciprocal_direction_is_accepted(self):
        edges = [
            edge("drug_protein", "G", "gene/protein", "D", "drug"),
            edge("disease_protein", "G", "gene/protein", "X", "disease"),
        ]
        profiles = build_gene_profiles(edges, ("D",), ("X",))
        self.assertEqual(profiles.drug_gene_pairs, {("D", "G")})
        self.assertEqual(profiles.primary_disease_gene_pairs, {("X", "G")})

    def test_candidate_order_is_preserved(self):
        prep = prepared(candidates=("D2", "D1"), diseases=(LONG_DISEASE,))
        self.assertEqual(prep.candidate_ids, ("D2", "D1"))
        self.assertEqual(tuple(score_prepared_profiles(prep)[0] > 0), (False, True))

    def test_disease_order_is_preserved(self):
        prep = prepared(diseases=("EMPTY", LONG_DISEASE))
        self.assertEqual(prep.disease_ids, ("EMPTY", LONG_DISEASE))
        scores = score_prepared_profiles(prep)
        self.assertFalse(np.any(scores[0]))
        self.assertTrue(np.any(scores[1]))

    def test_repeated_runs_are_bitwise_identical(self):
        prep = prepared()
        self.assertTrue(np.array_equal(score_prepared_profiles(prep), score_prepared_profiles(prep)))

    def test_long_composite_ids_remain_intact(self):
        profiles = build_gene_profiles(fixture_edges(), ("D1",), (LONG_DISEASE,))
        self.assertEqual(profiles.disease_ids[0], LONG_DISEASE)
        self.assertIn((LONG_DISEASE, "G1"), profiles.primary_disease_gene_pairs)


class E1InformationFlowTests(unittest.TestCase):
    def _scores(self, extra):
        prep = prepare_profiles(build_gene_profiles(fixture_edges() + extra, ("D1", "D2"), (LONG_DISEASE,)))
        return score_prepared_profiles(prep)

    def test_therapeutic_edges_cannot_change_scores(self):
        first = self._scores([edge("indication", "D1", "drug", LONG_DISEASE, "disease")])
        second = self._scores([edge("contraindication", "D2", "drug", LONG_DISEASE, "disease")])
        self.assertTrue(np.array_equal(first, second))

    def test_disease_ontology_edges_cannot_change_scores(self):
        first = self._scores([edge("disease_disease", LONG_DISEASE, "disease", "A", "disease")])
        second = self._scores([edge("disease_disease", LONG_DISEASE, "disease", "B", "disease")])
        self.assertTrue(np.array_equal(first, second))


class E1ArchiveContractTests(unittest.TestCase):
    def test_round_trip_uses_non_object_axes(self):
        prep = prepared()
        run = package_run(prep, score_prepared_profiles(prep), benchmark_id="B")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scores.npz"
            save_score_archive(run, path)
            archive = load_score_archive(path)
        self.assertEqual(archive.disease_ids, run.disease_ids)
        self.assertEqual(archive.drug_ids, run.candidate_ids)
        self.assertTrue(np.array_equal(archive.scores, run.scores))

    def test_score_archive_axis_mismatch_fails(self):
        prep = prepared()
        run = package_run(prep, score_prepared_profiles(prep), benchmark_id="B")
        historical = ScoreArchive(run.scores, run.disease_ids, tuple(reversed(run.candidate_ids)))
        with self.assertRaisesRegex(ValueError, "axis"):
            compare_scores(run, historical)


@unittest.skipUnless(os.environ.get("PRIMEKG_GATE4_REPORT"), "requires completed full-local Gate-4 run")
class FullLocalE1EquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(Path(os.environ["PRIMEKG_GATE4_REPORT"]).read_text(encoding="utf-8"))

    def test_applicability_matches_frozen_e1(self):
        self.assertEqual(self.report["applicable_count"], 504)
        self.assertEqual(self.report["abstention_count"], 234)
        self.assertTrue(self.report["evaluator_equivalence"]["applicability_exact"])

    def test_genuine_historical_score_archive_comparison_succeeds(self):
        score = self.report["score_equivalence"]
        self.assertEqual(score["shape"], [738, 7957])
        self.assertEqual(score["scores_compared"], 738 * 7957)
        self.assertEqual(score["unequal_value_count"], 0)
        self.assertEqual(score["max_absolute_difference"], 0.0)

    def test_gate3_evaluator_produces_frozen_disease_metrics(self):
        evaluation = self.report["evaluator_equivalence"]
        self.assertLessEqual(evaluation["max_absolute_disease_level_difference"], 2e-15)
        self.assertEqual(evaluation["historical_archive_gate3_status"], "PASS")

    def test_macro_recall50_reproduces_exactly(self):
        evaluation = self.report["evaluator_equivalence"]
        self.assertEqual(evaluation["macro_recall50_clean"], evaluation["macro_recall50_frozen"])
        self.assertEqual(evaluation["macro_recall50_absolute_difference"], 0.0)


if __name__ == "__main__":
    unittest.main()
