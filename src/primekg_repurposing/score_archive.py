"""Strict readers for historical NumPy score archives.

Historical Cell 14 serialized its string axes as object arrays.  NumPy's
ordinary ``allow_pickle=True`` path is intentionally not used here: the
restricted unpickler admits only the small set of NumPy constructors needed
for an ndarray and the result is then required to be a one-dimensional array
of Python strings.
"""

from __future__ import annotations

import io
import pickle
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScoreArchive:
    scores: object
    disease_ids: tuple[str, ...]
    drug_ids: tuple[str, ...]


class _RestrictedNumpyUnpickler(pickle.Unpickler):
    _ALLOWED = {
        ("numpy", "dtype"),
        ("numpy", "ndarray"),
        ("numpy.core.multiarray", "_reconstruct"),
        ("numpy._core.multiarray", "_reconstruct"),
    }

    def find_class(self, module: str, name: str):
        if (module, name) not in self._ALLOWED:
            raise pickle.UnpicklingError(f"forbidden object in NumPy axis: {module}.{name}")
        return super().find_class(module, name)


def _read_npy_header(raw: bytes):
    from numpy.lib import format

    handle = io.BytesIO(raw)
    version = format.read_magic(handle)
    if version == (1, 0):
        shape, fortran_order, dtype = format.read_array_header_1_0(handle)
    elif version in {(2, 0), (3, 0)}:
        shape, fortran_order, dtype = format.read_array_header_2_0(handle)
    else:
        raise ValueError(f"unsupported NPY version {version}")
    return handle, shape, fortran_order, dtype


def _read_numeric_array(raw: bytes, *, name: str):
    import numpy as np

    handle, shape, _fortran_order, dtype = _read_npy_header(raw)
    if dtype.hasobject:
        raise ValueError(f"{name} must not be an object array")
    handle.seek(0)
    array = np.lib.format.read_array(handle, allow_pickle=False)
    if array.shape != shape:
        raise ValueError(f"{name} shape changed while reading")
    return array


def _read_string_axis(raw: bytes, *, name: str) -> tuple[str, ...]:
    import numpy as np

    handle, shape, _fortran_order, dtype = _read_npy_header(raw)
    if len(shape) != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if dtype.hasobject:
        array = _RestrictedNumpyUnpickler(handle).load()
    else:
        handle.seek(0)
        array = np.lib.format.read_array(handle, allow_pickle=False)
    if not isinstance(array, np.ndarray) or array.shape != shape:
        raise ValueError(f"{name} is not the declared ndarray")
    values = array.tolist()
    if not isinstance(values, list) or any(type(value) is not str for value in values):
        raise ValueError(f"{name} must contain only plain strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} contains duplicate IDs")
    return tuple(values)


def load_score_archive(path: Path) -> ScoreArchive:
    """Load the score matrix and axes without unrestricted object loading."""
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {"scores.npy", "disease_ids.npy", "drug_ids.npy"}
        if not required <= names:
            missing = sorted(required - names)
            raise ValueError(f"score archive missing arrays: {missing}")
        scores = _read_numeric_array(archive.read("scores.npy"), name="scores")
        diseases = _read_string_axis(archive.read("disease_ids.npy"), name="disease_ids")
        drugs = _read_string_axis(archive.read("drug_ids.npy"), name="drug_ids")
    if scores.ndim != 2 or scores.shape != (len(diseases), len(drugs)):
        raise ValueError("score matrix shape does not match archive axes")
    return ScoreArchive(scores=scores, disease_ids=diseases, drug_ids=drugs)
