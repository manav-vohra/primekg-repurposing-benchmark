import csv
import json
from pathlib import Path
import pytest
from primekg_repurposing.cli import main
from primekg_repurposing.reproduction import reproduce, output_directory, verify_exports

ROOT=Path(__file__).resolve().parents[1]


def test_output_guard_blocks_references_and_ancestors(tmp_path):
    for path in [ROOT,ROOT.parent,ROOT/'artifacts/frozen/new',ROOT/'src/new',ROOT/'outputs/new']:
        with pytest.raises(ValueError,match='overlaps'):output_directory(ROOT,path)
    assert output_directory(ROOT,tmp_path/'generated').is_dir()


def test_one_command_exports_supported_tables_and_explicit_limitations(tmp_path):
    out=tmp_path/'release'
    assert main(['reproduce','--repository-root',str(ROOT),'--output',str(out)])==0
    report=json.loads((out/'equivalence_report.json').read_text())
    assert report['status']=='PASS' and not report['complete_paper_reproduction']
    assert not report['training_started'] and not report['META_TEST_read']
    assert report['unsupported_claim_count']>0
    robustness=json.loads((out/'robustness_historical.json').read_text())
    assert all(x['family']=='PAIRED_PROTOCOL_COMPARABLE' for x in robustness['observations'] if x['metric_id'].startswith('R.protocol.'))
    assert all(x['family']=='ORIGINAL_CANONICAL' for x in robustness['observations'] if x['metric_id'].startswith('J.'))
    for name in ('table1.csv','table2.csv','table3.csv','table4_historical.csv','table5.csv','figure1_historical.svg','figure1_historical.pdf','figure1_historical.png','output_manifest.json','robustness_historical.json'):
        assert (out/name).stat().st_size>0
    with (out/'table3.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    assert rows[0]['evidence_class']=='4' and rows[0]['F1']==''
    assert rows[1]['evidence_class']=='1' and rows[1]['F1']=='6856'
    with (out/'disease_utilities.csv').open(newline='') as f:
        utilities=list(csv.DictReader(f))
    assert len(utilities)==738 and sum(all(r[e+'_applicable']=='False' for e in ('E1','E2','E3','E4')) for r in utilities)==2
    # A rendered cell is checked independently against the primary-paper target.
    table=out/'table5.csv';table.write_text(table.read_text().replace('0.406243','0.906243'))
    manifest=json.loads((ROOT/'outputs/gate6c_claim_artifact_manifest.json').read_text())
    assert verify_exports(out,manifest)['status']=='FAIL'


def test_manifest_identity_cannot_be_silently_replaced(tmp_path,monkeypatch):
    import primekg_repurposing.reproduction as module
    monkeypatch.setattr(module,'PAPER_MANIFEST_SHA256','0'*64)
    with pytest.raises(ValueError,match='manifest identity'):
        reproduce(ROOT,tmp_path/'bad')
