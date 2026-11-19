"""Supported cost calculations and explicitly labeled historical evidence replay."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from .analysis import EXPERTS, METRICS, EVIDENCE_CLASSES
from .provenance import load_registry, sha256_file

GATE_A_SOURCE = {'notebook_cell_index': 99, 'source_sha256': '65139f2c215d8aa4beaeafd203f6b3e6882bbc31707956331be9a20164e594bb'}


def read_reference(registry, frozen, artifact_id):
    item = next(a for a in load_registry(registry)['artifacts'] if a['artifact_id'] == artifact_id)
    path = frozen/item['logical_path']
    if sha256_file(path) != item['expected_sha256']:
        raise ValueError('frozen downstream evidence hash mismatch')
    return json.loads(path.read_text()), {'artifact_id':artifact_id,'sha256':item['expected_sha256']}


def choose_actions(utility, costs, valid, lam):
    utility, costs, valid = np.asarray(utility), np.asarray(costs), np.asarray(valid, dtype=bool)
    if utility.ndim != 2 or utility.shape != costs.shape or valid.shape != utility.shape or not valid.any(axis=1).all():
        raise ValueError('invalid costed action matrices')
    if not np.isfinite(utility).all() or not np.isfinite(costs).all() or (costs < 0).any() or not np.isfinite(lam) or lam < 0:
        raise ValueError('invalid costed action values')
    net = np.where(valid, utility-lam*costs, -np.inf)
    tied = valid & np.isclose(net, net.max(axis=1,keepdims=True), rtol=0, atol=1e-12)
    low_cost = np.where(tied, costs, np.inf).min(axis=1,keepdims=True)
    candidates = tied & np.isclose(costs,low_cost,rtol=0,atol=1e-15)
    return candidates.argmax(axis=1)  # fixed action order: stop, E1, E3, E4


def gate_a(portfolio, registry, frozen):
    timing,timing_input=read_reference(registry,frozen,'recovered_contracts/p1_p15_cost_timing_audit_v1.json')
    constitution,constitution_input=read_reference(registry,frozen,'recovered_contracts/p1_p15_gateA_constitution_v1.json')
    r=portfolio.values[:,:,METRICS.index('Recall@50')]
    app=portfolio.applicable
    cost=np.array([timing['expert_median_ms'][e]/1000 for e in EXPERTS])
    default_cost=app[:,1]*cost[1]
    order=(1,0,2,3)
    utility=r[:,order]
    costs=np.column_stack([default_cost,*(default_cost+cost[j] for j in (0,2,3))])
    valid=np.column_stack([np.ones(len(r),dtype=bool),app[:,(0,2,3)]])
    grid=constitution['lambda_grid']
    lambdas=np.concatenate([[0.],np.logspace(np.log10(grid['positive_min']),np.log10(grid['positive_max']),grid['positive_points'])])
    points=[]
    rows=np.arange(len(r))
    for lam in lambdas:
        action=choose_actions(utility,costs,valid,float(lam))
        points.append({'lambda':float(lam),'quality':float(utility[rows,action].mean()),'cost_ms':float(costs[rows,action].mean()*1000),'escalations':int((action!=0).sum())})
    baseline=float(default_cost.mean()*1000)
    budgets=[]
    for multiple in (1.,1.25,1.5,2.):
        eligible=[p for p in points if p['cost_ms']<=baseline*multiple+1e-12]
        best=min(eligible,key=lambda p:(-p['quality'],p['cost_ms'])) if eligible else None
        budgets.append({'multiple_E2':multiple,'budget_ms':baseline*multiple,'best':best})
    return {'evidence_class':2,'evidence_label':EVIDENCE_CLASSES[2],'family':'ORIGINAL_CANONICAL','population':len(r),'default':'E2',
            'oracle_only_not_deployable':True,'new_timing':False,'baseline_effective_E2_ms':baseline,'lambda0':points[0],'budgets':budgets,
            'costs':timing,'contract':{'source':GATE_A_SOURCE,'net_tie_atol':1e-12,'cost_tie_atol':1e-15,'action_order':['STOP_E2','E1','E3','E4']},'inputs':[timing_input,constitution_input]}


def downstream_evidence(registry, frozen):
    """Read an allowlist of aggregate summaries; never load split membership/outcomes."""
    result={}
    for label,artifact_id in [
        ('static_routing','recovered_contracts/p1_static_routing_closure.json'),
        ('gate_b','recovered_contracts/p1_p15_gateB_development_gate_v1.json'),
        ('timing','recovered_contracts/p1_p15_cost_timing_audit_v1.json')]:
        value,source=read_reference(registry,frozen,artifact_id)
        result[label]={'evidence_class':3,'evidence_label':EVIDENCE_CLASSES[3],'data':value,'input':source,'rerun':False,
                       'limitation':'Historical summary replay; original fitting, timing and prediction input chain is not rerun.'}
    return result


def compare_gate_a(result, registry, frozen):
    target,_=read_reference(registry,frozen,'recovered_contracts/p1_p15_gateA_summary_v1.json')
    budget={x['multiple_E2']:x for x in result['budgets']}
    expected=[('effective_E2_ms',result['baseline_effective_E2_ms'],target['fixed_E2_mean_warm_cost_ms']),
              ('lambda0_quality',result['lambda0']['quality'],target['VBS_R50']),
              ('lambda0_cost_ms',result['lambda0']['cost_ms'],target['cheapest_lambda0_VBS_cascade_cost_ms']),
              ('budget1.25_quality',budget[1.25]['best']['quality'],target['SBS_R50']+target['best_supported_gain_within_1_25x_E2_cost']),
              ('budget1.5_quality',budget[1.5]['best']['quality'],target['VBS_R50'])]
    checks=[{'name':name,'actual':actual,'expected':value,'max_absolute_difference':abs(actual-value),'pass':abs(actual-value)<=1e-12} for name,actual,value in expected]
    return {'status':'PASS' if all(x['pass'] for x in checks) else 'FAIL','checks':checks}
