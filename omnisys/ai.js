"use strict";
/**
 * OMNISYS.ai — portable tensor/autograd/inference core. Dense tensors with
 * shape, elementwise ops, matmul, activations, linear layers, softmax, and
 * JSON round-trip. Hardware accelerators are escapes behind the same model.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const ai = (omnisys.ai = omnisys.ai || {});
  const core = omnisys.core;

  function sizeOf(shape) {
    return shape.reduce((n, d) => n * d, 1);
  }

  ai.tensor = function (shape, data) {
    const n = sizeOf(shape);
    if (data.length !== n) core.panic("ai.tensor: data length " + data.length + " != shape product " + n);
    return { tag: "tensor", shape: shape.slice(), data: data.slice() };
  };
  ai.tensor_zeros = function (shape) {
    return ai.tensor(shape, new Array(sizeOf(shape)).fill(0));
  };
  ai.tensor_ones = function (shape) {
    return ai.tensor(shape, new Array(sizeOf(shape)).fill(1));
  };
  ai.tensor_shape = function (tensor) {
    return tensor.shape.slice();
  };
  ai.tensor_add = function (a, b) {
    if (a.data.length !== b.data.length) core.panic("ai.tensor_add: length mismatch");
    return ai.tensor(a.shape, a.data.map((v, i) => v + b.data[i]));
  };
  ai.tensor_scale = function (a, factor) {
    return ai.tensor(a.shape, a.data.map((v) => v * factor));
  };
  ai.tensor_matmul = function (a, b) {
    const [m, k] = a.shape;
    const [k2, n] = b.shape;
    if (k !== k2) core.panic("ai.tensor_matmul: inner dims mismatch");
    const out = new Array(m * n);
    for (let i = 0; i < m; i++) {
      for (let j = 0; j < n; j++) {
        let sum = 0;
        for (let p = 0; p < k; p++) sum += a.data[i * k + p] * b.data[p * n + j];
        out[i * n + j] = sum;
      }
    }
    return ai.tensor([m, n], out);
  };
  ai.tensor_relu = function (a) {
    return ai.tensor(a.shape, a.data.map((v) => Math.max(0, v)));
  };
  ai.tensor_sigmoid = function (a) {
    return ai.tensor(a.shape, a.data.map((v) => 1 / (1 + Math.exp(-v))));
  };
  ai.tensor_sum = function (a) {
    return a.data.reduce((s, v) => s + v, 0);
  };
  ai.tensor_to_json = function (tensor) {
    return { tag: "tensor", shape: tensor.shape.slice(), data: tensor.data.slice() };
  };
  ai.tensor_from_json = function (json) {
    return ai.tensor(json.shape, json.data);
  };

  ai.linear = function (input, weights, bias) {
    if (input.length !== weights.length) core.panic("ai.linear: input/weights length mismatch");
    let sum = 0;
    for (let i = 0; i < input.length; i++) sum += input[i] * weights[i];
    return sum + (bias || 0);
  };
  ai.softmax = function (values) {
    const max = Math.max.apply(null, values);
    const exps = values.map((v) => Math.exp(v - max));
    const total = exps.reduce((s, v) => s + v, 0);
    return exps.map((v) => v / total);
  };
  ai.predict = function (layers, input) {
    // layers: [{weights: [...], bias: number}] -> input passes through each.
    let out = input.slice();
    for (const layer of layers) {
      const next = [];
      for (const neuron of layer.weights) {
        next.push(ai.linear(out, neuron, layer.bias));
      }
      out = next;
    }
    return out;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);