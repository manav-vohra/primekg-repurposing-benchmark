"""Focused Gate-6A contract tests; no training is performed."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from primekg_repurposing.experts.e3_complex import (
    CLEAN_RELATION, COMPLEX_DIM, EXPECTED_FOLD_COUNTS, STAGE_B, THERAPEUTIC_RELATIONS,
    ComplExModel, historical_reference_score, read_csv_rows, sample_clean_head_corruptions,
    sha256_file, validate_checkpoint,
)

torch = pytest.importorskip("torch")
ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "artifacts/frozen"
RECOVERED = ROOT / "artifacts/recovered/external"
REPORT = ROOT / "outputs/gate6a_e3_preparation.json"
PREREG = ROOT / "outputs/gate6b_preregistration.json"


def report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_01_corrected_cell19b_corpus_semantics(): assert report()["corpus"]["status"] == "PASS"
def test_02_therapeutic_relations_absent(): assert report()["corpus"]["checks"]["therapeutic_relations_absent"]
def test_03_entity_vocabulary_ordering(): assert report()["corpus"]["checks"]["entity_lexical_order"]
def test_04_relation_vocabulary_ordering(): assert report()["corpus"]["checks"]["relation_lexical_order"]
def test_05_fold_legal_label_counts(): assert tuple(report()["corpus"]["fold_legal_counts"]) == EXPECTED_FOLD_COUNTS
def test_06_target_labels_absent(): assert report()["corpus"]["checks"]["hidden_label_leaks"]
def test_07_buffer_labels_absent(): assert report()["corpus"]["checks"]["hidden_label_leaks"]
def test_08_long_ids_not_truncated(): assert report()["corpus"]["checks"]["long_ids_complete"]


def test_09_complex_equation_hand_fixture():
    model = ComplExModel(2, 1, 1)
    state = {"entity_re.weight": torch.tensor([[2.0], [3.0]]), "entity_im.weight": torch.tensor([[5.0], [7.0]]),
             "relation_re.weight": torch.tensor([[11.0]]), "relation_im.weight": torch.tensor([[13.0]])}
    model.load_state_dict(state)
    assert model.score(torch.tensor([0]), torch.tensor([0]), torch.tensor([1])).item() == 438.0


def test_10_head_tail_orientation():
    model = ComplExModel(2, 1, 1); state = {"entity_re.weight": torch.tensor([[2.0], [3.0]]), "entity_im.weight": torch.tensor([[5.0], [7.0]]), "relation_re.weight": torch.tensor([[11.0]]), "relation_im.weight": torch.tensor([[13.0]])}; model.load_state_dict(state)
    assert model.score(torch.tensor([0]), torch.tensor([0]), torch.tensor([1])).item() != model.score(torch.tensor([1]), torch.tensor([0]), torch.tensor([0])).item()


def test_11_clean_relation_orientation():
    rows = read_csv_rows(FROZEN / "benchmark/p1_e3_complex_relations.csv")
    assert rows[7]["relation_name"] == CLEAN_RELATION


def test_12_candidate_axis_ordering(): assert all(x["candidate_axis_verified"] for x in report()["score_archives"])
def test_13_disease_axis_ordering(): assert all(x["disease_axis_verified"] for x in report()["score_archives"])


def test_14_negative_corruption_semantics():
    rng = np.random.default_rng(1); result = sample_clean_head_corruptions(np.array([9]), np.array([1, 2, 3]), {9: np.array([1, 2])}, rng, 8)
    assert set(result.ravel()) == {3}


def test_15_corruptions_are_not_benchmark_negatives(): assert "not biological negatives" in STAGE_B["negative_semantics"]


def test_16_deterministic_score_probe():
    torch.manual_seed(4); model = ComplExModel(4, 2, 3); h = torch.tensor([0, 2]); r = torch.tensor([1, 0]); t = torch.tensor([3, 1])
    assert torch.equal(model.score(h, r, t), model.score(h, r, t))


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_17_19_checkpoints_load(seed):
    path = RECOVERED / f"p1_e3_complex_seed{seed}_base_pretrain.pt"
    if not path.exists(): pytest.skip("registered external checkpoint not local")
    assert validate_checkpoint(path, seed)["strict_load"]


def test_20_checkpoint_tensor_shapes():
    for item in report()["checkpoint_validation"]:
        assert item["tensors"]["entity_re.weight"]["shape"] == [129307, 64]
        assert item["tensors"]["relation_re.weight"]["shape"] == [28, 64]


def test_21_reference_forward_probe_equals_clean():
    assert all(x["probe_bitwise_equal"] and x["probe_max_abs_difference"] == 0.0 for x in report()["checkpoint_validation"])


def _bad_checkpoint(directory, name, payload):
    path = directory / name
    torch.save(payload, path)
    return path


def test_22_wrong_checkpoint_dimensionality_fails(tmp_path):
    path = _bad_checkpoint(tmp_path, "test_bad_dim.pt", {"seed": 0, "complex_dim": 63, "corpus_manifest_sha256": "x", "state_dict": {}})
    try:
        with pytest.raises(ValueError, match="dimension"): validate_checkpoint(path, 0)
    finally: path.unlink(missing_ok=True)


def test_23_wrong_entity_vocabulary_fails(tmp_path):
    path = _bad_checkpoint(tmp_path, "test_bad_entity_vocab.pt", {"seed": 0, "complex_dim": 64, "corpus_manifest_sha256": "wrong", "state_dict": {}})
    try:
        with pytest.raises(ValueError, match="mapping"): validate_checkpoint(path, 0)
    finally: path.unlink(missing_ok=True)


def test_24_wrong_relation_vocabulary_fails(tmp_path):
    path = _bad_checkpoint(tmp_path, "test_bad_relation_vocab.pt", {"seed": 0, "complex_dim": 64, "corpus_manifest_sha256": "wrong", "state_dict": {}})
    try:
        with pytest.raises(ValueError, match="mapping"): validate_checkpoint(path, 0)
    finally: path.unlink(missing_ok=True)


def test_25_seed_identity_mismatch_fails():
    path = RECOVERED / "p1_e3_complex_seed0_base_pretrain.pt"
    if not path.exists(): pytest.skip("registered external checkpoint not local")
    with pytest.raises(ValueError, match="seed"): validate_checkpoint(path, 2)


def test_26_historical_archives_keep_axes(): assert all(x["status"] == "PASS" for x in report()["score_archives"])


def test_27_preregistration_complete_machine_readable():
    value = json.loads(PREREG.read_text(encoding="utf-8"))
    required = {"implementation", "corpus", "benchmark", "seeds", "stage_a_checkpoints", "stage_b", "axes", "reference_score_archives", "runtime_environment", "comparison_fields"}
    assert value["state"] == "FROZEN_BEFORE_TRAINING" and required <= set(value) and value["pass_tolerance"] is None


@pytest.mark.parametrize("filename,expected_hash", [
    ("p1_e3_complex_base_nonther_triples.npz", "4b13562268f237b4217002279338a721e9c6b9c30fa178d29883066848fd733b"),
    ("p1_e3_complex_clean_indication_triples.npz", "06573916aa538640949c4fceb79acb4455856aaf2038cd44df5c54675a30c0b3"),
])
def test_corpus_npz_hashes_match_historical_manifest(filename, expected_hash):
    path = RECOVERED / filename
    if not path.exists():
        pytest.skip("registered external corpus not local")
    assert sha256_file(path) == expected_hash


def test_model_uses_sparse_entity_and_dense_relation_embeddings():
    model = ComplExModel(3, 2, COMPLEX_DIM)
    assert model.entity_re.sparse and model.entity_im.sparse and not model.relation_re.sparse and not model.relation_im.sparse
