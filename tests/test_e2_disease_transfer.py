"""Gate-5 E2 feature, legality, leakage, and full-local equivalence tests."""

from __future__ import annotations

import json
import math
import os
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

from primekg_repurposing.benchmark import (
    FrozenBenchmark,
    GraphStructure,
    LabelState,
    MaskingProtocol,
    QuarantineEntry,
    TherapeuticPair,
)
from primekg_repurposing.experts.e2_disease_transfer import (
    NO_PROFILE,
    build_disease_feature_corpus,
    build_tfidf_profiles,
    feature_token,
    prepare_e2_from_corpus,
    score_e2_prepared,
)


ROOT = Path(__file__).resolve().parents[1]
LONG_ID = "MONDO:0000001|DOID:12345678901234567890"


def edge(relation, x_id, x_type, y_id, y_type):
    return relation, x_id, x_type, y_id, y_type


def benchmark(role_pairs=None, candidates=("DRUG_B", "DRUG_A", "DRUG_C"), target=LONG_ID):
    roles = role_pairs or (
        TherapeuticPair("DRUG_C", target, LabelState.CLEAN_INDICATION),
        TherapeuticPair("DRUG_C", "BUFFER", LabelState.CLEAN_INDICATION),
        TherapeuticPair("DRUG_A", "TRAIN_1", LabelState.CLEAN_INDICATION),
        TherapeuticPair("DRUG_B", "TRAIN_1", LabelState.CLEAN_INDICATION),
        TherapeuticPair("DRUG_A", "TRAIN_2", LabelState.CLEAN_INDICATION),
        TherapeuticPair("DRUG_C", "TRAIN_1", LabelState.CONTRAINDICATION_ONLY),
        TherapeuticPair("DRUG_C", "TRAIN_2", LabelState.OFFLABEL_ONLY),
    )
    return FrozenBenchmark(
        benchmark_id="B",
        protocol=MaskingProtocol.CANONICAL_1HOP,
        candidate_ids=tuple(candidates),
        disease_folds=((target, 0),),
        role_pairs=tuple(roles),
        quarantine=(
            QuarantineEntry(0, target, "TARGET", True),
            QuarantineEntry(0, "BUFFER", "BUFFER", True),
        ),
        fold_summary=(),
        fold_labels=(),
        graph_structure=GraphStructure(0, 0, 0),
        expected={"folds": 1},
    )


def profile_edges(target=LONG_ID):
    return [
        edge("disease_protein", target, "disease", "G_SHARED", "gene/protein"),
        edge("disease_protein", "TRAIN_1", "disease", "G_SHARED", "gene/protein"),
        edge("disease_protein", "TRAIN_2", "disease", "G_SHARED", "gene/protein"),
        edge("disease_protein", "BUFFER", "disease", "G_SHARED", "gene/protein"),
    ]


def run_fixture(*, roles=None, edges=None, candidates=("DRUG_B", "DRUG_A", "DRUG_C")):
    frozen = benchmark(roles, candidates=candidates)
    corpus = build_disease_feature_corpus(edges or profile_edges())
    prepared = prepare_e2_from_corpus(corpus, frozen)
    return frozen, prepared, score_e2_prepared(prepared, frozen)


class E2FeatureTests(unittest.TestCase):
    def test_binary_feature_construction(self):
        corpus = build_disease_feature_corpus(profile_edges())
        expected = feature_token("disease_protein", "gene/protein", "G_SHARED")
        self.assertIn((LONG_ID, expected), corpus.pairs)

    def test_duplicate_feature_handling(self):
        duplicate = profile_edges() + [profile_edges()[0], edge("disease_protein", "G_SHARED", "gene/protein", LONG_ID, "disease")]
        corpus = build_disease_feature_corpus(duplicate)
        self.assertEqual(sum(disease == LONG_ID for disease, _ in corpus.pairs), 1)

    def test_therapeutic_relations_excluded_from_profiles(self):
        base = build_disease_feature_corpus(profile_edges())
        mutated = build_disease_feature_corpus(profile_edges() + [edge("indication", LONG_ID, "disease", "DRUG_A", "drug")])
        self.assertEqual(base, mutated)

    def test_tfidf_formula(self):
        edges = [
            edge("r", "A", "disease", "S", "gene/protein"),
            edge("r", "B", "disease", "S", "gene/protein"),
            edge("r", "A", "disease", "U", "gene/protein"),
        ]
        corpus = build_disease_feature_corpus(edges)
        profiles = build_tfidf_profiles(corpus, ("A", "B"))
        by_feature = dict(zip(profiles.feature_ids, profiles.idf))
        self.assertEqual(by_feature["r|gene/protein|S"], np.float32(1.0))
        self.assertEqual(by_feature["r|gene/protein|U"], np.float32(np.log(3 / 2) + 1))

    def test_cosine_similarity(self):
        edges = [
            edge("r", "A", "disease", "S", "gene/protein"),
            edge("r", "B", "disease", "S", "gene/protein"),
            edge("r", "A", "disease", "U", "gene/protein"),
        ]
        corpus = build_disease_feature_corpus(edges)
        profiles = build_tfidf_profiles(corpus, ("A", "B"))
        similarity = (profiles.matrix[0] @ profiles.matrix[1].T).toarray()[0, 0]
        unique = np.float32(np.log(3 / 2) + 1)
        expected = np.float32(1 / np.sqrt(np.float32(1 + unique * unique)))
        self.assertAlmostEqual(float(similarity), float(expected), places=7)

    def test_zero_profile_behavior(self):
        frozen = benchmark()
        corpus = build_disease_feature_corpus([edge("r", "TRAIN_1", "disease", "X", "gene/protein")])
        run = score_e2_prepared(prepare_e2_from_corpus(corpus, frozen), frozen)
        self.assertEqual(run.statuses, (NO_PROFILE,))
        self.assertFalse(run.applicable[0])
        self.assertFalse(np.any(run.scores[0]))

    def test_no_top_k_truncation(self):
        roles = tuple(
            TherapeuticPair("DRUG_A", disease, LabelState.CLEAN_INDICATION)
            for disease in ("TRAIN_1", "TRAIN_2", "TRAIN_3")
        )
        edges = profile_edges() + [edge("disease_protein", "TRAIN_3", "disease", "G_SHARED", "gene/protein")]
        frozen, prepared, _run = run_fixture(roles=roles, edges=edges)
        allowed = [i for i, disease in enumerate(prepared.label_disease_ids) if disease not in frozen.mask(0).hidden_ids]
        self.assertEqual(prepared.similarity[0, allowed].nnz, 3)

    def test_ontology_features_are_included(self):
        corpus = build_disease_feature_corpus([edge("disease_disease", LONG_ID, "disease", "NEIGHBOR", "disease")])
        self.assertIn((LONG_ID, "disease_disease|disease|NEIGHBOR"), corpus.pairs)

    def test_long_ids_preserved(self):
        corpus = build_disease_feature_corpus(profile_edges())
        self.assertIn(LONG_ID, corpus.disease_ids)


class E2TransferAndLeakageTests(unittest.TestCase):
    def test_legal_clean_training_label_transfer(self):
        _frozen, _prepared, run = run_fixture()
        self.assertEqual(run.scores[0, 0], np.float32(0.5))
        self.assertEqual(run.scores[0, 1], np.float32(1.0))

    def test_target_labels_excluded(self):
        frozen, _prepared, run = run_fixture()
        self.assertNotIn((LONG_ID, "DRUG_C"), {(p.disease_id, p.drug_id) for p in frozen.mask(0).legal_clean_pairs})
        self.assertEqual(run.scores[0, 2], 0.0)

    def test_buffer_labels_excluded(self):
        frozen, _prepared, run = run_fixture()
        self.assertNotIn(("BUFFER", "DRUG_C"), {(p.disease_id, p.drug_id) for p in frozen.mask(0).legal_clean_pairs})
        self.assertEqual(run.scores[0, 2], 0.0)

    def test_contraindication_excluded_as_positive(self):
        _frozen, _prepared, run = run_fixture()
        self.assertEqual(run.scores[0, 2], 0.0)

    def test_offlabel_excluded_as_positive(self):
        _frozen, _prepared, run = run_fixture()
        self.assertEqual(run.scores[0, 2], 0.0)

    def test_repeated_drug_support_accumulates(self):
        _frozen, _prepared, run = run_fixture()
        self.assertGreater(run.scores[0, 1], run.scores[0, 0])

    def test_candidate_axis_preserved(self):
        candidates = ("DRUG_C", "DRUG_A", "DRUG_B")
        _frozen, _prepared, run = run_fixture(candidates=candidates)
        self.assertEqual(run.candidate_ids, candidates)

    def test_disease_axis_preserved(self):
        _frozen, _prepared, run = run_fixture()
        self.assertEqual(run.disease_ids, (LONG_ID,))

    def test_applicability_rule(self):
        _frozen, _prepared, run = run_fixture()
        self.assertEqual(run.statuses, ("OK",))
        self.assertEqual(run.applicable, (True,))

    def test_deterministic_repeated_runs(self):
        frozen = benchmark()
        prepared = prepare_e2_from_corpus(build_disease_feature_corpus(profile_edges()), frozen)
        first = score_e2_prepared(prepared, frozen)
        second = score_e2_prepared(prepared, frozen)
        self.assertTrue(np.array_equal(first.scores, second.scores))
        self.assertEqual(first.applicable, second.applicable)

    def test_fold_specific_legal_count_consumed(self):
        _frozen, _prepared, run = run_fixture()
        self.assertEqual(run.fold_legal_clean_counts, (3,))

    def test_target_label_mutation_has_no_effect(self):
        base_roles = benchmark().role_pairs
        mutated = tuple(p for p in base_roles if p.disease_id != LONG_ID) + (
            TherapeuticPair("DRUG_B", LONG_ID, LabelState.CLEAN_INDICATION),
        )
        base = run_fixture()[2]
        changed = run_fixture(roles=mutated)[2]
        self.assertTrue(np.array_equal(base.scores, changed.scores))

    def test_buffer_label_mutation_has_no_effect(self):
        base_roles = benchmark().role_pairs
        mutated = tuple(p for p in base_roles if p.disease_id != "BUFFER") + (
            TherapeuticPair("DRUG_B", "BUFFER", LabelState.CLEAN_INDICATION),
        )
        self.assertTrue(np.array_equal(run_fixture()[2].scores, run_fixture(roles=mutated)[2].scores))

    def test_legal_training_label_mutation_changes_score(self):
        base_roles = benchmark().role_pairs
        mutated = tuple(
            TherapeuticPair("DRUG_C", p.disease_id, p.role)
            if p.disease_id == "TRAIN_2" and p.role is LabelState.CLEAN_INDICATION else p
            for p in base_roles
        )
        base = run_fixture()[2].scores
        changed = run_fixture(roles=mutated)[2].scores
        self.assertFalse(np.array_equal(base, changed))
        self.assertGreater(changed[0, 2], base[0, 2])

    def test_therapeutic_edge_mutation_does_not_affect_profile(self):
        base = build_disease_feature_corpus(profile_edges())
        changed = build_disease_feature_corpus(profile_edges() + [edge("off-label use", "DRUG_A", "drug", LONG_ID, "disease")])
        self.assertEqual(base, changed)

    def test_contra_and_offlabel_mutation_has_no_effect(self):
        base_roles = benchmark().role_pairs
        mutated = tuple(p for p in base_roles if p.role is LabelState.CLEAN_INDICATION) + (
            TherapeuticPair("DRUG_B", "TRAIN_1", LabelState.CONTRAINDICATION_ONLY),
            TherapeuticPair("DRUG_A", "TRAIN_2", LabelState.OFFLABEL_ONLY),
        )
        self.assertTrue(np.array_equal(run_fixture()[2].scores, run_fixture(roles=mutated)[2].scores))


@unittest.skipUnless(os.environ.get("PRIMEKG_GATE5_REPORT"), "requires completed full-local Gate-5 run")
class FullLocalE2EquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(Path(os.environ["PRIMEKG_GATE5_REPORT"]).read_text(encoding="utf-8"))

    def test_historical_score_archive_comparison(self):
        score = self.report["score_equivalence"]
        self.assertEqual(score["shape"], [738, 7957])
        self.assertEqual(score["scores_compared"], 738 * 7957)
        self.assertEqual(score["unequal_value_count"], 0)
        self.assertEqual(score["max_absolute_difference"], 0.0)

    def test_frozen_applicability_matches_712(self):
        self.assertEqual(self.report["applicable_count"], 712)
        self.assertEqual(self.report["abstention_count"], 26)
        self.assertTrue(self.report["evaluator_equivalence"]["applicability_exact"])

    def test_gate3_evaluator_reproduces_frozen_disease_metrics(self):
        evaluation = self.report["evaluator_equivalence"]
        self.assertLessEqual(evaluation["max_absolute_disease_level_difference"], 2e-15)
        self.assertEqual(evaluation["historical_archive_gate3_status"], "PASS")

    def test_macro_recall50_reproduces_frozen_value(self):
        evaluation = self.report["evaluator_equivalence"]
        self.assertLessEqual(evaluation["macro_recall50_absolute_difference"], 2e-16)


if __name__ == "__main__":
    unittest.main()
