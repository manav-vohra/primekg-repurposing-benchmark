"""CPU historical-result reductions; frozen metric inputs are never model scores."""
from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .evaluation import load_frozen_evaluator
from .provenance import load_registry, sha256_file

EXPERTS = ('E1', 'E2', 'E3', 'E4')
METRICS = ('Recall@10', 'Recall@50', 'Recall@100', 'Hit@10', 'Hit@50', 'Hit@100', 'MRR')
EVIDENCE_CLASSES = {
    1: 'Independently recomputed',
    2: 'Reproduced from verified frozen outputs',
    3: 'Historical evidence only',
    4: 'Not currently verifiable',
}
# Historical producer explicitly sets atol, retaining NumPy's default rtol.
# This is utility-level winner labeling, distinct from exact-score evaluator ties.
WINNER_RTOL, WINNER_ATOL = 1e-5, 1e-12
CONTRACT = {
    'notebook_sha256': '704d8ea1cef1dae7cdd058462e73f89eac60355d0f4e6b1b0d41500560b2a200',
    'winner_source': {'cell_index': 44, 'source_sha256': '46975170f3751cca81db631080469b277ddbb22d85de2d62439bbb1129cb3d3f'},
    'cross_metric_source': {'cell_index': 47, 'source_sha256': 'e55a329f70bdef59e3b72f7c503a016a8c7fc8cd6afa296c1559c7e6b307e029'},
    'bootstrap_source': {'cell_index': 113, 'source_sha256': 'b6f539a2b44f30abdceaf8ea3b870dae3a2f4d3d7458f4aa4c78c801ccb73d38'},
    'bootstrap': {'generator': 'PCG64 (historical default_rng)', 'seed': 68020260905, 'subset_seed': 68020260906, 'reps': 10000, 'batch': 500, 'quantiles': [0.025, 0.975], 'method': 'linear'},
    'winner': {'rtol': WINNER_RTOL, 'atol': WINNER_ATOL},
    'seed_sd': {'paper': 'population ddof=0', 'historical_stability_summary': 'sample ddof=1'},
}


@dataclass
class Portfolio:
    disease_ids: tuple[str, ...]
    values: np.ndarray  # disease x expert x metric; seed metrics averaged first
    applicable: np.ndarray  # disease x expert, explicit expert status
    seed_macros: dict[str, np.ndarray]
    provenance: list[dict]


def aggregate_seed_rows(seed_rows, expected_seeds, disease_ids):
    if set(seed_rows) != set(expected_seeds):
        raise ValueError('missing or unexpected expert seed')
    values, signatures = [], []
    for seed in expected_seeds:
        rows = seed_rows[seed]
        if tuple(r['disease_id'] for r in rows) != tuple(disease_ids):
            raise ValueError('disease axis identity/order mismatch')
        if any(r['seed'] != str(seed) for r in rows):
            raise ValueError('seed metadata mismatch')
        signature = [(r['status'], r['applicable']) for r in rows]
        for status, applicable in signature:
            if applicable not in ('True', 'False') or (status == 'OK') != (applicable == 'True'):
                raise ValueError('contradictory applicability')
            if applicable == 'False' and not status.startswith('ABSTAIN_'):
                raise ValueError('abstention reason missing')
        matrix = np.array([[float(r[m]) for m in METRICS] for r in rows], dtype=np.float64)
        if matrix.shape != (len(disease_ids), len(METRICS)) or not np.isfinite(matrix).all() or ((matrix < 0) | (matrix > 1)).any():
            raise ValueError('invalid disease metric')
        unavailable = np.array([r['applicable'] == 'False' for r in rows])
        if np.any(matrix[unavailable] != 0):
            raise ValueError('abstention must retain zero utility')
        if any(float(r['primary_utility']) != float(r['Recall@50']) for r in rows):
            raise ValueError('primary utility mismatch')
        values.append(matrix); signatures.append(signature)
    if any(s != signatures[0] for s in signatures[1:]):
        raise ValueError('seed applicability/status mismatch')
    stacked = np.stack(values)
    return stacked.mean(axis=0), np.array([a == 'True' for _, a in signatures[0]]), stacked.mean(axis=1)


def load_portfolio(registry: Path, frozen: Path) -> Portfolio:
    evaluator, _ = load_frozen_evaluator(registry, frozen)  # existing integrity/semantics boundary
    records = load_registry(registry)['artifacts']
    values, applicability, macros, provenance = [], [], {}, []
    for expert in EXPERTS:
        items = [a for a in records if a['artifact_id'].startswith(f'reference_results/p1_{expert.lower()}_') and 'expert_matrix' in a['artifact_id']]
        expected = (0,) if expert in ('E1', 'E2') else (0, 1, 2)
        if len(items) != len(expected):
            raise ValueError('wrong matrix/seed count')
        seed_rows = {}
        for item in items:
            path = frozen / item['logical_path']
            digest = sha256_file(path)
            if digest != item['expected_sha256']:
                raise ValueError('matrix hash mismatch')
            with path.open(newline='', encoding='utf-8-sig') as handle:
                rows = list(csv.DictReader(handle))
            seed = int(item['metadata_equals']['seed'])
            if seed in seed_rows:
                raise ValueError('duplicate seed matrix')
            for row in rows:
                if any(row.get(k) != str(v) for k, v in item['metadata_equals'].items()):
                    raise ValueError('matrix identity mismatch')
            seed_rows[seed] = rows
            provenance.append({'artifact_id': item['artifact_id'], 'sha256': digest, 'seed': seed})
        v, app, per_seed = aggregate_seed_rows(seed_rows, expected, evaluator.disease_ids)
        values.append(v); applicability.append(app); macros[expert] = per_seed
    return Portfolio(evaluator.disease_ids, np.stack(values, axis=1), np.stack(applicability, axis=1), macros, provenance)


def summarize_metric(values):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 4 or not len(values) or not np.isfinite(values).all():
        raise ValueError('expected finite disease x four-expert utility matrix')
    means = values.mean(axis=0)
    best = values.max(axis=1)
    mask = np.isclose(values, best[:, None], rtol=WINNER_RTOL, atol=WINNER_ATOL)
    labels = np.array(['TIE' if row.sum() != 1 else EXPERTS[int(row.argmax())] for row in mask])
    sbs_index = int(means.argmax())
    return {'expert_means': dict(zip(EXPERTS, means.tolist())), 'SBS_expert': EXPERTS[sbs_index], 'SBS': float(means[sbs_index]), 'VBS': float(best.mean()), 'gap': float(best.mean()-means[sbs_index]), 'winner_counts': {e: int(np.sum(labels == e)) for e in (*EXPERTS, 'TIE')}}, best, labels


def bootstrap_interval(values, *, seed, reps=10000, batch=500):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or reps < 1 or batch < 1:
        raise ValueError('invalid paired bootstrap input')
    rng = np.random.Generator(np.random.PCG64(seed))
    out = np.empty(reps, dtype=np.float64)
    for start in range(0, reps, batch):
        count = min(batch, reps-start)
        idx = rng.integers(0, len(values), size=(count, len(values)))
        out[start:start+count] = values[idx].mean(axis=1)
    return np.quantile(out, [0.025, 0.975], method='linear').tolist()


def compute_core(portfolio: Portfolio):
    metrics = {name: summarize_metric(portfolio.values[:, :, i])[0] for i, name in enumerate(METRICS)}
    summary, vbs, winners = summarize_metric(portfolio.values[:, :, METRICS.index('Recall@50')])
    e2 = portfolio.values[:, 1, METRICS.index('Recall@50')]
    regret = vbs-e2
    e2_app = portfolio.applicable[:, 1]
    return {'evidence_class': 2, 'evidence_label': EVIDENCE_CLASSES[2], 'family': 'ORIGINAL_CANONICAL', 'population': len(e2), 'metrics': metrics,
            'applicability': dict(zip(EXPERTS, portfolio.applicable.sum(axis=0).tolist())), 'all_experts_unavailable': int((~portfolio.applicable.any(axis=1)).sum()),
            'seed_macros': {e: {name: values[:, i].tolist() for i, name in enumerate(METRICS)} for e, values in portfolio.seed_macros.items()},
            'seed_sd': {e: {'population': float(v[:, 1].std(ddof=0)), 'sample': float(v[:, 1].std(ddof=1)) if len(v)>1 else None} for e,v in portfolio.seed_macros.items()},
            'E2_applicable_gap': float(regret[e2_app].mean()), 'E2_applicable_share_full_gap': float(regret[e2_app].sum()/regret.sum()),
            'paired_bootstrap': {'evidence_class': 2, 'reps': 10000, 'full_738_CI': bootstrap_interval(regret, seed=68020260905), 'E2_applicable_712_CI': bootstrap_interval(regret[e2_app], seed=68020260906)},
            'contract': CONTRACT, 'inputs': portfolio.provenance}, vbs, winners


def compare_core(portfolio, report, frozen):
    """Independent frozen targets are consumed only after all reductions finish."""
    import json
    expected = json.loads((frozen/'audits/p1_oracle_gap_uncertainty_v1.json').read_text())
    checks = []
    def check(name, actual, target, tolerance=1e-12):
        if isinstance(target, (dict, str)):
            ok = actual == target; delta = None
        else:
            delta = float(np.max(np.abs(np.asarray(actual)-np.asarray(target))))
            ok = delta <= tolerance
        checks.append({'name': name, 'pass': bool(ok), 'max_absolute_difference': delta, 'tolerance': tolerance, 'actual': actual, 'expected': target})
    main = report['metrics']['Recall@50']
    for name, key in [('SBS','SBS_R50'),('VBS','VBS_R50'),('gap','oracle_gap'),('SBS_expert','SBS'),('winner_counts','winner_counts')]:
        check(name, main[name], expected[key])
    check('applicability', report['applicability'], expected['applicability_counts'])
    check('all_experts_unavailable',report['all_experts_unavailable'],expected['no_applicable_expert_n'])
    for name in ('E2_applicable_gap','E2_applicable_share_full_gap'):
        check(name,report[name],expected[name])
    for name in ('full_738_CI','E2_applicable_712_CI'):
        check(name,report['paired_bootstrap'][name],expected['paired_bootstrap'][name])
    with (frozen/'reference_results/p1_e1_e2_e3_e4_expected_oracle.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    if tuple(r['disease_id'] for r in rows) != portfolio.disease_ids:
        raise ValueError('comparison oracle disease axis mismatch')
    for j,e in enumerate(EXPERTS):
        check(e+'_disease_expected_utility',portfolio.values[:,j,METRICS.index('Recall@50')].tolist(),[float(r[e+'_expected_R50']) for r in rows])
    return {'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL', 'checks':checks}
