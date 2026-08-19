"""OMNISYS.ai — dense tensors, linear algebra, activations, prediction.

Python reference implementation of the OMNISYS ``ai`` module (v6), mirroring
the JS reference lane ``omnisys/ai.js`` and satisfying the registry contract
(``OMNISYS_MODULES["ai"]``). Tensors are JSON values ``{"tag": "tensor",
"shape": [...], "data": [...]}``; all fifteen functions are pure. GPU and
autograd are documented escapes; this is the portable dense-tensor core.
"""

import math
from typing import Any, TypeAlias

from omnisys_core import panic

__all__ = [
    'tensor',
    'tensor_zeros',
    'tensor_ones',
    'tensor_shape',
    'tensor_add',
    'tensor_scale',
    'tensor_matmul',
    'tensor_relu',
    'tensor_sigmoid',
    'tensor_sum',
    'tensor_to_json',
    'tensor_from_json',
    'linear',
    'softmax',
    'predict',
]

Tensor: TypeAlias = dict[str, Any]
Layer: TypeAlias = dict[str, Any]


def _size_of(shape: list[int]) -> int:
    """Return the product of ``shape`` dimensions (1 for an empty shape)."""
    size = 1
    for dim in shape:
        size *= dim
    return size


def tensor(shape: list[int], data: list[float]) -> Tensor:
    """Build a tensor value, panicking when the data length mismatches."""
    n = _size_of(shape)
    if len(data) != n:
        panic(f'ai.tensor: data length {len(data)} != shape product {n}')
    return {'tag': 'tensor', 'shape': list(shape), 'data': list(data)}


def tensor_zeros(shape: list[int]) -> Tensor:
    """Return a tensor filled with zeros."""
    return tensor(shape, [0] * _size_of(shape))


def tensor_ones(shape: list[int]) -> Tensor:
    """Return a tensor filled with ones."""
    return tensor(shape, [1] * _size_of(shape))


def tensor_shape(value: Tensor) -> list[int]:
    """Return a copy of the tensor's shape."""
    return list(value['shape'])


def tensor_add(a: Tensor, b: Tensor) -> Tensor:
    """Element-wise addition, panicking on data length mismatch."""
    if len(a['data']) != len(b['data']):
        panic('ai.tensor_add: length mismatch')
    return tensor(a['shape'], [va + vb for va, vb in zip(a['data'], b['data'], strict=True)])


def tensor_scale(a: Tensor, factor: Any) -> Tensor:
    """Scale every element of ``a`` by ``factor``."""
    return tensor(a['shape'], [v * factor for v in a['data']])


def tensor_matmul(a: Tensor, b: Tensor) -> Tensor:
    """Matrix multiply ``a`` (m×k) by ``b`` (k×n), panicking on inner mismatch."""
    m, k = a['shape']
    k2, n = b['shape']
    if k != k2:
        panic('ai.tensor_matmul: inner dims mismatch')
    out: list[float] = []
    for i in range(m):
        for j in range(n):
            total = 0
            for p in range(k):
                total += a['data'][i * k + p] * b['data'][p * n + j]
            out.append(total)
    return tensor([m, n], out)


def tensor_relu(a: Tensor) -> Tensor:
    """Apply ReLU (``max(0, v)``) element-wise."""
    return tensor(a['shape'], [max(0.0, v) for v in a['data']])


def tensor_sigmoid(a: Tensor) -> Tensor:
    """Apply the sigmoid ``1 / (1 + exp(-v))`` element-wise."""
    return tensor(a['shape'], [1 / (1 + math.exp(-v)) for v in a['data']])


def tensor_sum(a: Tensor) -> float:
    """Return the sum of all tensor elements."""
    return float(sum(a['data']))


def tensor_to_json(value: Tensor) -> Tensor:
    """Export the tensor as a JSON value (shape and data copies)."""
    return {'tag': 'tensor', 'shape': list(value['shape']), 'data': list(value['data'])}


def tensor_from_json(value: Tensor) -> Tensor:
    """Rebuild a tensor from a JSON value."""
    return tensor(value['shape'], value['data'])


def linear(input: list[float], weights: list[float], bias: Any) -> float:
    """Dot-product ``input``·``weights`` plus ``bias`` (panics on mismatch)."""
    if len(input) != len(weights):
        panic('ai.linear: input/weights length mismatch')
    return sum(v * w for v, w in zip(input, weights, strict=True)) + (bias or 0)


def softmax(values: list[float]) -> list[float]:
    """Return the softmax of ``values`` (empty list stays empty)."""
    if not values:
        return []
    max_value = max(values)
    exps = [math.exp(v - max_value) for v in values]
    total = sum(exps)
    return [v / total for v in exps]


def predict(layers: list[Layer], input: list[float]) -> list[float]:
    """Pass ``input`` through each layer's neurons (weights + bias)."""
    out: list[float] = list(input)
    for layer in layers:
        out = [linear(out, neuron, layer.get('bias', 0)) for neuron in layer['weights']]
    return out
