import copy
from pathlib import Path
import numpy as np
import pytest
from primekg_repurposing.analysis import METRICS, aggregate_seed_rows, summarize_metric, bootstrap_interval, load_portfolio, compute_core, compare_core

ROOT=Path(__file__).resolve().parents[1]


def rows(seed, values):
    return [dict(disease_id=str(i), seed=str(seed), status='OK', applicable='True', primary_utility=str(v), **{m:str(v) for m in METRICS}) for i,v in enumerate(values)]


def test_seed_mean_precedes_oracle_not_seedwise_best():
    v,_,_=aggregate_seed_rows({s:rows(s,x) for s,x in enumerate([[1,0],[0,1],[0,0]])},(0,1,2),('0','1'))
    utility=np.column_stack([np.zeros(2),np.full(2,.5),v[:,1],np.zeros(2)])
    result,_,_=summarize_metric(utility)
    assert result['VBS']==.5 and result['SBS_expert']=='E2'


def test_historical_relative_tolerance_and_fixed_zero_ties():
    result,_,labels=summarize_metric([[0,.5,.500004,0],[0,0,0,0],[1,0,0,0]])
    assert labels.tolist()==['TIE','TIE','E1']
    assert result['winner_counts']['TIE']==2


def test_missing_seed_or_axis_corruption_rejected():
    with pytest.raises(ValueError,match='seed'):
        aggregate_seed_rows({0:rows(0,[.2,.3])},(0,1,2),('0','1'))
    with pytest.raises(ValueError,match='axis'):
        aggregate_seed_rows({0:rows(0,[.2,.3])[::-1]},(0,),('0','1'))


def test_explicit_abstention_zero_and_applicable_zero_distinct():
    data=rows(0,[0,0]);data[0].update(status='ABSTAIN_FIXTURE',applicable='False')
    _,app,_=aggregate_seed_rows({0:data},(0,),('0','1'))
    assert app.tolist()==[False,True]
    data[0]['MRR']='.1'
    with pytest.raises(ValueError,match='abstention'):
        aggregate_seed_rows({0:data},(0,),('0','1'))


def test_conflicting_seed_status_rejected():
    d={0:rows(0,[0]),1:rows(1,[0])};d[1][0].update(status='ABSTAIN_FIXTURE',applicable='False')
    with pytest.raises(ValueError,match='status mismatch'):
        aggregate_seed_rows(d,(0,1),('0',))


def test_paired_bootstrap_deterministic_and_bounded():
    assert bootstrap_interval([.25,.25],seed=12,reps=30)==[.25,.25]
    assert bootstrap_interval([0,1,.5],seed=1,reps=100,batch=10)==bootstrap_interval([0,1,.5],seed=1,reps=100,batch=100)
    with pytest.raises(ValueError):bootstrap_interval([],seed=1)


def test_verified_real_core_matches_independent_frozen_targets():
    p=load_portfolio(ROOT/'artifacts/registry.json',ROOT/'artifacts/frozen')
    r,_,_=compute_core(p)
    equivalence=compare_core(p,r,ROOT/'artifacts/frozen')
    assert equivalence['status']=='PASS',equivalence
    assert r['evidence_class']==2
    assert r['all_experts_unavailable']==2
    assert r['metrics']['Recall@50']['winner_counts']=={'E1':39,'E2':442,'E3':38,'E4':56,'TIE':163}
