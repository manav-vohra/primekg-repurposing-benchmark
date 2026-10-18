"""Independent tie-block enumeration and Gate-3 evaluator regressions."""

from __future__ import annotations

import itertools
import contextlib
import io
import math
import os
import unittest
from pathlib import Path

from primekg_repurposing.evaluation import (
    ExpertScoreResult,
    TieSafeEvaluator,
    evaluator_formula_self_checks,
    expected_first_rank_and_mrr,
    hit_probability_in_tie,
    load_frozen_evaluator,
    reproduce_archive,
)

ROOT = Path(__file__).resolve().parents[1]


def evaluator_for(roles, k_values=(1, 2, 3, 5, 10)):
    candidates = tuple(f"D{i}" for i in range(1, 6))
    return TieSafeEvaluator("P1_TRACK_A_PRIMEKG_V0", "1.1_tiesafe", candidates, ("disease",), {"disease": roles}, k_values)


def result_for(scores, *, applicable=True, reason=None, candidates=None):
    return ExpertScoreResult("FIXTURE", "0", "disease", candidates or tuple(f"D{i}" for i in range(1, 6)), scores, applicable, reason)


def brute_force_metrics(scores, roles, k_values):
    """Enumerate every tie-consistent ranking, without using analytic formulas."""
    import numpy as np

    candidates = [f"D{i}" for i in range(1, 6)]
    eligible = [(drug, float(np.float32(score))) for drug, score in zip(candidates, scores) if roles.get(drug) not in {"AMBIGUOUS_INDICATION", "OFFLABEL_ONLY", "CONFLICTING_NONINDICATION"}]
    blocks = []
    for score in sorted({score for _, score in eligible}, reverse=True):
        blocks.append([drug for drug, value in eligible if value == score])
    rankings = [sum(parts, ()) for parts in itertools.product(*(itertools.permutations(block) for block in blocks))]
    clean = {drug for drug, role in roles.items() if role == "CLEAN_INDICATION"}
    contra = {drug for drug, role in roles.items() if role == "CONTRAINDICATION_ONLY"}
    values = {"MRR": [], "first_hit_rank": [], "first_contra_rank": []}
    for k in k_values:
        for prefix in ("Recall", "Hit", "Contra", "ContraRate"):
            values[f"{prefix}@{k}"] = []
    for ranking in rankings:
        first = next(i + 1 for i, drug in enumerate(ranking) if drug in clean)
        values["first_hit_rank"].append(first)
        values["MRR"].append(1 / first)
        values["first_contra_rank"].append(next((i + 1 for i, drug in enumerate(ranking) if drug in contra), math.nan))
        for k in k_values:
            top = ranking[:k]
            positive_count = sum(drug in clean for drug in top)
            contraindication_count = sum(drug in contra for drug in top)
            values[f"Recall@{k}"].append(positive_count / len(clean))
            values[f"Hit@{k}"].append(float(positive_count > 0))
            values[f"Contra@{k}"].append(contraindication_count)
            values[f"ContraRate@{k}"].append(contraindication_count / k)
    return {field: math.nan if all(math.isnan(x) for x in xs) else sum(x for x in xs if not math.isnan(x)) / sum(not math.isnan(x) for x in xs) for field, xs in values.items()}


class TieFormulaTests(unittest.TestCase):
    def assert_matches_enumeration(self, scores, roles):
        evaluator = evaluator_for(roles)
        analytic = evaluator.evaluate(result_for(scores))
        brute = brute_force_metrics(scores, roles, evaluator.k_values)
        for field, expected in brute.items():
            if math.isnan(expected):
                self.assertTrue(math.isnan(analytic[field]), field)
            else:
                self.assertAlmostEqual(analytic[field], expected, places=13, msg=field)

    def test_no_ties_ordinary_ranking(self):
        self.assert_matches_enumeration([5, 4, 3, 2, 1], {"D1": "CLEAN_INDICATION", "D3": "CLEAN_INDICATION", "D2": "CONTRAINDICATION_ONLY"})

    def test_tie_entirely_above_k(self):
        self.assert_matches_enumeration([5, 5, 3, 2, 1], {"D1": "CLEAN_INDICATION", "D3": "CLEAN_INDICATION", "D2": "CONTRAINDICATION_ONLY"})

    def test_tie_entirely_below_k(self):
        self.assert_matches_enumeration([5, 4, 3, 1, 1], {"D1": "CLEAN_INDICATION", "D4": "CLEAN_INDICATION", "D5": "CONTRAINDICATION_ONLY"})

    def test_boundary_crossing_one_positive(self):
        self.assert_matches_enumeration([5, 4, 4, 4, 1], {"D3": "CLEAN_INDICATION", "D5": "CONTRAINDICATION_ONLY"})

    def test_multiple_positives_in_same_tie(self):
        self.assert_matches_enumeration([5, 4, 4, 4, 1], {"D2": "CLEAN_INDICATION", "D3": "CLEAN_INDICATION", "D4": "CONTRAINDICATION_ONLY"})

    def test_earlier_positive_and_later_positive(self):
        self.assert_matches_enumeration([5, 4, 4, 2, 2], {"D1": "CLEAN_INDICATION", "D4": "CLEAN_INDICATION", "D3": "CONTRAINDICATION_ONLY"})

    def test_all_candidates_tied(self):
        self.assert_matches_enumeration([1] * 5, {"D1": "CLEAN_INDICATION", "D3": "CLEAN_INDICATION", "D4": "CONTRAINDICATION_ONLY"})

    def test_all_zero_applicable_is_not_abstention(self):
        roles = {"D1": "CLEAN_INDICATION"}
        metrics = evaluator_for(roles).evaluate(result_for([0] * 5))
        self.assertAlmostEqual(metrics["Recall@1"], 0.2)
        self.assertAlmostEqual(metrics["Hit@1"], 0.2)
        self.assert_matches_enumeration([0] * 5, roles)

    def test_hit_is_probability_not_expected_count_boolean(self):
        self.assertAlmostEqual(hit_probability_in_tie(4, 2, 2), 5 / 6)
        self.assertNotEqual(hit_probability_in_tie(4, 2, 2), 1.0)

    def test_first_rank_and_mrr_analytic(self):
        rank, mrr = expected_first_rank_and_mrr(4, 1, 2)
        self.assertEqual(rank, 4.5)
        self.assertAlmostEqual(mrr, sum(1 / r for r in (3, 4, 5, 6)) / 4)

    def test_ignored_roles_removed_before_rank(self):
        roles = {"D1": "OFFLABEL_ONLY", "D2": "AMBIGUOUS_INDICATION", "D3": "CONFLICTING_NONINDICATION", "D4": "CLEAN_INDICATION", "D5": "CONTRAINDICATION_ONLY"}
        metrics = evaluator_for(roles).evaluate(result_for([9, 8, 7, 6, 5]))
        self.assertEqual(metrics["first_hit_rank"], 1.0)
        self.assertEqual(metrics["Recall@1"], 1.0)
        self.assert_matches_enumeration([9, 8, 7, 6, 5], roles)

    def test_contraindication_separate_from_clean(self):
        roles = {"D1": "CONTRAINDICATION_ONLY", "D2": "CLEAN_INDICATION"}
        metrics = evaluator_for(roles).evaluate(result_for([5, 4, 3, 2, 1]))
        self.assertEqual(metrics["Recall@1"], 0.0)
        self.assertEqual(metrics["Contra@1"], 1.0)
        self.assertEqual(metrics["first_contra_rank"], 1.0)
        self.assert_matches_enumeration([5, 4, 3, 2, 1], roles)

    def test_unobserved_is_unlabeled_not_negative(self):
        roles = {"D2": "CLEAN_INDICATION"}
        metrics = evaluator_for(roles).evaluate(result_for([5, 4, 3, 2, 1]))
        self.assertEqual(metrics["first_hit_rank"], 2.0)
        self.assertTrue(math.isnan(metrics["first_contra_rank"]))
        self.assert_matches_enumeration([5, 4, 3, 2, 1], roles)

    def test_k_larger_than_small_fixture_saturates_count(self):
        metrics = evaluator_for({"D3": "CLEAN_INDICATION", "D5": "CONTRAINDICATION_ONLY"}).evaluate(result_for([5, 4, 3, 2, 1]))
        self.assertEqual(metrics["Recall@10"], 1.0)
        self.assertEqual(metrics["Hit@10"], 1.0)
        self.assertEqual(metrics["Contra@10"], 1.0)
        self.assertEqual(metrics["ContraRate@10"], 0.1)

    def test_exact_float32_tie_and_infinities(self):
        self.assert_matches_enumeration([math.inf, math.inf, 0, -math.inf, -math.inf], {"D1": "CLEAN_INDICATION", "D5": "CONTRAINDICATION_ONLY"})

    def test_formula_self_checks_pass(self):
        self.assertEqual(evaluator_formula_self_checks()["status"], "PASS")


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.evaluator = evaluator_for({"D1": "CLEAN_INDICATION"})

    def test_explicit_abstention_zero_and_nan_ranks(self):
        metrics = self.evaluator.evaluate(result_for([0] * 5, applicable=False, reason="NO_CONTEXT"))
        self.assertEqual(metrics["Recall@1"], 0.0)
        self.assertEqual(metrics["MRR"], 0.0)
        self.assertTrue(math.isnan(metrics["first_hit_rank"]))

    def test_abstention_requires_reason(self):
        with self.assertRaises(ValueError):
            self.evaluator.evaluate(result_for([0] * 5, applicable=False))

    def test_shuffled_candidate_axis_fails(self):
        with self.assertRaisesRegex(ValueError, "axis"):
            self.evaluator.evaluate(result_for([5, 4, 3, 2, 1], candidates=("D2", "D1", "D3", "D4", "D5")))

    def test_duplicate_candidate_id_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.evaluator.evaluate(result_for([5, 4, 3, 2, 1], candidates=("D1", "D1", "D3", "D4", "D5")))

    def test_wrong_disease_fails(self):
        result = ExpertScoreResult("F", "0", "other", self.evaluator.candidate_ids, [1] * 5, True)
        with self.assertRaisesRegex(ValueError, "disease"):
            self.evaluator.evaluate(result)

    def test_wrong_evaluator_version_fails(self):
        with self.assertRaisesRegex(ValueError, "version"):
            self.evaluator.evaluate(result_for([1] * 5), evaluator_version="1.0")

    def test_wrong_benchmark_id_fails(self):
        with self.assertRaisesRegex(ValueError, "benchmark"):
            self.evaluator.evaluate(result_for([1] * 5), benchmark_id="OTHER")

    def test_malformed_score_vector_fails(self):
        with self.assertRaisesRegex(ValueError, "length"):
            self.evaluator.evaluate(result_for([1] * 4))

    def test_nan_fails_loudly(self):
        with self.assertRaisesRegex(ValueError, "NaN"):
            self.evaluator.evaluate(result_for([1, math.nan, 3, 2, 1]))

    def test_no_clean_truth_fails_for_applicable(self):
        evaluator = evaluator_for({"D1": "CONTRAINDICATION_ONLY"})
        with self.assertRaisesRegex(ValueError, "no evaluable CLEAN"):
            evaluator.evaluate(result_for([1] * 5))

    def test_constructor_rejects_duplicate_canonical_axis(self):
        with self.assertRaisesRegex(ValueError, "duplicated"):
            TieSafeEvaluator("P1_TRACK_A_PRIMEKG_V0", "1.1_tiesafe", ("D1", "D1"), ("disease",), {}, (1,))


class FrozenContractTests(unittest.TestCase):
    def test_frozen_config_policy_and_axes_load_through_registry(self):
        evaluator, contract = load_frozen_evaluator(ROOT / "artifacts/registry.json", ROOT / "artifacts/frozen")
        self.assertEqual(evaluator.version, "1.1_tiesafe")
        self.assertEqual(len(evaluator.candidate_ids), 7957)
        self.assertEqual(len(evaluator.disease_ids), 738)
        self.assertEqual(evaluator.k_values, (10, 50, 100))
        self.assertFalse(contract["configuration"]["important_semantics"]["unobserved_are_true_negatives"])
        self.assertEqual(contract["metric_policy"]["primary_positive"], "CLEAN_INDICATION")

    def test_cli_without_raw_scores_cannot_pass(self):
        from primekg_repurposing.cli import main

        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["reproduce-evaluator", "--data-root", "missing-data-root"])
        self.assertNotEqual(exit_code, 0)


@unittest.skipUnless(os.environ.get("PRIMEKG_GATE3_E3_SEED0"), "requires real registry-indexed score archive; never ordinary CI")
class FullLocalScoreEquivalenceTests(unittest.TestCase):
    def test_e3_seed0_score_to_matrix_and_macro_exact(self):
        evaluator, _ = load_frozen_evaluator(ROOT / "artifacts/registry.json", ROOT / "artifacts/frozen")
        report = reproduce_archive("external/p1_e3_complex_seed0_scores.npz", Path(os.environ["PRIMEKG_GATE3_E3_SEED0"]), ROOT / "artifacts/frozen", ROOT / "artifacts/registry.json", evaluator)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["max_absolute_difference"], 0.0)
        self.assertEqual(report["macro_recall50_absolute_difference"], 0.0)
        self.assertEqual(report["disease_rows"], 738)


if __name__ == "__main__":
    unittest.main()
