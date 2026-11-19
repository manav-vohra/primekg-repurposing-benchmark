"""Validate paper coverage and evidence lineage; never aggregate expert utilities.

Optional --paper and --evidence-index verify original bytes locally. CI validates
coverage, links, reported scalar rounding and bundled hashes without external data.
"""
from __future__ import annotations
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER_SHA256 = 'ab7e80b1d82046c7c26886710a4fb5f53884534d289d787185c1ee7fc0faff87'
RESOLUTIONS = {'SUPPORTED_HISTORICAL_EVIDENCE', 'SUPPORTED_FROZEN_CONTRACT', 'UNRESOLVED', 'DISCREPANCY', 'EXPLICITLY_UNRESOLVED_IN_PAPER', 'SCOPE_OR_INTERPRETATION', 'CONTEXT_OR_DEFINITION', 'PUBLIC_RELEASE_COMMITMENT_NOT_COMPLETION_CLAIM'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(items, key):
    values = [x[key] for x in items]
    require(len(set(values)) == len(values), f'duplicate {key}')
    return {x[key]: x for x in items}


def validate_inventory(manifest, root=ROOT, paper=None, evidence_index=None):
    m = manifest
    target = m['authoritative_target']
    require(target['sha256'] == PAPER_SHA256 and target['page_count'] == 10, 'wrong authoritative paper identity')
    require(target['size_bytes'] == 258644 and target['filename'] == '163_From_Complementarity_to_Ac (1).pdf', 'wrong authoritative file metadata')
    require(target['confirmed'] and target['all_pages_read'] and m['paper_inventory_complete'], 'incomplete paper inventory')
    pages = unique(m['paper_pages'], 'page')
    require(set(pages) == set(range(1, 11)), 'missing paper page')
    require(all(p['read_complete'] and p['characters'] > 0 and len(p['text_sha256']) == 64 for p in pages.values()), 'unreadable paper page')
    claims = unique(m['paper_claims'], 'claim_id')
    units = unique(m['paper_coverage'], 'unit_id')
    require(claims and units, 'empty paper coverage')
    for page, data in pages.items():
        blocks = sorted(u['block'] for u in units.values() if u['page'] == page)
        require(blocks == list(range(data['block_count'])), 'missing or repeated PDF block')
    for uid, u in units.items():
        require(u['reviewed'] and len(u['text_sha256']) == 64, 'unreviewed PDF block')
        if u['kind'] == 'SCIENTIFIC_CONTENT':
            require(u['claim_ids'], 'unmapped scientific block')
        else:
            require(u.get('exclusion_reason'), 'unexplained paper exclusion')
        for cid in u['claim_ids']:
            require(cid in claims and uid in claims[cid]['locations'], 'broken block-to-claim link')
    known = {a['artifact_id'] for a in m['frozen_artifacts']}
    known.update(a['evidence_id'] for key in ('external_evidence_observations', 'implementation_observations', 'prior_gate_report_observations', 'unavailable_evidence') for a in m[key])
    for cid, c in claims.items():
        require(c['locations'] and c['accounted_for'] and c['claim'], 'unaccounted paper claim')
        require(c['reconciliation_status'] in RESOLUTIONS and c['resolution_note'], 'unresolved or unsupported claim without explanation')
        require(c['evidence_refs'] and set(c['evidence_refs']) <= known, 'unknown evidence reference')
        require(c['historical_source_ids'] and set(c['historical_source_ids']) <= set(m['historical_sources']), 'unknown historical source')
        for uid in c['locations']:
            require(uid in units and cid in units[uid]['claim_ids'], 'broken claim-to-block link')
    metrics = unique(m['paper_metrics'], 'metric_id')
    for metric in metrics.values():
        require(metric['claim_id'] in claims and metric['evidence_ref'] in known, 'broken metric evidence link')
        observed = metric['observed_evidence_value']
        status = metric['status']
        require(status == claims[metric['claim_id']]['reconciliation_status'], 'metric/claim status mismatch')
        require(claims[metric['claim_id']]['reported_values'].get('value') == metric['reported_value'], 'metric/claim value mismatch')
        if observed is None:
            require(status == 'UNRESOLVED', 'missing scalar falsely marked supported')
        elif isinstance(metric['reported_value'], (int, float)):
            display = Decimal(metric['reported_display'])
            tolerance = Decimal(0) if isinstance(metric['reported_value'], int) else Decimal(5).scaleb(-metric['display_decimal_places']-1)
            require(abs(display-Decimal(str(observed))) <= tolerance+Decimal('1e-12') or status == 'DISCREPANCY', 'scalar mismatch hidden by rounding')
        else:
            require(metric['reported_value'] == observed or status == 'DISCREPANCY', 'label mismatch')
    tables = unique(m['paper_tables'], 'table_id')
    require(set(tables) == {'T1','T2','T3','T4','T5'}, 'missing paper table')
    for tid, rows in [('T1',4),('T2',6),('T3',3),('T4',3),('T5',7)]:
        require(len(tables[tid]['rows']) == rows and tables[tid]['claim_ids'], 'missing table row')
    for table in tables.values():
        require(set(table['claim_ids']) <= set(claims), 'unknown table claim')
        require(set(table['claim_ids']) <= set(metrics), 'missing table metric record')
    require(tables['T1']['family'] == tables['T5']['family'] == 'ORIGINAL_CANONICAL', 'original result family changed')
    require(tables['T4']['family'] == 'PAIRED_PROTOCOL_COMPARABLE', 'paired family conflated')
    require(len(tables['T3']['claim_ids']) == 24 and all(len(r['F1_to_F8']) == 8 for r in tables['T3']['rows']), 'missing fold cell')
    require(len(tables['T4']['claim_ids']) == len(tables['T5']['claim_ids']) == 21, 'missing quantitative table cell')
    figs = unique(m['paper_figures'], 'figure_id')
    require(set(figs) == {'F1'}, 'missing or substituted paper figure')
    f = figs['F1']
    require(f['page'] == 8 and f['family'] == 'PAIRED_PROTOCOL_COMPARABLE' and len(f['claim_ids']) == 15, 'figure coverage or lineage wrong')
    require(len(f['rows']) == 3 and all(len(r['E1_E2_E3_E4_Ties']) == 5 and sum(r['E1_E2_E3_E4_Ties']) == r['denominator'] == 738 for r in f['rows']), 'figure count/denominator mismatch')
    require(set(f['claim_ids']) <= set(claims), 'broken figure claim')
    require(set(f['claim_ids']) <= set(metrics), 'missing figure metric record')
    for row in tables['T1']['rows']:
        for key in ('applicable', 'denominator', 'Recall@50'):
            require(metrics[f'T1.{row["expert"]}.{key}']['reported_value'] == row[key], 'table1 value mismatch')
        if row['seed_SD'] is not None:
            require(metrics[f'T1.{row["expert"]}.seed_SD']['reported_value'] == row['seed_SD'], 'table1 SD mismatch')
    for row in tables['T2']['rows']:
        require(metrics[f'T2.{row["stage"]}']['reported_value'] == row['outcome'], 'table2 value mismatch')
    for row in tables['T3']['rows']:
        for i, value in enumerate(row['F1_to_F8'], 1):
            require(metrics[f'T3.{row["protocol"]}.F{i}']['reported_value'] == value, 'table3 value mismatch')
    for row in tables['T4']['rows']:
        for key, value in row.items():
            if key != 'protocol':
                require(metrics[f'T4.{row["protocol"]}.{key}']['reported_value'] == value, 'table4 value mismatch')
    for row in tables['T5']['rows']:
        require(row['SBS_expert'] == 'E2', 'table5 SBS identity mismatch')
        for key in ('SBS', 'VBS', 'Gap'):
            require(metrics[f'T5.{row["metric"]}.{key}']['reported_value'] == row[key], 'table5 value mismatch')
    for row in f['rows']:
        for expert, value in zip(('E1', 'E2', 'E3', 'E4', 'Ties'), row['E1_E2_E3_E4_Ties']):
            require(metrics[f'F1.{row["protocol"]}.{expert}']['reported_value'] == value, 'figure label value mismatch')
    for key in ('frozen_artifacts', 'implementation_observations', 'prior_gate_report_observations'):
        for item in m[key]:
            path = root/item['path']
            expected = item.get('expected_sha256', item.get('sha256'))
            require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'evidence hash mismatch: {item["path"]}')
    for item in m['external_evidence_observations']:
        require(item['hash_classification'] == 'RECOVERY_TIME_OBSERVED_2026_11_19' and not item['historical_hash_verified'], 'recovered hash promoted to historical identity')
    external_checked = 0
    if evidence_index is not None:
        index = {item['title']: item for item in evidence_index}
        for item in m['external_evidence_observations']:
            path = Path(index[item['filename']]['download']['path'])
            data = path.read_bytes()
            require(len(data) == item['size_bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], 'external evidence raw bytes differ')
            external_checked += 1
    if paper is not None:
        data = Path(paper).read_bytes()
        require(len(data) == target['size_bytes'] and hashlib.sha256(data).hexdigest() == PAPER_SHA256, 'paper bytes differ')
    require(m['gate_decision'] == 'PASS' and m['gate_decision_scope'].startswith('Complete paper inventory'), 'ambiguous gate decision')
    require(not m['scientific_reproduction_complete'] and not m['gate8_started'] and not m['next_gate_authorized'], 'inventory mislabeled as scientific execution')
    for d in m['paper_discrepancies']:
        require(d['details'] and set(d['claims']) <= set(claims), 'unexplained discrepancy')
    return {'gate':'PHASE_2_GATE_6C_A','decision':'PASS','scope':'Inventory coverage and provenance accounting; unresolved claims retained, not validated as scientific truth','paper_sha256':PAPER_SHA256,'pages':10,'coverage_units':len(units),'scientific_units':sum(u['kind']=='SCIENTIFIC_CONTENT' for u in units.values()),'claims':len(claims),'metrics':len(metrics),'tables':5,'figures':1,'claim_status_counts':dict(Counter(c['reconciliation_status'] for c in claims.values())),'external_raw_objects_verified_this_run':external_checked,'paper_bytes_verified_this_run':paper is not None,'scientific_reproduction_complete':False,'gate8_started':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', type=Path)
    parser.add_argument('--evidence-index', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    m=json.loads((ROOT/'outputs/gate6c_claim_artifact_manifest.json').read_text())
    evidence=json.loads(args.evidence_index.read_text()) if args.evidence_index else None
    report=validate_inventory(m,paper=args.paper,evidence_index=evidence)
    if args.report:
        args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
