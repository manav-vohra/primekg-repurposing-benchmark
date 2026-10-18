"""Rebuild the P1-v0 benchmark from hash-verified raw PrimeKG.

Scientific behavior is traced to historical notebook Cells 2, 3, 5, 9--13.
Frozen outputs are read only by the equivalence comparator, never the producer.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .provenance import load_registry, sha256_file

THERAPEUTIC = frozenset({"indication", "contraindication", "off-label use"})
ROLE_COLUMNS = ["CLEAN_INDICATION", "AMBIGUOUS_INDICATION", "CONTRAINDICATION_ONLY", "OFFLABEL_ONLY", "CONFLICTING_NONINDICATION"]
OUTPUTS = ["p1_v0_candidate_drugs.csv", "p1_v0_primary_diseases.csv", "p1_v0_primary_eval_roles.csv", "p1_v0_primary_truth.csv", "p1_v0_k8_quarantine_manifest.csv", "p1_v0_fold_summary.csv", "p1_v0_benchmark_manifest.json"]
KEYS = {OUTPUTS[0]: ["drug_id"], OUTPUTS[1]: ["disease_id"], OUTPUTS[2]: ["disease_id", "drug_id"], OUTPUTS[3]: ["disease_id", "drug_id"], OUTPUTS[4]: ["fold", "role", "disease_id"], OUTPUTS[5]: ["fold"]}


def verified_raw_path(registry_path: Path, data_root: Path, raw_override: Path | None = None) -> tuple[Path | None, dict]:
    """Resolve the Gate-1 logical raw path, then demand its registered hash."""
    registry = load_registry(registry_path)
    item = next(x for x in registry["artifacts"] if x["artifact_id"] == "raw/kg.csv")
    logical = Path(item["logical_path"])
    if logical.is_absolute() or ".." in logical.parts:
        raise ValueError("unsafe raw logical path")
    path = raw_override if raw_override is not None else data_root / logical
    report = {"artifact_id": item["artifact_id"], "logical_path": item["logical_path"], "path": str(path), "expected_sha256": item["expected_sha256"], "observed_sha256": None, "status": "MISSING_RAW_INPUT"}
    if not path.is_file():
        return None, report
    observed = sha256_file(path)
    report["observed_sha256"] = observed
    if observed != item["expected_sha256"] or path.stat().st_size != item["expected_size"]:
        report["status"] = "RAW_HASH_MISMATCH"
        return None, report
    report["status"] = "VERIFIED"
    return path, report


def classify_role(labels: tuple[str, ...]) -> str:
    """Cell 11: observed-label combinations; no binary negatives."""
    labels = set(labels)
    if labels == {"indication"}:
        return "CLEAN_INDICATION"
    if "indication" in labels:
        return "AMBIGUOUS_INDICATION"
    if labels == {"contraindication"}:
        return "CONTRAINDICATION_ONLY"
    if labels == {"off-label use"}:
        return "OFFLABEL_ONLY"
    if labels == {"contraindication", "off-label use"}:
        return "CONFLICTING_NONINDICATION"
    raise ValueError(f"unexpected therapeutic labels: {labels}")


def clean_count_bin(value: int) -> str:
    return "03_04" if value <= 4 else "05_09" if value <= 9 else "10_19" if value <= 19 else "20_plus"


def evidence_bin(value: int) -> str:
    return "zero" if value == 0 else "01_02" if value <= 2 else "03_09" if value <= 9 else "10_49" if value <= 49 else "50_plus"


def make_fold_assignment(primary: Any, k: int = 8, seed: int = 42) -> dict[str, int]:
    """Cell 12 RandomState shuffle, sorted strata, periodically least-loaded folds."""
    import numpy as np

    rng = np.random.RandomState(seed)
    sizes = {fold: 0 for fold in range(k)}
    assigned: dict[str, int] = {}
    for stratum in sorted(primary["stratum"].unique()):
        ids = primary.loc[primary["stratum"] == stratum, "disease_id"].astype(str).tolist()
        rng.shuffle(ids)
        fold_order: list[int] = []
        for cursor, disease_id in enumerate(ids):
            if cursor % k == 0:
                fold_order = sorted(range(k), key=lambda fold: (sizes[fold], fold))
            fold = fold_order[cursor % k]
            assigned[disease_id] = fold
            sizes[fold] += 1
    if len(assigned) != len(primary):
        raise ValueError("fold assignment lost or duplicated disease")
    return assigned


def derive_buffers(targets: set[str], adjacency: dict[str, set[str]]) -> set[str]:
    """Cell 13 union of direct indication-annotated ontology neighbors."""
    buffer: set[str] = set()
    for disease_id in targets:
        buffer.update(adjacency.get(disease_id, ()))
    return buffer - targets


def _read_raw(raw_path: Path):
    import pandas as pd

    return pd.read_csv(raw_path, chunksize=500_000, low_memory=False, dtype="string", usecols=["relation", "display_relation", "x_id", "x_type", "x_name", "x_source", "y_id", "y_type", "y_name", "y_source"])


def reconstruct(raw_path: Path, output_dir: Path) -> dict:
    """Produce seven separate artifacts; never consult frozen expected outputs."""
    import numpy as np
    import pandas as pd

    output_dir.mkdir(parents=True, exist_ok=True)
    directed = 0
    relation_counts: Counter[str] = Counter()
    nodes: dict[str, set[str]] = defaultdict(set)
    nonther_nodes: set[tuple[str, str]] = set()
    ther_parts = []
    drug_names: dict[str, set[str]] = defaultdict(set)
    drug_ids: set[str] = set()
    has_nonther: set[str] = set()
    drug_protein: dict[str, set[str]] = defaultdict(set)
    drug_effect: dict[str, set[str]] = defaultdict(set)
    drug_drug: set[str] = set()

    # Cells 2, 3 and 9. Names are picked as Cell 9's lexical minimum.
    for chunk in _read_raw(raw_path):
        directed += len(chunk)
        relation_counts.update({str(k): int(v) for k, v in chunk["relation"].value_counts().items()})
        for side in ("x", "y"):
            for node_type, group in chunk.groupby(f"{side}_type"):
                nodes[str(node_type)].update(group[f"{side}_id"].dropna().astype(str).unique())
            drugs = chunk.loc[chunk[f"{side}_type"] == "drug", [f"{side}_id", f"{side}_name"]].drop_duplicates()
            for drug_id, name in drugs.itertuples(index=False, name=None):
                if pd.isna(drug_id):
                    continue
                drug_id = str(drug_id)
                drug_ids.add(drug_id)
                if pd.notna(name):
                    drug_names[drug_id].add(str(name))
        ther = chunk.loc[chunk["relation"].isin(THERAPEUTIC)]
        if not ther.empty:
            x = ther["x_type"] == "drug"
            y = ther["y_type"] == "drug"
            if not ((x & (ther["y_type"] == "disease")) | (y & (ther["x_type"] == "disease"))).all():
                raise ValueError("unexpected therapeutic direction signature")
            canonical = pd.DataFrame({
                "relation": ther["relation"],
                "drug_id": ther["x_id"].where(x, ther["y_id"]),
                "drug_name": ther["x_name"].where(x, ther["y_name"]),
                "drug_source": ther["x_source"].where(x, ther["y_source"]),
                "disease_id": ther["y_id"].where(x, ther["x_id"]),
                "disease_name": ther["y_name"].where(x, ther["x_name"]),
                "disease_source": ther["y_source"].where(x, ther["x_source"]),
            })
            ther_parts.append(canonical)
        nonther = chunk.loc[~chunk["relation"].isin(THERAPEUTIC)]
        for side in ("x", "y"):
            for node_type, group in nonther.groupby(f"{side}_type"):
                nonther_nodes.update((str(node_type), str(node_id)) for node_id in group[f"{side}_id"].dropna().astype(str).unique())
        for side, other in (("x", "y"), ("y", "x")):
            rows = nonther.loc[nonther[f"{side}_type"] == "drug", ["relation", f"{side}_id", f"{other}_id", f"{other}_type"]]
            for relation, drug_id, neighbor_id, neighbor_type in rows.itertuples(index=False, name=None):
                drug_id = str(drug_id)
                has_nonther.add(drug_id)
                if relation == "drug_protein" and neighbor_type == "gene/protein":
                    drug_protein[drug_id].add(str(neighbor_id))
                elif relation == "drug_effect" and neighbor_type == "effect/phenotype":
                    drug_effect[drug_id].add(str(neighbor_id))
                elif relation == "drug_drug" and neighbor_type == "drug":
                    drug_drug.update((drug_id, str(neighbor_id)))

    therapeutic = pd.concat(ther_parts, ignore_index=True).drop_duplicates(subset=["relation", "drug_id", "disease_id"]).reset_index(drop=True)
    pair_roles = therapeutic.groupby(["drug_id", "disease_id"], dropna=False)["relation"].agg(lambda values: tuple(sorted(set(values)))).reset_index(name="labels")
    pair_roles["evaluation_role"] = pair_roles["labels"].map(classify_role)
    role_counts = {str(k): int(v) for k, v in pair_roles["evaluation_role"].value_counts().items()}

    # Cell 9/10: all drug nodes remain U0 regardless of labels.
    candidate = pd.DataFrame([{"drug_id": drug_id, "drug_name": min(drug_names[drug_id]) if drug_names[drug_id] else None, "has_nontherapeutic_evidence": drug_id in has_nonther, "gene_protein_neighbor_count": len(drug_protein[drug_id]), "effect_phenotype_neighbor_count": len(drug_effect[drug_id]), "has_drug_drug_evidence": drug_id in drug_drug} for drug_id in sorted(drug_ids)])
    universes = {"U0": len(drug_ids), "U1": len(has_nonther), "U2": sum(bool(drug_protein[x]) for x in drug_ids)}

    # Cell 3 disease name map: first canonical indication record per disease.
    indication = therapeutic.loc[therapeutic["relation"] == "indication"]
    disease_names = indication.drop_duplicates(subset=["disease_id"]).set_index("disease_id")["disease_name"].to_dict()
    clean = pair_roles.loc[pair_roles["evaluation_role"] == "CLEAN_INDICATION"]
    clean_counts = clean.groupby("disease_id")["drug_id"].nunique()
    cohort = set(clean_counts.loc[clean_counts >= 3].index.astype(str))
    cohort_roles = pair_roles.loc[pair_roles["disease_id"].isin(cohort)]
    disease_roles = cohort_roles.groupby(["disease_id", "evaluation_role"]).size().unstack(fill_value=0)
    for role in ROLE_COLUMNS:
        if role not in disease_roles:
            disease_roles[role] = 0
    disease_roles = disease_roles[ROLE_COLUMNS].reset_index()
    disease_roles["disease_name"] = disease_roles["disease_id"].map(disease_names)
    disease_roles["observed_therapeutic_pairs"] = disease_roles[ROLE_COLUMNS].sum(axis=1)
    disease_roles["unobserved_candidates"] = len(candidate) - disease_roles["observed_therapeutic_pairs"]
    disease_roles["primary_ignore_count"] = disease_roles[["AMBIGUOUS_INDICATION", "OFFLABEL_ONLY", "CONFLICTING_NONINDICATION"]].sum(axis=1)
    disease_roles["primary_scored_candidate_count"] = len(candidate) - disease_roles["primary_ignore_count"]

    # Cells 5 and 12/13: derive pre-label evidence descriptors and ontology
    # adjacency from raw edges, restricted to the cohorts needed by Cell 12.
    any_indication = set(pair_roles.loc[pair_roles["evaluation_role"].isin(["CLEAN_INDICATION", "AMBIGUOUS_INDICATION"]), "disease_id"].astype(str))
    typed_neighbors: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    adjacency: dict[str, set[str]] = defaultdict(set)
    for chunk in _read_raw(raw_path):
        nonther = chunk.loc[~chunk["relation"].isin(THERAPEUTIC)]
        for side, other in (("x", "y"), ("y", "x")):
            relevant = nonther.loc[(nonther[f"{side}_type"] == "disease") & nonther[f"{side}_id"].isin(cohort), [f"{side}_id", f"{other}_type", f"{other}_id"]].drop_duplicates()
            for disease_id, neighbor_type, neighbor_id in relevant.itertuples(index=False, name=None):
                typed_neighbors[str(disease_id)][str(neighbor_type)].add(str(neighbor_id))
        ontology = chunk.loc[(chunk["relation"] == "disease_disease") & (chunk["x_type"] == "disease") & (chunk["y_type"] == "disease") & chunk["x_id"].isin(any_indication) & chunk["y_id"].isin(any_indication), ["x_id", "y_id"]].drop_duplicates()
        for a, b in ontology.itertuples(index=False, name=None):
            a, b = str(a), str(b)
            if a != b:
                adjacency[a].add(b)
                adjacency[b].add(a)
    disease_roles["nonontology_neighbor_count"] = disease_roles["disease_id"].map(lambda x: sum(len(typed_neighbors[str(x)][kind]) for kind in ("gene/protein", "effect/phenotype", "exposure")))
    disease_roles["stratum"] = disease_roles.apply(lambda row: clean_count_bin(row["CLEAN_INDICATION"]) + "__" + evidence_bin(row["nonontology_neighbor_count"]), axis=1)
    fold_lookup = make_fold_assignment(disease_roles, 8, 42)
    disease_roles["oof_fold"] = disease_roles["disease_id"].map(fold_lookup).astype(int)
    primary_diseases = disease_roles.drop(columns=["nonontology_neighbor_count", "stratum"]).sort_values(["oof_fold", "disease_id"]).reset_index(drop=True)
    primary_roles = cohort_roles.sort_values(["disease_id", "drug_id"]).reset_index(drop=True)
    primary_truth = primary_roles.loc[primary_roles["evaluation_role"] == "CLEAN_INDICATION", ["disease_id", "drug_id", "labels", "evaluation_role"]].sort_values(["disease_id", "drug_id"]).reset_index(drop=True)

    global_clean_counts = clean.groupby("disease_id").size().to_dict()
    global_ther_counts = pair_roles.groupby("disease_id").size().to_dict()
    quarantine_rows = []
    fold_rows = []
    raw_exposures = 0
    for fold in range(8):
        targets = {d for d, f in fold_lookup.items() if f == fold}
        buffers = derive_buffers(targets, adjacency)
        hidden = targets | buffers
        for role, ids in (("TARGET", targets), ("BUFFER", buffers)):
            for disease_id in sorted(ids):
                quarantine_rows.append({"fold": fold, "disease_id": disease_id, "role": role, "hide_all_therapeutic_relations": True})
        leaks = sum(len(adjacency.get(d, set()) - hidden) for d in targets)
        raw_exposures += sum(len(adjacency.get(d, set())) for d in targets)
        hidden_clean = sum(global_clean_counts.get(d, 0) for d in hidden)
        hidden_ther = sum(global_ther_counts.get(d, 0) for d in hidden)
        fold_rows.append({"fold": fold, "target_diseases": len(targets), "buffer_diseases": len(buffers), "hidden_diseases_total": len(hidden), "clean_training_pairs_remaining": len(clean) - hidden_clean, "clean_training_fraction_remaining": (len(clean) - hidden_clean) / len(clean), "therapeutic_training_pairs_remaining": len(pair_roles) - hidden_ther, "therapeutic_training_fraction_remaining": (len(pair_roles) - hidden_ther) / len(pair_roles), "direct_ontology_leaks": leaks})
    quarantine = pd.DataFrame(quarantine_rows)
    fold_summary = pd.DataFrame(fold_rows)

    frames = {OUTPUTS[0]: candidate, OUTPUTS[1]: primary_diseases, OUTPUTS[2]: primary_roles, OUTPUTS[3]: primary_truth, OUTPUTS[4]: quarantine, OUTPUTS[5]: fold_summary}
    for filename, frame in frames.items():
        frame.to_csv(output_dir / filename, index=False, lineterminator="\n")
    historical_base = "/content/drive/MyDrive/P1/PrimeKG"
    # Cell 12 policy is a scientifically relevant Cell-13 dependency.
    metric_policy = {"candidate_universe": "all_7957_primekg_drugbank_drugs", "primary_positive": "CLEAN_INDICATION", "ignored_primary_roles": ["AMBIGUOUS_INDICATION", "OFFLABEL_ONLY", "CONFLICTING_NONINDICATION"], "scored_but_not_true_negative_roles": ["CONTRAINDICATION_ONLY", "UNOBSERVED"], "primary_metrics": ["Recall@K", "Hit@K", "MRR", "first_hit_rank"], "safety_metric_family": ["Contraindication@K", "contraindication_intrusion_rate"], "secondary_diagnostic_metrics": ["AUPRC", "AUROC"], "important_note": "Unobserved pairs are unlabeled, not true negatives. Contraindications remain rankable candidates but are tracked separately as explicit safety evidence."}
    policy_path = output_dir / "p1_primary_metric_policy.json"
    with policy_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metric_policy, indent=2))
    hashes = {"primekg_kg_csv": {"path": f"{historical_base}/kg.csv", "bytes": raw_path.stat().st_size, "sha256": sha256_file(raw_path)}}
    for key, filename in zip(("candidate_drugs", "primary_diseases", "primary_eval_roles", "primary_truth", "quarantine_manifest", "fold_summary"), OUTPUTS[:6]):
        path = output_dir / filename
        hashes[key] = {"path": f"{historical_base}/{filename}", "bytes": path.stat().st_size, "sha256": sha256_file(path)}
    hashes["metric_policy"] = {"path": f"{historical_base}/p1_primary_metric_policy.json", "bytes": policy_path.stat().st_size, "sha256": sha256_file(policy_path)}
    manifest = {"benchmark_id": "P1_TRACK_A_PRIMEKG_V0", "benchmark_version": "0.0", "status": "FROZEN", "track": "A_controlled_information_parity", "graph": {"dataset": "PrimeKG", "canonical_file": f"{historical_base}/kg.csv", "directed_edge_records": directed, "drug_nodes": len(nodes["drug"]), "disease_nodes": len(nodes["disease"]), "gene_protein_nodes": len(nodes["gene/protein"])}, "task": {"name": "disease_cold_start_indication_ranking", "primary_scientific_unit": "disease", "candidate_universe": "all_PrimeKG_DrugBank_drug_nodes", "candidate_count": len(candidate), "disease_eligibility": "at_least_3_CLEAN_INDICATION_pairs", "primary_disease_count": len(primary_diseases), "primary_clean_truth_pairs": len(primary_truth)}, "label_policy": {"primary_positive": "CLEAN_INDICATION", "ignored_primary_roles": sorted(["AMBIGUOUS_INDICATION", "OFFLABEL_ONLY", "CONFLICTING_NONINDICATION"]), "rankable_not_true_negative": ["CONTRAINDICATION_ONLY", "UNOBSERVED"], "primary_cohort_role_counts": {str(k): int(v) for k, v in primary_roles["evaluation_role"].value_counts().items()}, "unobserved_semantics": "UNOBSERVED means unlabeled, not true negative."}, "oof_protocol": {"k": 8, "seed": 42, "target_assignment": "deterministic stratified disease-level OOF", "quarantine_rule": "For every evaluation disease, hide all therapeutic relations for the target disease and all direct disease_disease ontology neighbors that possess any indication annotation.", "preserved_information": "All non-therapeutic PrimeKG evidence remains available.", "direct_ontology_leakage": int(fold_summary["direct_ontology_leaks"].sum())}, "primary_metrics": ["Recall@K", "Hit@K", "MRR", "first_hit_rank"], "safety_metrics": ["Contraindication@K", "contraindication_intrusion_rate"], "secondary_diagnostics": ["AUPRC", "AUROC"], "important_metric_semantics": {"unobserved_are_not_negatives": True, "contraindications_are_not_generic_negatives": True, "macro_average_over_diseases": True}, "artifacts": hashes, "software_environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__}}
    with (output_dir / OUTPUTS[6]).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2))
    retained_nodes = nonther_nodes | {("drug", str(x)) for x in candidate["drug_id"]} | {("disease", str(x)) for x in primary_diseases["disease_id"]} | {("drug", str(x)) for x in clean["drug_id"]} | {("disease", str(x)) for x in clean["disease_id"]}
    return {"census": {"directed_rows": directed, "reciprocal_conceptual_relations": directed // 2, "entities": len(retained_nodes), "raw_typed_entity_keys": sum(map(len, nodes.values())), "raw_untyped_entity_ids": len(set().union(*nodes.values())), "nodes_by_type": {kind: len(ids) for kind, ids in nodes.items()}, "relation_counts": dict(relation_counts), "retained_nontherapeutic_relation_types": len(set(relation_counts) - THERAPEUTIC)}, "therapeutic_directed_rows": {rel: relation_counts[rel] for rel in THERAPEUTIC}, "therapeutic_canonical_pairs": {str(k): int(v) for k, v in therapeutic["relation"].value_counts().items()}, "global_role_counts": role_counts, "candidate_universes": universes, "primary_diseases": len(primary_diseases), "primary_truth": len(primary_truth), "fold_sizes": [int(x) for x in fold_summary["target_diseases"]], "buffer_sizes": [int(x) for x in fold_summary["buffer_diseases"]], "legal_clean_counts": [int(x) for x in fold_summary["clean_training_pairs_remaining"]], "tested_direct_ontology_edges": raw_exposures, "surviving_direct_ontology_edges": int(fold_summary["direct_ontology_leaks"].sum())}


def compare_artifacts(output_dir: Path, frozen_root: Path, registry_path: Path) -> list[dict]:
    """Report science and bytes independently, including first ordered mismatch."""
    registry = load_registry(registry_path)
    by_path = {x.get("logical_path"): x for x in registry["artifacts"]}
    reports = []
    for filename in OUTPUTS:
        logical = f"benchmark/{filename}"
        expected = by_path[logical]
        generated = output_dir / filename
        frozen = frozen_root / logical
        if sha256_file(frozen) != expected["expected_sha256"]:
            raise ValueError(f"Gate-1 frozen hash mismatch: {logical}")
        observed_hash = sha256_file(generated)
        item = {"artifact": filename, "expected_sha256": expected["expected_sha256"], "generated_sha256": observed_hash, "hash_equivalence": observed_hash == expected["expected_sha256"]}
        if filename.endswith(".csv"):
            with frozen.open(newline="", encoding="utf-8") as handle:
                baseline_reader = csv.DictReader(handle)
                baseline_schema = baseline_reader.fieldnames
                baseline = list(baseline_reader)
            with generated.open(newline="", encoding="utf-8") as handle:
                generated_reader = csv.DictReader(handle)
                generated_schema = generated_reader.fieldnames
                actual = list(generated_reader)
            item.update({"expected_rows": len(baseline), "generated_rows": len(actual), "schema_match": baseline_schema == generated_schema})
            keys = KEYS[filename]
            item["ordered_keys_match"] = [tuple(row[k] for k in keys) for row in baseline] == [tuple(row[k] for k in keys) for row in actual]
            first = next((i for i, (left, right) in enumerate(zip(baseline, actual)) if left != right), None)
            if first is None and len(baseline) != len(actual):
                first = min(len(baseline), len(actual))
            item["first_ordered_mismatch"] = None if first is None else {"row": first, "expected": baseline[first] if first < len(baseline) else None, "generated": actual[first] if first < len(actual) else None}
            # Compare records by scientific key, independent of row order; CSV
            # text values are exact except float formatting in fold fractions.
            if filename == OUTPUTS[5]:
                for rows in (baseline, actual):
                    for row in rows:
                        for field in ("clean_training_fraction_remaining", "therapeutic_training_fraction_remaining"):
                            row[field] = round(float(row[field]), 14)
            by_key = lambda rows: {tuple(row[k] for k in keys): row for row in rows}
            item["unordered_content_equivalence"] = baseline_schema == generated_schema and len(baseline) == len(actual) and by_key(baseline) == by_key(actual)
            item["semantic_equivalence"] = item["unordered_content_equivalence"] and item["ordered_keys_match"]
            item["classification"] = "EXACT" if item["hash_equivalence"] else "SERIALIZATION_ONLY_DIFFERENCE" if item["semantic_equivalence"] else "SCIENTIFIC_DIFFERENCE"
        else:
            baseline = json.loads(frozen.read_text(encoding="utf-8"))
            actual = json.loads(generated.read_text(encoding="utf-8"))
            scientific_fields = ["benchmark_id", "benchmark_version", "status", "track", "graph", "task", "label_policy", "oof_protocol", "primary_metrics", "safety_metrics", "secondary_diagnostics", "important_metric_semantics"]
            item["scientific_field_matches"] = {field: baseline[field] == actual.get(field) for field in scientific_fields}
            item["semantic_equivalence"] = all(item["scientific_field_matches"].values())
            item["provenance_differences"] = {field: {"expected": baseline["artifacts"].get(field), "generated": actual["artifacts"].get(field)} for field in baseline["artifacts"] if baseline["artifacts"].get(field) != actual["artifacts"].get(field)}
            if baseline["software_environment"] != actual["software_environment"]:
                item["provenance_differences"]["software_environment"] = {"expected": baseline["software_environment"], "generated": actual["software_environment"]}
            normalized = dict(actual)
            normalized["software_environment"] = baseline["software_environment"]
            item["historical_environment_normalized_hash_equivalence"] = hashlib.sha256(json.dumps(normalized, indent=2).encode("utf-8")).hexdigest() == expected["expected_sha256"]
            item["classification"] = "EXACT" if item["hash_equivalence"] else "ENVIRONMENT_METADATA_ONLY_DIFFERENCE" if item["semantic_equivalence"] and item["historical_environment_normalized_hash_equivalence"] else "PROVENANCE_OR_SERIALIZATION_DIFFERENCE" if item["semantic_equivalence"] else "SCIENTIFIC_DIFFERENCE"
        reports.append(item)
    policy_registry = by_path["recovered_contracts/p1_primary_metric_policy.json"]
    expected_policy = frozen_root / "recovered_contracts/p1_primary_metric_policy.json"
    actual_policy = output_dir / "p1_primary_metric_policy.json"
    if sha256_file(expected_policy) != policy_registry["expected_sha256"]:
        raise ValueError("Gate-1 frozen metric-policy hash mismatch")
    policy_exact = sha256_file(actual_policy) == policy_registry["expected_sha256"]
    policy_semantic = json.loads(actual_policy.read_text(encoding="utf-8")) == json.loads(expected_policy.read_text(encoding="utf-8"))
    reports.append({"artifact": "p1_primary_metric_policy.json", "expected_sha256": policy_registry["expected_sha256"], "generated_sha256": sha256_file(actual_policy), "hash_equivalence": policy_exact, "semantic_equivalence": policy_semantic, "classification": "EXACT" if policy_exact else "SERIALIZATION_ONLY_DIFFERENCE" if policy_semantic else "SCIENTIFIC_DIFFERENCE"})
    return reports


def validate_reconstruction_counts(observed: dict, registry_path: Path, frozen_root: Path) -> list[dict]:
    """Check stage counts against Gate-1 contracts and verified historical census."""
    registry = load_registry(registry_path)
    contract = registry["benchmark"]
    census_item = next(x for x in registry["artifacts"] if x.get("logical_path") == "benchmark/primekg_graph_census.json")
    census_path = frozen_root / census_item["logical_path"]
    if sha256_file(census_path) != census_item["expected_sha256"]:
        raise ValueError("Gate-1 frozen graph census hash mismatch")
    census = json.loads(census_path.read_text(encoding="utf-8"))
    checks = [
        ("directed_rows", contract["raw_edge_rows"], observed["census"]["directed_rows"]),
        ("reciprocal_conceptual_relations", contract["raw_edge_rows"] // 2, observed["census"]["reciprocal_conceptual_relations"]),
        ("entities", contract["e3_entities"], observed["census"]["entities"]),
        ("relation_counts", census["relation_counts"], observed["census"]["relation_counts"]),
        ("nodes_by_type", census["unique_nodes_by_type"], observed["census"]["nodes_by_type"]),
        ("nontherapeutic_relation_types", 27, observed["census"]["retained_nontherapeutic_relation_types"]),
        ("global_clean_pairs", contract["global_clean_pairs"], observed["global_role_counts"]["CLEAN_INDICATION"]),
        ("candidate_U0", contract["candidate_count"], observed["candidate_universes"]["U0"]),
        ("candidate_U1", 7828, observed["candidate_universes"]["U1"]),
        ("candidate_U2", 6282, observed["candidate_universes"]["U2"]),
        ("primary_diseases", contract["primary_disease_count"], observed["primary_diseases"]),
        ("primary_truth", contract["primary_clean_truth_pairs"], observed["primary_truth"]),
        ("fold_sizes", [93, 93, 92, 92, 92, 92, 92, 92], observed["fold_sizes"]),
        ("legal_clean_counts", contract["fold_clean_counts"], observed["legal_clean_counts"]),
        ("direct_ontology_leaks", 0, observed["surviving_direct_ontology_edges"]),
    ]
    expected_therapeutic = {rel: census["relation_counts"][rel] for rel in THERAPEUTIC}
    checks.append(("therapeutic_directed_rows", expected_therapeutic, observed["therapeutic_directed_rows"]))
    checks.append(("therapeutic_canonical_pairs", {rel: count // 2 for rel, count in expected_therapeutic.items()}, observed["therapeutic_canonical_pairs"]))
    for role, count in {"CLEAN_INDICATION": 9177, "CONTRAINDICATION_ONLY": 30552, "OFFLABEL_ONLY": 2407, "AMBIGUOUS_INDICATION": 211, "CONFLICTING_NONINDICATION": 36}.items():
        checks.append((f"role_{role}", count, observed["global_role_counts"].get(role)))
    return [{"field": field, "expected": expected, "observed": actual, "pass": expected == actual} for field, expected, actual in checks]
