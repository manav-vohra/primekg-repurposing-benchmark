"""Coverage, provenance and corruption checks; no downstream scientific analysis."""
import copy
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
validate_inventory = runpy.run_path(str(ROOT / 'scripts/gate6c_validate_inventory.py'))['validate_inventory']


@pytest.fixture
def manifest():
    return json.loads((ROOT / 'outputs/gate6c_claim_artifact_manifest.json').read_text())


def test_complete_primary_paper_inventory_resolves_all_links(manifest):
    r = validate_inventory(manifest)
    assert r['pages'] == 10 and r['tables'] == 5 and r['figures'] == 1
    assert r['claim_status_counts']['UNRESOLVED'] > 0
    assert not r['scientific_reproduction_complete'] and not r['gate8_started']


def test_wrong_paper_cannot_replace_authoritative_version(manifest, tmp_path):
    manifest['authoritative_target']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='paper identity'):
        validate_inventory(manifest)
    manifest['authoritative_target']['sha256'] = 'ab7e80b1d82046c7c26886710a4fb5f53884534d289d787185c1ee7fc0faff87'
    p = tmp_path / 'earlier.pdf'; p.write_bytes(b'earlier manuscript')
    with pytest.raises(ValueError, match='paper bytes differ'):
        validate_inventory(manifest, paper=p)


def test_missing_page_or_scientific_block_rejected(manifest):
    before = copy.deepcopy(manifest)
    manifest['paper_pages'].pop()
    with pytest.raises(ValueError, match='missing paper page'):
        validate_inventory(manifest)
    manifest = before
    manifest['paper_coverage'] = [u for u in manifest['paper_coverage'] if u['unit_id'] != 'p1.b4']
    with pytest.raises(ValueError, match='PDF block'):
        validate_inventory(manifest)


def test_unmapped_paragraph_is_not_hidden(manifest):
    next(u for u in manifest['paper_coverage'] if u['unit_id'] == 'p1.b4')['claim_ids'] = []
    with pytest.raises(ValueError, match='unmapped scientific block'):
        validate_inventory(manifest)


def test_missing_table_cell_is_not_hidden(manifest):
    manifest['paper_metrics'] = [x for x in manifest['paper_metrics'] if x['metric_id'] != 'T5.MRR.Gap']
    with pytest.raises(ValueError, match='missing table metric'):
        validate_inventory(manifest)


def test_original_and_paired_families_cannot_be_substituted(manifest):
    next(t for t in manifest['paper_tables'] if t['table_id'] == 'T4')['family'] = 'ORIGINAL_CANONICAL'
    with pytest.raises(ValueError, match='paired family conflated'):
        validate_inventory(manifest)


def test_figures_cannot_exchange_counts_while_preserving_sum(manifest):
    row = manifest['paper_figures'][0]['rows'][0]['E1_E2_E3_E4_Ties']
    row[0], row[1] = row[1], row[0]
    with pytest.raises(ValueError, match='figure label value mismatch'):
        validate_inventory(manifest)


def test_unavailable_output_cannot_be_called_verified(manifest):
    metric = next(x for x in manifest['paper_metrics'] if x['metric_id'] == 'T3.STRICT_2HOP.F1')
    metric['status'] = 'SUPPORTED_HISTORICAL_EVIDENCE'
    next(c for c in manifest['paper_claims'] if c['claim_id'] == metric['claim_id'])['reconciliation_status'] = metric['status']
    with pytest.raises(ValueError, match='missing scalar falsely marked supported'):
        validate_inventory(manifest)


def test_scalar_rounding_cannot_hide_changed_result(manifest):
    metric = next(x for x in manifest['paper_metrics'] if x['metric_id'] == 'T5.MRR.Gap')
    metric['observed_evidence_value'] = 0.5
    with pytest.raises(ValueError, match='scalar mismatch hidden'):
        validate_inventory(manifest)


def test_recovery_digest_does_not_become_historical_hash(manifest):
    manifest['external_evidence_observations'][0]['historical_hash_verified'] = True
    with pytest.raises(ValueError, match='promoted to historical identity'):
        validate_inventory(manifest)


def test_missing_evidence_and_unexplained_claim_rejected(manifest):
    before = copy.deepcopy(manifest)
    manifest['paper_claims'][0]['evidence_refs'] = ['invented/result.csv']
    with pytest.raises(ValueError, match='unknown evidence reference'):
        validate_inventory(manifest)
    manifest = before
    manifest['paper_claims'][0]['resolution_note'] = ''
    with pytest.raises(ValueError, match='without explanation'):
        validate_inventory(manifest)


def test_changed_reference_bytes_are_rejected(manifest, tmp_path):
    item = manifest['frozen_artifacts'][0]
    p = tmp_path / 'changed.csv'; p.write_bytes(b'changed reference')
    item['path'] = str(p)
    with pytest.raises(ValueError, match='evidence hash mismatch'):
        validate_inventory(manifest)
