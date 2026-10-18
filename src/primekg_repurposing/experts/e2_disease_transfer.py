"""Cell-17-equivalent fold-legal disease-profile label transfer expert."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..benchmark import FrozenBenchmark, LabelState, MaskingProtocol
from ..evaluation import ExpertScoreResult


EXPERT_ID = "E2_DISEASE_PROFILE_LABEL_TRANSFER"
EXPERT_VERSION = "1.0"
EXPERT_FAMILY = "nonparametric_label_transfer"
THERAPEUTIC_RELATIONS = frozenset({"indication", "contraindication", "off-label use"})
NO_PROFILE = "ABSTAIN_NO_NONTHERAPEUTIC_PROFILE"
NO_SIMILAR = "ABSTAIN_NO_SIMILAR_TRAINING_DISEASE"
NO_TRANSFER = "ABSTAIN_NO_TRANSFERABLE_INDICATION"


@dataclass(frozen=True)
class DiseaseFeatureCorpus:
    pairs: frozenset[tuple[str, str]]
    disease_ids: tuple[str, ...]
    feature_ids: tuple[str, ...]
    relation_types: tuple[str, ...]


@dataclass(frozen=True)
class TfidfProfiles:
    relevant_disease_ids: tuple[str, ...]
    feature_ids: tuple[str, ...]
    idf: object
    matrix: object
    raw_feature_counts: tuple[int, ...]
    all_disease_count: int


@dataclass(frozen=True)
class E2Prepared:
    candidate_ids: tuple[str, ...]
    disease_ids: tuple[str, ...]
    disease_folds: tuple[int, ...]
    label_disease_ids: tuple[str, ...]
    global_clean_pairs: frozenset[tuple[str, str]]
    label_matrix: object
    profiles: TfidfProfiles
    query_profiles: object
    label_profiles: object
    similarity: object
    query_feature_counts: tuple[int, ...]
    relation_types: tuple[str, ...]
    feature_pair_count: int
    runtime_seconds: Mapping[str, float]


@dataclass(frozen=True)
class E2RunResult:
    expert_id: str
    expert_version: str
    expert_family: str
    benchmark_id: str
    masking_protocol: str
    candidate_ids: tuple[str, ...]
    disease_ids: tuple[str, ...]
    scores: object
    applicable: tuple[bool, ...]
    abstention_reasons: tuple[str | None, ...]
    deterministic: bool
    stochastic: bool
    seed: None
    statuses: tuple[str, ...]
    fold_legal_clean_counts: tuple[int, ...]
    metadata: Mapping[str, object]

    def disease_result(self, row: int) -> ExpertScoreResult:
        return ExpertScoreResult(
            expert_id=self.expert_id,
            expert_version=self.expert_version,
            disease_id=self.disease_ids[row],
            candidate_ids=self.candidate_ids,
            scores=self.scores[row],
            applicable=self.applicable[row],
            abstention_reason=self.abstention_reasons[row],
            seed=None,
            provenance="historical Cell 17; clean deterministic implementation",
            benchmark_id=self.benchmark_id,
            deterministic=True,
            metadata=self.metadata,
        )


def _edge_values(edge) -> tuple[str, str, str, str, str]:
    if isinstance(edge, Mapping):
        values = (edge["relation"], edge["x_id"], edge["x_type"], edge["y_id"], edge["y_type"])
    else:
        if len(edge) != 5:
            raise ValueError("edge must have relation, x_id, x_type, y_id, y_type")
        values = tuple(edge)
    return tuple(str(value) for value in values)  # type: ignore[return-value]


def feature_token(relation: str, neighbor_type: str, neighbor_id: str) -> str:
    return f"{relation}|{neighbor_type}|{neighbor_id}"


def build_disease_feature_corpus(edges: Iterable[object]) -> DiseaseFeatureCorpus:
    """Cell 17: binary features from every incident nontherapeutic edge."""
    pairs: set[tuple[str, str]] = set()
    diseases: set[str] = set()
    relations: set[str] = set()
    for edge in edges:
        relation, x_id, x_type, y_id, y_type = _edge_values(edge)
        if relation in THERAPEUTIC_RELATIONS:
            continue
        if x_type == "disease":
            diseases.add(x_id)
            relations.add(relation)
            pairs.add((x_id, feature_token(relation, y_type, y_id)))
        if y_type == "disease":
            diseases.add(y_id)
            relations.add(relation)
            pairs.add((y_id, feature_token(relation, x_type, x_id)))
    features = tuple(sorted({feature for _, feature in pairs}))
    return DiseaseFeatureCorpus(
        pairs=frozenset(pairs), disease_ids=tuple(sorted(diseases)),
        feature_ids=features, relation_types=tuple(sorted(relations)),
    )


def extract_disease_feature_corpus(raw_kg: Path, *, chunksize: int = 500_000) -> DiseaseFeatureCorpus:
    import pandas as pd

    def selected_edges():
        usecols = ["relation", "x_id", "x_type", "y_id", "y_type"]
        for chunk in pd.read_csv(
            raw_kg, usecols=usecols, chunksize=chunksize, low_memory=False, dtype="string"
        ):
            nontherapeutic = chunk.loc[~chunk["relation"].isin(THERAPEUTIC_RELATIONS), usecols]
            yield from nontherapeutic.loc[
                (nontherapeutic["x_type"] == "disease") | (nontherapeutic["y_type"] == "disease")
            ].itertuples(index=False, name=None)

    return build_disease_feature_corpus(selected_edges())


def build_tfidf_profiles(corpus: DiseaseFeatureCorpus, relevant_disease_ids: Sequence[str]) -> TfidfProfiles:
    """Build Cell 17's binary, smoothed-natural-log, L2-normalized CSR matrix."""
    import numpy as np
    from scipy.sparse import csr_matrix, diags

    relevant = tuple(sorted(str(value) for value in relevant_disease_ids))
    if len(relevant) != len(set(relevant)):
        raise ValueError("relevant disease IDs must be unique")
    feature_index = {feature: index for index, feature in enumerate(corpus.feature_ids)}
    relevant_index = {disease: index for index, disease in enumerate(relevant)}
    relevant_set = set(relevant)
    feature_df = np.zeros(len(corpus.feature_ids), dtype=np.int32)
    for _disease, feature in corpus.pairs:
        feature_df[feature_index[feature]] += 1
    idf = (
        np.log((1.0 + len(corpus.disease_ids)) / (1.0 + feature_df)) + 1.0
    ).astype(np.float32)
    rows: list[int] = []
    cols: list[int] = []
    values: list[object] = []
    for disease, feature in corpus.pairs:
        if disease not in relevant_set:
            continue
        column = feature_index[feature]
        rows.append(relevant_index[disease])
        cols.append(column)
        values.append(idf[column])
    tfidf = csr_matrix(
        (np.asarray(values, dtype=np.float32), (rows, cols)),
        shape=(len(relevant), len(corpus.feature_ids)), dtype=np.float32,
    )
    row_sq_sum = np.asarray(tfidf.multiply(tfidf).sum(axis=1)).reshape(-1)
    row_norm = np.sqrt(row_sq_sum)
    inverse_norm = np.zeros_like(row_norm, dtype=np.float32)
    nonzero = row_norm > 0
    inverse_norm[nonzero] = 1.0 / row_norm[nonzero]
    normalized = (diags(inverse_norm) @ tfidf).tocsr()
    return TfidfProfiles(
        relevant_disease_ids=relevant,
        feature_ids=corpus.feature_ids,
        idf=idf,
        matrix=normalized,
        raw_feature_counts=tuple(int(value) for value in np.diff(tfidf.indptr)),
        all_disease_count=len(corpus.disease_ids),
    )


def build_global_clean_labels(benchmark: FrozenBenchmark):
    import numpy as np
    from scipy.sparse import csr_matrix

    candidate_index = {drug: index for index, drug in enumerate(benchmark.candidate_ids)}
    pairs = frozenset(
        (pair.disease_id, pair.drug_id)
        for pair in benchmark.role_pairs
        if pair.role is LabelState.CLEAN_INDICATION and pair.drug_id in candidate_index
    )
    label_diseases = tuple(sorted({disease for disease, _ in pairs}))
    disease_index = {disease: index for index, disease in enumerate(label_diseases)}
    rows, cols = [], []
    for disease, drug in pairs:
        rows.append(disease_index[disease])
        cols.append(candidate_index[drug])
    matrix = csr_matrix(
        (np.ones(len(rows), dtype=np.float32), (rows, cols)),
        shape=(len(label_diseases), len(benchmark.candidate_ids)), dtype=np.float32,
    )
    if matrix.nnz != len(pairs):
        raise ValueError("global CLEAN label matrix lost pair identity")
    return label_diseases, pairs, matrix


def prepare_e2_from_corpus(corpus: DiseaseFeatureCorpus, benchmark: FrozenBenchmark) -> E2Prepared:
    import numpy as np

    if benchmark.protocol is not MaskingProtocol.CANONICAL_1HOP:
        raise ValueError("E2 primary implementation requires CANONICAL_1HOP")
    start = time.perf_counter()
    label_diseases, clean_pairs, label_matrix = build_global_clean_labels(benchmark)
    primary_ids = tuple(disease for disease, _fold in benchmark.disease_folds)
    relevant = tuple(sorted(set(primary_ids) | set(label_diseases)))
    profiles = build_tfidf_profiles(corpus, relevant)
    relevant_index = {disease: index for index, disease in enumerate(profiles.relevant_disease_ids)}
    primary_rows = np.asarray([relevant_index[disease] for disease in primary_ids], dtype=int)
    label_rows = np.asarray([relevant_index[disease] for disease in label_diseases], dtype=int)
    query_profiles = profiles.matrix[primary_rows]
    label_profiles = profiles.matrix[label_rows]
    profile_end = time.perf_counter()
    similarity = (query_profiles @ label_profiles.T).tocsr()
    similarity_end = time.perf_counter()
    return E2Prepared(
        candidate_ids=benchmark.candidate_ids,
        disease_ids=primary_ids,
        disease_folds=tuple(fold for _disease, fold in benchmark.disease_folds),
        label_disease_ids=label_diseases,
        global_clean_pairs=clean_pairs,
        label_matrix=label_matrix,
        profiles=profiles,
        query_profiles=query_profiles,
        label_profiles=label_profiles,
        similarity=similarity,
        query_feature_counts=tuple(int(value) for value in np.diff(query_profiles.indptr)),
        relation_types=corpus.relation_types,
        feature_pair_count=len(corpus.pairs),
        runtime_seconds={
            "profile_preparation": profile_end - start,
            "similarity": similarity_end - profile_end,
        },
    )


def prepare_e2(raw_kg: Path, benchmark: FrozenBenchmark) -> E2Prepared:
    start = time.perf_counter()
    corpus = extract_disease_feature_corpus(raw_kg)
    extraction_end = time.perf_counter()
    prepared = prepare_e2_from_corpus(corpus, benchmark)
    runtime = dict(prepared.runtime_seconds)
    runtime["graph_profile_extraction"] = extraction_end - start
    runtime["total_preparation"] = time.perf_counter() - start
    return E2Prepared(**{**prepared.__dict__, "runtime_seconds": runtime})


def score_e2_prepared(prepared: E2Prepared, benchmark: FrozenBenchmark) -> E2RunResult:
    """Score fold by fold, consuming the Gate-2 benchmark mask API."""
    import numpy as np

    if tuple(d for d, _ in benchmark.disease_folds) != prepared.disease_ids:
        raise ValueError("benchmark disease axis differs from prepared E2 axis")
    if benchmark.candidate_ids != prepared.candidate_ids:
        raise ValueError("benchmark candidate axis differs from prepared E2 axis")
    score_start = time.perf_counter()
    scores = np.zeros((len(prepared.disease_ids), len(prepared.candidate_ids)), dtype=np.float32)
    statuses: list[str | None] = [None] * len(prepared.disease_ids)
    similar_counts = np.zeros(len(prepared.disease_ids), dtype=np.int32)
    similarity_masses = np.zeros(len(prepared.disease_ids), dtype=np.float32)
    coverage_counts = np.zeros(len(prepared.disease_ids), dtype=np.int32)
    label_disease_index = {disease: index for index, disease in enumerate(prepared.label_disease_ids)}
    fold_counts: list[int] = []
    folds = int(benchmark.expected["folds"])
    candidate_set = frozenset(prepared.candidate_ids)
    for fold in range(folds):
        query_rows = np.flatnonzero(np.asarray(prepared.disease_folds) == fold)
        mask = benchmark.mask(fold)
        legal_clean = frozenset(
            (pair.disease_id, pair.drug_id)
            for pair in mask.legal_clean_pairs
            if pair.drug_id in candidate_set
        )
        allowed_diseases = {disease for disease, _drug in legal_clean}
        allowed_rows = np.asarray(
            [label_disease_index[disease] for disease in prepared.label_disease_ids if disease in allowed_diseases],
            dtype=int,
        )
        if allowed_diseases & mask.hidden_ids:
            raise ValueError("target/buffer disease leaked into legal E2 labels")
        train_labels = prepared.label_matrix[allowed_rows]
        if train_labels.nnz != len(legal_clean):
            raise ValueError("Gate-2 legal CLEAN count differs from E2 label slice")
        fold_counts.append(int(train_labels.nnz))
        sim_fold = prepared.similarity[query_rows][:, allowed_rows]
        weighted_votes = sim_fold @ train_labels
        fold_scores = weighted_votes.toarray().astype(np.float32)
        similarity_mass = np.asarray(sim_fold.sum(axis=1)).reshape(-1).astype(np.float32)
        valid_mass = similarity_mass > 0
        fold_scores[valid_mass] /= similarity_mass[valid_mass, None]
        scores[query_rows] = fold_scores
        for local_row, global_row in enumerate(query_rows):
            n_similar = int(sim_fold[local_row].nnz)
            mass = float(similarity_mass[local_row])
            coverage = int((fold_scores[local_row] > 0).sum())
            similar_counts[global_row] = n_similar
            similarity_masses[global_row] = similarity_mass[local_row]
            coverage_counts[global_row] = coverage
            if prepared.query_feature_counts[global_row] == 0:
                status = NO_PROFILE
            elif n_similar == 0 or mass <= 0:
                status = NO_SIMILAR
            elif coverage == 0:
                status = NO_TRANSFER
            else:
                status = "OK"
            statuses[global_row] = status
    if any(status is None for status in statuses) or not np.isfinite(scores).all():
        raise ValueError("E2 scoring left unresolved diseases or nonfinite scores")
    status_values = tuple(str(status) for status in statuses)
    applicable = tuple(status == "OK" for status in status_values)
    reasons = tuple(None if status == "OK" else status for status in status_values)
    runtime = dict(prepared.runtime_seconds)
    runtime["fold_scoring"] = time.perf_counter() - score_start
    metadata = {
        "representation": "binary TF-IDF over all incident nontherapeutic disease features",
        "feature_token": "relation|neighbor_type|neighbor_id",
        "direction_encoded": False,
        "therapeutic_relations_excluded": sorted(THERAPEUTIC_RELATIONS),
        "relation_types_used": list(prepared.relation_types),
        "all_disease_count_for_idf": prepared.profiles.all_disease_count,
        "feature_count": len(prepared.profiles.feature_ids),
        "disease_feature_pair_count": prepared.feature_pair_count,
        "relevant_disease_count": len(prepared.profiles.relevant_disease_ids),
        "global_clean_pair_count": len(prepared.global_clean_pairs),
        "global_label_disease_count": len(prepared.label_disease_ids),
        "idf_formula": "ln((1 + N_all_diseases) / (1 + document_frequency)) + 1",
        "tf": "binary",
        "normalization": "L2",
        "similarity": "full cosine; no top-k cutoff",
        "label_transfer": "sum(similarity * CLEAN indicator) / sum(legal similarity)",
        "score_dtype": "float32",
        "runtime_seconds": runtime,
        "similar_training_counts": similar_counts.tolist(),
        "similarity_masses": similarity_masses.tolist(),
        "candidate_coverage_counts": coverage_counts.tolist(),
    }
    return E2RunResult(
        expert_id=EXPERT_ID,
        expert_version=EXPERT_VERSION,
        expert_family=EXPERT_FAMILY,
        benchmark_id=benchmark.benchmark_id,
        masking_protocol=benchmark.protocol.value,
        candidate_ids=prepared.candidate_ids,
        disease_ids=prepared.disease_ids,
        scores=scores,
        applicable=applicable,
        abstention_reasons=reasons,
        deterministic=True,
        stochastic=False,
        seed=None,
        statuses=status_values,
        fold_legal_clean_counts=tuple(fold_counts),
        metadata=metadata,
    )


def run_e2(raw_kg: Path, benchmark: FrozenBenchmark) -> E2RunResult:
    return score_e2_prepared(prepare_e2(raw_kg, benchmark), benchmark)


def save_score_archive(run: E2RunResult, path: Path) -> None:
    import numpy as np

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        scores=np.asarray(run.scores, dtype=np.float32),
        disease_ids=np.asarray(run.disease_ids, dtype="U"),
        drug_ids=np.asarray(run.candidate_ids, dtype="U"),
    )
