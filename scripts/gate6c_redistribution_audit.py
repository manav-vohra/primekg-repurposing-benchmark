"""Inventory tracked filenames/hashes and possible redistribution issues; no clearance implied."""
import csv,hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
records=[]
main_files=set(subprocess.check_output(['git','ls-tree','-r','--name-only','origin/main'],cwd=root,text=True).splitlines())
for name in filter(None,paths):
 p=root/name;b=p.read_bytes(); s=b.decode('utf-8',errors='replace')
 db=len(set(re.findall(r'\bDB\d{5}\b',s)))
 columns=next(csv.reader(s.splitlines()),[]) if p.suffix=='.csv' else []
 risk=[]
 if name.startswith('artifacts/frozen/'):
  if name.startswith('artifacts/frozen/reference_results/') or 'expected_utility_matrix' in name: risk.append('DISEASE_LEVEL_DERIVED_RESULTS')
  elif name.endswith('p1_e3_complex_entities.csv'):risk.append('MULTISOURCE_GRAPH_ENTITY_MAPPING')
  elif columns and any(c in columns for c in ['drug_id','disease_id','entity_id']):risk.append('GRAPH_DERIVED_IDENTIFIERS_OR_LABELS')
  else:risk.append('DERIVED_CONTRACT_OR_SUMMARY')
 if db:risk.append('DRUGBANK_IDENTIFIER_CONTENT')
 if re.search(r'/content/drive/|[A-Z]:\\Users\\',s):risk.append('MACHINE_SPECIFIC_PROVENANCE_PATHS')
 if re.search(r'drive.google.com|connected_source_id|drive_id|external_drive',s):risk.append('EXTERNAL_ARTIFACT_LOCATORS_REVIEW_ACCESS')
 if p.suffix in ['.npz','.pt','.pth','.zip','.tar','.gz'] or p.name=='kg.csv':risk.append('RAW_OR_LARGE_EXTERNAL_OBJECT')
 if not risk:risk=['CODE_DOCUMENTATION_OR_SYNTHETIC_FIXTURE']
 main_digest=hashlib.sha256(subprocess.check_output(['git','show','origin/main:'+name],cwd=root)).hexdigest() if name in main_files else None
 records.append(dict(observed_main_sha256=main_digest,path=name,tracked_on_observed_main=name in main_files,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),risk_flags=risk,unique_drugbank_identifiers=db,csv_columns=columns,redistribution_clearance='NOT_ESTABLISHED',raw_content_republished=False))
out=dict(audit='GATE_6C_A_TRACKED_REDISTRIBUTION',scope='Current tracked tree; not Git history, external archives or a legal opinion',tracked_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip(),tracked_file_count=len(records),observed_main_sha=subprocess.check_output(['git','rev-parse','origin/main'],cwd=root,text=True).strip(),observed_main_file_count=len(main_files),license_files=[r['path'] for r in records if re.search(r'(^|/)(LICENSE|COPYING|NOTICE)',r['path'],re.I)],risk_flag_counts=dict(Counter(f for r in records for f in r['risk_flags'])),records=records)
(root/'outputs/gate6c_redistribution_audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='records'},indent=2))
print('Highest-priority identifier/label files:')
for r in records:
 if 'DRUGBANK_IDENTIFIER_CONTENT' in r['risk_flags'] and r['unique_drugbank_identifiers']>10:print(r['path'],r['unique_drugbank_identifiers'])
