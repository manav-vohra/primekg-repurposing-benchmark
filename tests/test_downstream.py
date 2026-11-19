from pathlib import Path
import numpy as np
import pytest
from primekg_repurposing.analysis import load_portfolio
from primekg_repurposing.downstream import choose_actions, gate_a, compare_gate_a, downstream_evidence

ROOT=Path(__file__).resolve().parents[1]


def test_net_then_cost_then_frozen_order():
    u=np.array([[.5,.5,.5],[.5,.5001,.8]])
    c=np.array([[.2,.1,.1],[.2,.1,.01]])
    valid=np.array([[True,True,True],[True,True,False]])
    assert choose_actions(u,c,valid,0).tolist()==[1,1]
    assert choose_actions([[.1,.2]],[[0,.1]],[[True,True]],2).tolist()==[0]


def test_invalid_actions_never_selected():
    assert choose_actions([[0,1]],[[0,0]],[[True,False]],0).tolist()==[0]
    with pytest.raises(ValueError):choose_actions([[0,1]],[[0,0]],[[False,False]],0)
    with pytest.raises(ValueError):choose_actions([[0,1]],[[0,-1]],[[True,True]],0)


def test_gate_a_recomputes_published_cost_bounds():
    registry=ROOT/'artifacts/registry.json';frozen=ROOT/'artifacts/frozen'
    portfolio=load_portfolio(registry,frozen)
    result=gate_a(portfolio,registry,frozen)
    assert compare_gate_a(result,registry,frozen)['status']=='PASS'
    assert result['evidence_class']==2 and result['oracle_only_not_deployable']
    assert result['population']==738 and not result['new_timing']


def test_gate_b_replay_never_becomes_new_fit():
    result=downstream_evidence(ROOT/'artifacts/registry.json',ROOT/'artifacts/frozen')
    assert all(x['evidence_class']==3 and not x['rerun'] for x in result.values())
    assert not result['gate_b']['data']['formal_pass']
    assert result['gate_b']['data']['switch_count']==0
    assert not result['gate_b']['data']['META_TEST_opened']
