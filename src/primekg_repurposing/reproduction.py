"""One-command offline historical-result reproduction and labeled paper exports."""
from __future__ import annotations
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import numpy as np

from .analysis import EXPERTS, METRICS, EVIDENCE_CLASSES, load_portfolio, compute_core, compare_core
from .benchmark import load_frozen_benchmark
from .provenance import validate, sha256_file
from .downstream import gate_a, downstream_evidence, compare_gate_a

PAPER_MANIFEST_SHA256 = '6f68b78072805b62e95e1bb1ecf5bf8739a028688a203c032eafe6df6493987e'


def output_directory(root, output):
    root, output = root.resolve(), output.resolve()
    protected = [root/x for x in ('artifacts','src','outputs','docs','tests','.git')]
    if output == root or root.is_relative_to(output) or any(output.is_relative_to(p) or p.is_relative_to(output) for p in protected):
        raise ValueError('output directory overlaps repository inputs or references; use work/reproduction')
    output.mkdir(parents=True,exist_ok=True)
    return output


def write_json(path, value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def write_table(output, name, rows, *, decimals=6, markdown=True):
    if not rows:
        raise ValueError('empty supported table')
    columns=list(rows[0])
    def display(value):
        return (repr(value) if decimals is None else f'{value:.{decimals}f}') if isinstance(value,float) else '' if value is None else str(value)
    with (output/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        writer.writerows({k:display(v) for k,v in row.items()} for row in rows)
    if markdown:
        (output/(name+'.md')).write_text('| '+' | '.join(columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+''.join('| '+' | '.join(display(row[c]).replace('|','/') for c in columns)+' |\n' for row in rows),encoding='utf-8')


def paper_exports(output, core, cost, evidence, manifest, benchmark):
    """Computed results and historical snapshots have explicit per-row classes."""
    metrics={r['metric_id']:r for r in manifest['paper_metrics']}
    rows=[]
    r50=core['metrics']['Recall@50']
    for expert in EXPERTS:
        rows.append({'expert':expert,'applicable':core['applicability'][expert],'Recall@50':r50['expert_means'][expert],
                     'seed_SD_population':core['seed_sd'][expert]['population'] if expert in ('E3','E4') else None,'evidence_class':2,'family':'ORIGINAL_CANONICAL'})
    for label,key in [('SBS','SBS'),('VBS','VBS'),('Oracle gap','gap')]:
        rows.append({'expert':label,'applicable':None,'Recall@50':r50[key],'seed_SD_population':None,'evidence_class':2,'family':'ORIGINAL_CANONICAL'})
    write_table(output,'table1',rows)
    budgets={x['multiple_E2']:x for x in cost['budgets']}
    b=evidence['gate_b']['data'];s=evidence['static_routing']['data'];tim=evidence['timing']['data']
    write_table(output,'table2',[
        {'stage':'SBS','population':738,'outcome':r50['SBS'],'cost':'1.00x effective E2','evidence_class':2},
        {'stage':'VBS','population':738,'outcome':r50['VBS'],'cost':'oracle bound','evidence_class':2},
        {'stage':'Static_v2','population':738,'outcome':s['feature_v2']['switches'],'cost':'not re-estimated; switches','evidence_class':3},
        {'stage':'GateA','population':738,'outcome':budgets[1.25]['best']['quality'],'cost':'<=1.25x effective E2','evidence_class':2},
        {'stage':'GateB_S0','population':b['n'],'outcome':b['switch_count'],'cost':f"{tim['gateB']['S0_multiple_E2']:.3f}x per-invocation E2; switches",'evidence_class':3},
        {'stage':'GateB_S1','population':b['n'],'outcome':'over budget; not fit','cost':f"{tim['gateB']['S1_multiple_E2']:.3f}x per-invocation E2",'evidence_class':3},
    ])
    write_table(output,'table3',[
        {'protocol':protocol,**{f'F{i+1}':len(benchmark.mask(i).legal_clean_pairs) if protocol=='CANONICAL_1HOP' else None for i in range(8)},'evidence_class':1 if protocol=='CANONICAL_1HOP' else 4,'note':'recomputed legal-label mask' if protocol=='CANONICAL_1HOP' else 'not currently verifiable; no speculative protocol implementation'}
        for protocol in ('TARGET_ONLY','CANONICAL_1HOP','STRICT_2HOP')])
    t4=[]
    for row in next(t for t in manifest['paper_tables'] if t['table_id']=='T4')['rows']:
        protocol=row['protocol']
        t4.append({'protocol':protocol,**{col:metrics[f'T4.{protocol}.{col}']['observed_evidence_value'] for col in row if col!='protocol'},'evidence_class':3,'family':'PAIRED_PROTOCOL_COMPARABLE'})
    write_table(output,'table4_historical',t4)
    write_table(output,'table5',[{'metric':name,'SBS_expert':r['SBS_expert'],'SBS':r['SBS'],'VBS':r['VBS'],'Gap':r['gap'],'evidence_class':2,'family':'ORIGINAL_CANONICAL'} for name,r in core['metrics'].items()])
    # Figure1 is a historical paired-family visualization, not original-family winners.
    os.environ.setdefault('MPLCONFIGDIR', str(output/'.matplotlib'))
    os.environ.setdefault('XDG_CACHE_HOME', str(output/'.cache'))
    Path(os.environ['XDG_CACHE_HOME']).mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,3.8))
    figure=manifest['paper_figures'][0]
    counts=np.array([[metrics[f'F1.{row["protocol"]}.{e}']['observed_evidence_value'] for e in (*EXPERTS,'Ties')] for row in figure['rows']])
    left=np.zeros(3)
    for j,(expert,color) in enumerate(zip((*EXPERTS,'Ties'),('#4878b3','#df854d','#55a464','#cb4b51','#bdbdbd'))):
        widths=counts[:,j]*100/738
        ax.barh(np.arange(3),widths,left=left,label=expert,color=color)
        for i,count in enumerate(counts[:,j]):
            ax.text(left[i]+widths[i]/2,i,str(int(count)),ha='center',va='center',fontsize=9)
        left+=widths
    ax.set_yticks(range(3),['Target-only','Canonical 1-hop','Strict 2-hop']);ax.invert_yaxis()
    ax.set_xlim(0,100);ax.set_xlabel('Share of 738 held-out diseases (%)');ax.legend(ncols=5,loc='lower center',bbox_to_anchor=(.5,1.01),frameon=False)
    fig.text(.5,.01,'Historical evidence only (class 3) — paired protocol family; no protocol retraining',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,1))
    for suffix in ('svg','pdf','png'):
        fig.savefig(output/f'figure1_historical.{suffix}',dpi=180)
    plt.close(fig)
    write_table(output,'figure1_historical_counts',[{'protocol':row['protocol'],**dict(zip((*EXPERTS,'Ties'),counts[i].tolist())),'evidence_class':3} for i,row in enumerate(figure['rows'])])


def verify_exports(output, manifest):
    """Read generated CSVs back and compare to separately inventoried paper targets."""
    checks=[]
    def check(name, actual, expected, cls):
        difference=abs(float(actual)-float(expected))
        checks.append({'name':name,'pass':difference<=.000000500001,'actual':float(actual),'published':expected,'evidence_class':cls})
    def rows(name):
        with (output/(name+'.csv')).open(newline='') as f:return list(csv.DictReader(f))
    tables={t['table_id']:t for t in manifest['paper_tables']}
    t1={r['expert']:r for r in rows('table1')}
    for target in tables['T1']['rows']:
        for actual_key,target_key in [('Recall@50','Recall@50'),('applicable','applicable')]:check('T1/'+target['expert']+'/'+target_key,t1[target['expert']][actual_key],target[target_key],2)
        if target['seed_SD'] is not None:check('T1/'+target['expert']+'/SD',t1[target['expert']]['seed_SD_population'],target['seed_SD'],2)
    published={x['metric_id']:x for x in manifest['paper_metrics']}
    for key,row in [('SBS','SBS'),('VBS','VBS'),('gap','Oracle gap')]:check('T1/'+key,t1[row]['Recall@50'],published['T1.'+key]['reported_value'],2)
    t2={r['stage']:r for r in rows('table2')}
    for target in tables['T2']['rows']:
        if isinstance(target['outcome'],(int,float)):check('T2/'+target['stage'],t2[target['stage']]['outcome'],target['outcome'],2 if target['stage'] in ('SBS','VBS','GateA') else 3)
    t3=next(r for r in rows('table3') if r['protocol']=='CANONICAL_1HOP')
    target=next(r for r in tables['T3']['rows'] if r['protocol']=='CANONICAL_1HOP')
    for i,v in enumerate(target['F1_to_F8'],1):check('T3/canonical/F'+str(i),t3['F'+str(i)],v,1)
    for tid,name,key,cols,cls in [('T4','table4_historical','protocol',('E1_macro_R50','E2_macro_R50','E3_macro_R50','E4_macro_R50','SBS_macro_R50','VBS_macro_R50','SBS_VBS_gap'),3),('T5','table5','metric',('SBS','VBS','Gap'),2)]:
        actual={r[key]:r for r in rows(name)}
        for target in tables[tid]['rows']:
            for col in cols:check(tid+'/'+target[key]+'/'+col,actual[target[key]][col],target[col],cls)
    actual={r['protocol']:r for r in rows('figure1_historical_counts')}
    for target in manifest['paper_figures'][0]['rows']:
        for key,val in zip((*EXPERTS,'Ties'),target['E1_E2_E3_E4_Ties']):check('F1/'+target['protocol']+'/'+key,actual[target['protocol']][key],val,3)
    return {'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','scope':'Exported supported cells; historical rows remain class 3 and blank unsupported cells are excluded','checks':checks}


def reproduce(root, output):
    root=Path(root).resolve();output=output_directory(root,Path(output))
    registry=root/'artifacts/registry.json';frozen=root/'artifacts/frozen'
    manifest_path=root/'outputs/gate6c_claim_artifact_manifest.json'
    if sha256_file(manifest_path)!=PAPER_MANIFEST_SHA256:
        raise ValueError('paper claim manifest identity changed')
    manifest=json.loads(manifest_path.read_text())
    portfolio=load_portfolio(registry,frozen)
    core,vbs,winners=compute_core(portfolio)
    core_checks=compare_core(portfolio,core,frozen)
    cost=gate_a(portfolio,registry,frozen);cost_checks=compare_gate_a(cost,registry,frozen)
    evidence=downstream_evidence(registry,frozen)
    reference=validate(registry,frozen,'REFERENCE')
    benchmark=load_frozen_benchmark(registry,frozen,reference)
    paper_exports(output,core,cost,evidence,manifest,benchmark)
    export_checks=verify_exports(output,manifest)
    unsupported=[{'claim_id':c['claim_id'],'claim':c['claim'],'evidence_class':4,'reason':c['resolution_note']} for c in manifest['paper_claims'] if c['reconciliation_status'] in ('UNRESOLVED','DISCREPANCY','EXPLICITLY_UNRESOLVED_IN_PAPER')]
    # Raw scores/memberships/variant models/fits are not available to this pipeline.
    limitations=[
        'No model retraining or raw-score metric reevaluation; primary reductions are evidence class 2.',
        'Historical paired protocol/robustness summaries are class 3; Figure1 is not recomputed from protocol models.',
        'Target-only/strict-2hop fold counts are class 4 and left blank in Table3.',
        'Static and GateB results are class 3 historical replay, not refitted policies. META_TEST membership/outcomes are never read.',
        'Warm costs are historical implementation-specific measurements; no new timing/hardware claim.',
        'Entity-census wording, static-policy attribution and feature chronology limitations remain in the paper inventory.',
        'Redistribution and licensing review remains separate and unresolved.',
    ]
    write_json(output/'core_results.json',core);write_json(output/'gate_a.json',cost);write_json(output/'historical_evidence.json',evidence)
    write_json(output/'unsupported_results.json',unsupported)
    write_json(output/'robustness_historical.json',{'evidence_class':3,'note':'Selected observed historical scalars from the pinned claim manifest; no variant scores or models rerun.','observations':[m for m in manifest['paper_metrics'] if m['metric_id'].startswith(('J.','R.U1','R.U2','R.protocol.','F.E2_no_ontology'))],'source_hashes':manifest['external_evidence_observations']})
    # Generated disease-level outputs are kept in the user-selected output root, not Git.
    write_table(output,'disease_utilities',[{'disease_id':d,**{e:float(portfolio.values[i,j,METRICS.index('Recall@50')]) for j,e in enumerate(EXPERTS)},**{e+'_applicable':bool(portfolio.applicable[i,j]) for j,e in enumerate(EXPERTS)},'VBS':float(vbs[i]),'winner':winners[i],'evidence_class':2} for i,d in enumerate(portfolio.disease_ids)], decimals=None, markdown=False)
    result={'status':'PASS' if all(c['status']=='PASS' for c in (core_checks,cost_checks,export_checks)) else 'FAIL',
            'scope':'Supported historical-result package; not complete independent paper/model reproduction',
            'complete_paper_reproduction':False,'evidence_classes':EVIDENCE_CLASSES,'core_equivalence':core_checks,'gate_a_equivalence':cost_checks,'export_equivalence':export_checks,
            'paper_sha256':manifest['authoritative_target']['sha256'],'paper_claim_manifest_sha256':PAPER_MANIFEST_SHA256,
            'resolved_historical_contracts':core['contract'],'limitations':limitations,'unsupported_claim_count':len(unsupported),
            'training_started':False,'META_TEST_read':False,'environment':{'python':platform.python_version(),'numpy':np.__version__,'matplotlib':__import__('matplotlib').__version__},
            'implementation_sha256':{name:sha256_file(Path(__file__).parent/name) for name in ('analysis.py','downstream.py','reproduction.py')},
            'input_registry_sha256':sha256_file(registry)}
    write_json(output/'equivalence_report.json',result)
    (output/'LIMITATIONS.md').write_text('# Reproduction scope\n\n'+'\n'.join('- '+x for x in limitations)+'\n\nEvidence classes:\n\n'+'\n'.join(f'- {k}: {v}' for k,v in EVIDENCE_CLASSES.items())+'\n',encoding='utf-8')
    files={p.name:sha256_file(p) for p in sorted(output.iterdir()) if p.is_file() and p.name!='output_manifest.json'}
    write_json(output/'output_manifest.json',{'files_sha256':files,'family':'ORIGINAL_CANONICAL unless explicitly labeled paired/historical','evidence_classes':EVIDENCE_CLASSES,'paper_sha256':result['paper_sha256']})
    return result
