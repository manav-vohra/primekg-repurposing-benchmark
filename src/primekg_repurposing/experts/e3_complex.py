"""Exact pre-training contract for the historical P1 E3 ComplEx expert.

This module deliberately contains validation and small deterministic helpers,
not a command that launches the canonical 8-fold training experiment.
"""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:  # pragma: no cover - exercised by minimal installs
    torch = None
    nn = None


COMPLEX_DIM = 64
N_ENTITIES = 129_307
N_RELATIONS = 28
CLEAN_RELATION = "clean_indication"
THERAPEUTIC_RELATIONS = frozenset({"indication", "contraindication", "off-label use"})
EXPECTED_FOLD_COUNTS = (6856, 6828, 6990, 7119, 6871, 7183, 7091, 6827)
CORPUS_MANIFEST_SHA256 = "36e7d2f620b25056bb5564d589e4a396c2a7fe591600c6af2cd122127145ceb8"

STAGE_A = {
    "epochs": 2, "batch_size": 131_072, "negatives_per_positive": 1,
    "entity_optimizer": "SparseAdam", "entity_lr": 0.01,
    "relation_optimizer": "Adam", "relation_lr": 0.01,
    "loss": "mean(softplus(-positive)) + mean(softplus(negative))",
    "corruption": "one endpoint, 50/50 head/tail, replacement from base-active same-type pool, original excluded when pool size > 1",
    "relation_gradient_clip_norm": 5.0, "entity_gradient_clipping": False,
}
STAGE_B = {
    "epochs": 80, "positive_batch_size": 2048, "drug_head_corruptions_per_positive": 16,
    "entity_optimizer": "SparseAdam", "entity_lr": 0.002,
    "relation_optimizer": "Adam", "relation_lr": 0.01,
    "loss": "mean(softplus(-positive)) + mean(softplus(negative))",
    "corruption": "candidate drug head only; reject every legal CLEAN head for the same disease",
    "negative_semantics": "optimization contrasts only; not biological negatives or benchmark labels",
    "fold_rng_seed": "10000 + seed*100 + fold", "early_stopping": False,
    "validation_tuning": False, "relation_gradient_clip_norm": 5.0,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


if nn is not None:
    class ComplExModel(nn.Module):
        """Historical Cell-20/21 state layout and score equation."""

        def __init__(self, n_entities: int, n_relations: int, dim: int = COMPLEX_DIM):
            super().__init__()
            self.dim = int(dim)
            self.entity_re = nn.Embedding(n_entities, dim, sparse=True)
            self.entity_im = nn.Embedding(n_entities, dim, sparse=True)
            self.relation_re = nn.Embedding(n_relations, dim, sparse=False)
            self.relation_im = nn.Embedding(n_relations, dim, sparse=False)
            bound = 1.0 / math.sqrt(dim)
            for embedding in (self.entity_re, self.entity_im, self.relation_re, self.relation_im):
                nn.init.uniform_(embedding.weight, -bound, bound)

        def score(self, h: Any, r: Any, t: Any) -> Any:
            hr, hi = self.entity_re(h), self.entity_im(h)
            rr, ri = self.relation_re(r), self.relation_im(r)
            tr, ti = self.entity_re(t), self.entity_im(t)
            return (hr * rr * tr + hi * rr * ti + hr * ri * ti - hi * ri * tr).sum(dim=-1)
else:
    class ComplExModel:  # type: ignore[no-redef]
        def __init__(self, *_: Any, **__: Any):
            raise RuntimeError("PyTorch is required for E3 checkpoint validation")


def historical_reference_score(state: dict[str, Any], h: Any, r: Any, t: Any) -> Any:
    """Independent transcription of Cells 20/21; never calls ``ComplExModel.score``."""
    if torch is None:
        raise RuntimeError("PyTorch is required")
    hr, hi = state["entity_re.weight"][h], state["entity_im.weight"][h]
    rr, ri = state["relation_re.weight"][r], state["relation_im.weight"][r]
    tr, ti = state["entity_re.weight"][t], state["entity_im.weight"][t]
    return torch.sum(hr * rr * tr + hi * rr * ti + hr * ri * ti - hi * ri * tr, dim=-1)


def sample_same_type(original: np.ndarray, entity_type_codes: np.ndarray,
                     pools: dict[int, np.ndarray], rng: np.random.Generator) -> np.ndarray:
    original = np.asarray(original, dtype=np.int32)
    result = np.empty_like(original)
    for code in np.unique(entity_type_codes[original]):
        rows = np.flatnonzero(entity_type_codes[original] == code)
        pool = pools[int(code)]
        choices = pool[rng.integers(0, len(pool), size=len(rows))]
        if len(pool) > 1:
            bad = choices == original[rows]
            while bad.any():
                choices[bad] = pool[rng.integers(0, len(pool), size=int(bad.sum()))]
                bad = choices == original[rows]
        result[rows] = choices
    return result


def sample_clean_head_corruptions(positive_tails: np.ndarray, candidate_indices: np.ndarray,
                                  forbidden_by_tail: dict[int, np.ndarray], rng: np.random.Generator,
                                  count: int = 16) -> np.ndarray:
    """Historical optimization contrasts; outputs carry no biological-negative meaning."""
    tails = np.asarray(positive_tails, dtype=np.int32)
    candidates = np.asarray(candidate_indices, dtype=np.int32)
    negatives = candidates[rng.integers(0, len(candidates), size=(len(tails), count))].astype(np.int32, copy=False)
    for tail in np.unique(tails):
        rows = np.flatnonzero(tails == tail)
        forbidden = forbidden_by_tail[int(tail)]
        block = negatives[rows]
        bad = np.isin(block, forbidden)
        while bad.any():
            block[bad] = candidates[rng.integers(0, len(candidates), size=int(bad.sum()))]
            bad = np.isin(block, forbidden)
        negatives[rows] = block
    return negatives


def validate_frozen_corpus(frozen_root: Path, recovered_root: Path, benchmark: Any) -> dict[str, Any]:
    manifest = frozen_root / "benchmark/p1_e3_complex_corpus_manifest.json"
    entities_path = frozen_root / "benchmark/p1_e3_complex_entities.csv"
    relations_path = frozen_root / "benchmark/p1_e3_complex_relations.csv"
    fold_path = frozen_root / "recovered_contracts/p1_e3_complex_fold_label_manifest.csv"
    entities, relations = read_csv_rows(entities_path), read_csv_rows(relations_path)
    entity_keys = [row["entity_key"] for row in entities]
    relation_names = [row["relation_name"] for row in relations]
    masks = [benchmark.mask(fold) for fold in range(8)]
    fold_counts = [len(mask.legal_clean_pairs) for mask in masks]
    hidden_leaks = [sum(p.disease_id in mask.hidden_ids for p in mask.legal_clean_pairs) for mask in masks]
    long_ids = [p.disease_id for p in benchmark.role_pairs if p.role.value == "CLEAN_INDICATION" and len(p.disease_id) > 128]
    base_path = recovered_root / "p1_e3_complex_base_nonther_triples.npz"
    clean_path = recovered_root / "p1_e3_complex_clean_indication_triples.npz"
    with np.load(base_path, allow_pickle=False) as base:
        base_schema = {k: {"shape": list(base[k].shape), "dtype": str(base[k].dtype)} for k in base.files}
        base_count = int(len(base["head"]))
    with np.load(clean_path, allow_pickle=False) as clean:
        clean_schema = {k: {"shape": list(clean[k].shape), "dtype": str(clean[k].dtype)} for k in clean.files}
        clean_ids = clean["disease_ids"].astype(str).tolist()
        candidate_indices = clean["candidate_entity_indices"]
        disease_indices = clean["primary_disease_entity_indices"]
    checks = {
        "manifest_sha256": sha256_file(manifest) == CORPUS_MANIFEST_SHA256,
        "entity_count": len(entities) == N_ENTITIES,
        "entity_lexical_order": entity_keys == sorted(entity_keys),
        "relation_count": len(relations) == N_RELATIONS,
        "relation_lexical_order": relation_names == sorted(relation_names),
        "therapeutic_relations_absent": THERAPEUTIC_RELATIONS.isdisjoint(relation_names),
        "clean_relation_index": relation_names.index(CLEAN_RELATION) == 7,
        "base_triple_count": base_count == 8_015_236,
        "fold_legal_counts": tuple(fold_counts) == EXPECTED_FOLD_COUNTS,
        "hidden_label_leaks": hidden_leaks == [0] * 8,
        "long_id_count": len(long_ids) == 25,
        "long_ids_complete": set(long_ids).issubset(set(clean_ids)) and max(map(len, clean_ids)) == 523,
        "candidate_axis_size": candidate_indices.shape == (7957,),
        "disease_axis_size": disease_indices.shape == (738,),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
        "entities": len(entities), "relations": len(relations), "base_triples": base_count,
        "global_clean_pairs": len(clean_ids), "fold_legal_counts": fold_counts,
        "entity_sha256": sha256_file(entities_path), "relation_sha256": sha256_file(relations_path),
        "fold_manifest_sha256": sha256_file(fold_path), "base_sha256": sha256_file(base_path),
        "clean_sha256": sha256_file(clean_path), "base_schema": base_schema, "clean_schema": clean_schema,
        "representation": "directed source rows in original order; duplicates preserved; no inverse relations or normalization",
    }


def validate_checkpoint(path: Path, seed: int) -> dict[str, Any]:
    if torch is None:
        raise RuntimeError("PyTorch is required")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if int(payload["seed"]) != seed:
        raise ValueError(f"checkpoint seed {payload['seed']} does not match expected seed {seed}")
    if int(payload["complex_dim"]) != COMPLEX_DIM:
        raise ValueError("wrong checkpoint dimension")
    if payload["corpus_manifest_sha256"] != CORPUS_MANIFEST_SHA256:
        raise ValueError("wrong corpus/entity/relation mapping identity")
    state = payload["state_dict"]
    expected = {
        "entity_re.weight": (N_ENTITIES, COMPLEX_DIM), "entity_im.weight": (N_ENTITIES, COMPLEX_DIM),
        "relation_re.weight": (N_RELATIONS, COMPLEX_DIM), "relation_im.weight": (N_RELATIONS, COMPLEX_DIM),
    }
    if set(state) != set(expected):
        raise ValueError("unexpected checkpoint tensor names")
    for name, shape in expected.items():
        if tuple(state[name].shape) != shape or state[name].dtype != torch.float32:
            raise ValueError(f"wrong tensor contract for {name}")
    model = ComplExModel(N_ENTITIES, N_RELATIONS, COMPLEX_DIM)
    incompatible = model.load_state_dict(state, strict=True)
    h = torch.tensor([0, 1, 64_653, 129_306], dtype=torch.long)
    r = torch.tensor([0, 7, 14, 27], dtype=torch.long)
    t = torch.tensor([129_306, 64_653, 1, 0], dtype=torch.long)
    with torch.no_grad():
        clean = model.score(h, r, t)
        reference = historical_reference_score(state, h, r, t)
    difference = torch.abs(clean - reference)
    return {
        "seed": seed, "path": str(path), "size": path.stat().st_size,
        "sha256": sha256_file(path), "hash_classification": "RECOVERY_TIME_OBSERVED",
        "container": "PyTorch ZIP checkpoint", "payload_keys": sorted(payload),
        "state_dict_keys": sorted(state),
        "tensors": {k: {"shape": list(v.shape), "dtype": str(v.dtype)} for k, v in state.items()},
        "strict_load": not incompatible.missing_keys and not incompatible.unexpected_keys,
        "probe_finite": bool(torch.isfinite(clean).all()), "probe_bitwise_equal": bool(torch.equal(clean, reference)),
        "probe_max_abs_difference": float(difference.max()),
    }


def validate_score_archive(path: Path, seed: int, disease_ids: Iterable[str], candidate_ids: Iterable[str]) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != {"scores", "disease_ids", "drug_ids"}:
            raise ValueError("wrong score archive schema")
        scores = archive["scores"]
        disease_ok = np.array_equal(archive["disease_ids"].astype(str), np.asarray(tuple(disease_ids), dtype=str))
        candidate_ok = np.array_equal(archive["drug_ids"].astype(str), np.asarray(tuple(candidate_ids), dtype=str))
    return {
        "seed": seed, "path": str(path), "size": path.stat().st_size, "sha256": sha256_file(path),
        "hash_classification": "RECOVERY_TIME_OBSERVED", "schema": ["scores", "disease_ids", "drug_ids"],
        "shape": list(scores.shape), "dtype": str(scores.dtype), "disease_axis_verified": bool(disease_ok),
        "candidate_axis_verified": bool(candidate_ok),
        "status": "PASS" if scores.shape == (738, 7957) and scores.dtype == np.float32 and disease_ok and candidate_ok else "FAIL",
    }


def scan_raw_corpus(raw_kg: Path) -> dict[str, Any]:
    """Stream the Cell-19B pass-1 semantics without materializing 8M triples."""
    import pandas as pd
    entity_keys: set[str] = set()
    relations: Counter[str] = Counter()
    kept = removed = 0
    for chunk in pd.read_csv(raw_kg, usecols=["relation", "x_id", "x_type", "y_id", "y_type"], dtype=str, chunksize=500_000):
        therapeutic = chunk["relation"].isin(THERAPEUTIC_RELATIONS)
        removed += int(therapeutic.sum())
        nonther = chunk.loc[~therapeutic]
        kept += len(nonther)
        relations.update(nonther["relation"].tolist())
        entity_keys.update((nonther["x_type"] + "::" + nonther["x_id"]).tolist())
        entity_keys.update((nonther["y_type"] + "::" + nonther["y_id"]).tolist())
    return {"nontherapeutic_directed_triples": kept, "therapeutic_rows_removed": removed,
            "base_entity_keys": entity_keys, "relation_counts": dict(relations)}
