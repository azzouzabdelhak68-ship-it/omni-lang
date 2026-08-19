"""Property tests for OMNISYS.ai."""

from __future__ import annotations

import math

import omnisys_ai as ai
import pytest
from hypothesis import given
from hypothesis import strategies as st

_DIMS = st.integers(min_value=0, max_value=3)
_VALUES = st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False)


@given(
    st.lists(_DIMS, min_size=1, max_size=2),
    st.lists(_VALUES, min_size=0, max_size=20),
)
def test_tensor_to_from_json_round_trip(shape: list[int], data: list[float]) -> None:
    size = math.prod(shape)
    if len(data) != size:
        return
    value = ai.tensor(shape, data)
    assert ai.tensor_from_json(ai.tensor_to_json(value)) == value


@given(st.lists(_VALUES, min_size=1, max_size=8), st.lists(_VALUES, min_size=1, max_size=8))
def test_tensor_add_commutative(a: list[float], b: list[float]) -> None:
    if len(a) != len(b):
        return
    result = ai.tensor_add(ai.tensor([len(a)], a), ai.tensor([len(a)], b))
    assert result['data'] == ai.tensor_add(ai.tensor([len(a)], b), ai.tensor([len(a)], a))['data']


@given(st.lists(_VALUES, min_size=0, max_size=8), st.floats(min_value=-5, max_value=5))
def test_tensor_scale_distributes(a: list[float], factor: float) -> None:
    value = ai.tensor([len(a)], a)
    scaled = ai.tensor_scale(value, factor)['data']
    assert all(s == pytest.approx(v * factor, abs=1e-9) for s, v in zip(scaled, a, strict=True))


@given(st.lists(_VALUES, min_size=0, max_size=8))
def test_tensor_relu_nonnegative(a: list[float]) -> None:
    out = ai.tensor_relu(ai.tensor([len(a)], a))['data']
    assert all(v >= 0 for v in out)


@given(st.lists(_VALUES, min_size=0, max_size=8))
def test_softmax_sums_to_one(a: list[float]) -> None:
    out = ai.softmax(a)
    if not a:
        assert out == []
    else:
        assert sum(out) == pytest.approx(1.0, abs=1e-6)


@given(st.lists(_VALUES, min_size=1, max_size=4), st.lists(_VALUES, min_size=1, max_size=4))
def test_linear_commutes_scalar_weights(weights: list[float], bias_values: list[float]) -> None:
    del bias_values
    input = weights
    out = ai.linear(input, weights, 0)
    assert out == pytest.approx(sum(v * w for v, w in zip(input, weights, strict=True)))


@given(
    st.lists(_DIMS, min_size=1, max_size=3),
    st.lists(_VALUES, min_size=0, max_size=100),
)
def test_matmul_with_identity_returns_input(shape: list[int], data: list[float]) -> None:
    if len(shape) != 2 or shape[0] != shape[1] or len(data) != math.prod(shape):
        return
    n = shape[0]
    identity = ai.tensor([n, n], [1.0 if i == j else 0.0 for i in range(n) for j in range(n)])
    result = ai.tensor_matmul(ai.tensor(shape, data), identity)
    assert result['data'] == pytest.approx(data)


@given(
    st.lists(_VALUES, min_size=2, max_size=2),
    st.lists(_VALUES, min_size=0, max_size=8),
)
def test_predict_output_length(a: list[float], bias: list[float]) -> None:
    del bias
    layers = [{'weights': [[1, 0], [0, 1]], 'bias': 0}]
    out = ai.predict(layers, a)
    assert len(out) == 2
