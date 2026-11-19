"""Corruption checks for the read-only matrix reconciliation audit."""
import runpy
from pathlib import Path

import pytest

from primekg_repurposing.evaluation import TieSafeEvaluator

check_rows = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/gate6c_audit.py'))['check_rows']
EXPERT = 'E1_WEIGHTED_GENE_COSINE'


@pytest.fixture
def contract():
    evaluator = TieSafeEvaluator('fixture', '1.1_tiesafe', ('drug1', 'drug2'), ('disease',), {'disease': {'drug1': 'CLEAN_INDICATION'}}, (10, 50, 100))
    row = dict(benchmark_id='fixture', evaluator_version='1.1_tiesafe', expert_id=EXPERT,
               expert_version='1.0', seed='0', primary_utility_name='Recall@50', disease_id='disease',
               fold='0', applicable='True', status='OK', primary_utility='0', MRR='0',
               first_hit_rank='2', first_contra_rank='', n_clean_positives='1',
               n_ignored_candidates='0', n_contraindications='0', n_scored_candidates='2')
    row.update({f'{metric}@{k}': '0' for metric in ('Recall', 'Hit', 'Contra', 'ContraRate') for k in (10, 50, 100)})
    return evaluator, row


def run(contract, **changes):
    evaluator, row = contract
    return check_rows([{**row, **changes}], evaluator, {'disease': 0}, EXPERT, 0, {0: 1})


def test_zero_utility_does_not_imply_abstention(contract):
    assert run(contract) == {'OK': 1}


@pytest.mark.parametrize('column,value,message', [
    ('disease_id', 'other', 'disease axis'),
    ('seed', '2', 'identity'),
    ('expert_id', 'other', 'identity'),
    ('fold', '1', 'fold mismatch'),
    ('applicable', 'False', 'contradiction'),
    ('n_scored_candidates', '1', 'n_scored_candidates'),
    ('Recall@50', 'nan', 'finite unit interval'),
])
def test_corrupt_matrix_contract_is_rejected(contract, column, value, message):
    with pytest.raises(ValueError, match=message):
        run(contract, **{column: value})


def test_abstention_rejects_hidden_utility_and_rank(contract):
    abstain = dict(applicable='False', status='ABSTAIN_FIXTURE', first_hit_rank='', first_contra_rank='')
    assert run(contract, **abstain) == {'ABSTAIN_FIXTURE': 1}
    with pytest.raises(ValueError, match='nonzero metric'):
        run(contract, **abstain, MRR='0.5')
    with pytest.raises(ValueError, match='first-event rank'):
        run(contract, **{**abstain, 'first_hit_rank': '2'})


def test_duplicate_disease_rows_are_rejected(contract):
    evaluator, row = contract
    with pytest.raises(ValueError, match='disease axis'):
        check_rows([row, row], evaluator, {'disease': 0}, EXPERT, 0, {0: 1})
