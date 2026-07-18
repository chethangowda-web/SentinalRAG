import numpy as np

from app.services.embedding_service import normalize_embedding


def test_normalize_embedding():
    vec = [3.0, 4.0]
    normalized = normalize_embedding(vec)
    norm = np.linalg.norm(normalized)
    assert abs(norm - 1.0) < 1e-6


def test_normalize_zero_vector():
    vec = [0.0, 0.0, 0.0]
    normalized = normalize_embedding(vec)
    assert normalized == [0.0, 0.0, 0.0]


def test_normalize_already_normalized():
    vec = [1.0, 0.0]
    normalized = normalize_embedding(vec)
    assert abs(normalized[0] - 1.0) < 1e-6
    assert abs(normalized[1] - 0.0) < 1e-6
