import numpy as np
import pytest
from sign.service import SignService

def _make_frames(n=64):
    """Synthetic landmark sequence: 64 frames, 21 landmarks, 3 coords each."""
    return [[[0.5, 0.5, 0.0]] * 21 for _ in range(n)]

def test_classify_returns_string():
    svc = SignService()
    result = svc.classify(_make_frames())
    assert isinstance(result, str)
    assert len(result) > 0

def test_classify_short_sequence():
    svc = SignService()
    result = svc.classify(_make_frames(n=10))
    assert isinstance(result, str)

def test_classify_empty_returns_empty():
    svc = SignService()
    assert svc.classify([]) == ""

def test_classify_confidence():
    """classify_with_confidence should return (label, score) tuple."""
    svc = SignService()
    label, score = svc.classify_with_confidence(_make_frames())
    assert isinstance(label, str)
    assert 0.0 <= score <= 1.0
