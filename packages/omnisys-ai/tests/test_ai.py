"""Unit tests for OMNISYS.ai."""

from __future__ import annotations

import math

import omnisys_ai as ai
import pytest
from omnisys_core import PanicError


def test_tensor_shape_and_data() -> None:
    value = ai.tensor([2, 2], [1, 2, 3, 4])
    assert value == {'tag': 'tensor', 'shape': [2, 2], 'data': [1, 2, 3, 4]}


def test_tensor_panics_on_length_mismatch() -> None:
    with pytest.raises(PanicError):
        ai.tensor([2, 2], [1, 2, 3])


def test_tensor_copies_shape_and_data() -> None:
    shape = [1, 2]
    data = [1, 2]
    value = ai.tensor(shape, data)
    shape.append(9)
    data.append(9)
    assert value['shape'] == [1, 2]
    assert value['data'] == [1, 2]


def test_tensor_zeros() -> None:
    assert ai.tensor_zeros([2, 3]) == {'tag': 'tensor', 'shape': [2, 3], 'data': [0, 0, 0, 0, 0, 0]}


def test_tensor_ones() -> None:
    assert ai.tensor_ones([2]) == {'tag': 'tensor', 'shape': [2], 'data': [1, 1]}


def test_tensor_zeros_empty_shape() -> None:
    assert ai.tensor_zeros([]) == {'tag': 'tensor', 'shape': [], 'data': [0]}


def test_tensor_shape_returns_copy() -> None:
    value = ai.tensor([2, 2], [1, 2, 3, 4])
    shape = ai.tensor_shape(value)
    shape[0] = 99
    assert value['shape'] == [2, 2]


def test_tensor_add() -> None:
    a = ai.tensor([2], [1, 2])
    b = ai.tensor([2], [10, 20])
    assert ai.tensor_add(a, b)['data'] == [11, 22]


def test_tensor_add_length_mismatch() -> None:
    with pytest.raises(PanicError):
        ai.tensor_add(ai.tensor([2], [1, 2]), ai.tensor([3], [1, 2, 3]))


def test_tensor_scale() -> None:
    value = ai.tensor([2], [1, 2])
    assert ai.tensor_scale(value, 3)['data'] == [3, 6]


def test_tensor_scale_float() -> None:
    value = ai.tensor([2], [1, 2])
    assert ai.tensor_scale(value, 0.5)['data'] == [0.5, 1.0]


def test_tensor_matmul_known() -> None:
    a = ai.tensor([2, 3], [1, 2, 3, 4, 5, 6])
    b = ai.tensor([3, 2], [7, 8, 9, 10, 11, 12])
    assert ai.tensor_matmul(a, b)['data'] == [58, 64, 139, 154]


def test_tensor_matmul_inner_dims_mismatch() -> None:
    with pytest.raises(PanicError):
        ai.tensor_matmul(ai.tensor([2, 3], [0] * 6), ai.tensor([4, 2], [0] * 8))


def test_tensor_relu() -> None:
    value = ai.tensor([3], [-2, 0, 3])
    assert ai.tensor_relu(value)['data'] == [0, 0, 3]


def test_tensor_sigmoid() -> None:
    value = ai.tensor([2], [0, 1])
    data = ai.tensor_sigmoid(value)['data']
    assert data[0] == pytest.approx(0.5)
    assert data[1] == pytest.approx(1 / (1 + math.exp(-1)))


def test_tensor_sum() -> None:
    assert ai.tensor_sum(ai.tensor([3], [1, 2, 3])) == 6


def test_tensor_sum_empty_data() -> None:
    assert ai.tensor_sum(ai.tensor([0], [])) == 0


def test_tensor_to_json_and_from_json_round_trip() -> None:
    value = ai.tensor([2, 2], [1, 2, 3, 4])
    assert ai.tensor_from_json(ai.tensor_to_json(value)) == value


def test_tensor_from_json_panics_on_mismatch() -> None:
    with pytest.raises(PanicError):
        ai.tensor_from_json({'tag': 'tensor', 'shape': [2], 'data': [1, 2, 3]})


def test_linear() -> None:
    assert ai.linear([1, 2], [3, 4], 5) == 16


def test_linear_default_bias_zero() -> None:
    assert ai.linear([1, 2], [3, 4], None) == 11


def test_linear_length_mismatch() -> None:
    with pytest.raises(PanicError):
        ai.linear([1, 2], [3], 0)


def test_softmax_sums_to_one() -> None:
    out = ai.softmax([1, 2, 3])
    assert sum(out) == pytest.approx(1.0)
    assert out[2] > out[1] > out[0]


def test_softmax_empty() -> None:
    assert ai.softmax([]) == []


def test_softmax_large_values_stable() -> None:
    out = ai.softmax([1000, 1001, 1002])
    assert sum(out) == pytest.approx(1.0)


def test_predict_single_layer() -> None:
    layers = [{'weights': [[1, 2], [3, 4]], 'bias': 0}]
    assert ai.predict(layers, [1, 1]) == [3, 7]


def test_predict_multi_layer() -> None:
    layers = [{'weights': [[1, 2]], 'bias': 0}, {'weights': [[1]], 'bias': 0}]
    assert ai.predict(layers, [1, 1]) == [3]


def test_predict_missing_bias_defaults_zero() -> None:
    layers = [{'weights': [[1, 2]]}]
    assert ai.predict(layers, [1, 1]) == [3]


def test_predict_empty_layers_returns_input() -> None:
    assert ai.predict([], [1, 2, 3]) == [1, 2, 3]
