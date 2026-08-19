"use strict";
/**
 * OMNISYS.gpu — portable GPU-compute model. The portable core expresses
 * data-parallel kernels with explicit buffer inputs; the JS lane runs a
 * deterministic CPU fallback so programs are testable everywhere. Hardware
 * lanes (WebGPU/CUDA/Metal/Vulkan) are escapes that consume the same model.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const gpu = (omnisys.gpu = omnisys.gpu || {});
  const core = omnisys.core;

  gpu.buffer = function (data) {
    return { tag: "gpu.buffer", data: (data || []).slice() };
  };
  gpu.compute = function (kernel, input, size) {
    const n = Math.max(0, size | 0);
    const out = [];
    for (let i = 0; i < n; i++) {
      out.push(kernel(i, input));
    }
    return out;
  };
  gpu.parallel = function (kernel, list) {
    return (list || []).map((item, i) => kernel(i, item));
  };
  gpu.add = function (a, b) {
    if (a.length !== b.length) core.panic("gpu.add: length mismatch");
    return a.map((v, i) => v + b[i]);
  };
  gpu.scale = function (a, factor) {
    return a.map((v) => v * factor);
  };
  gpu.dot = function (a, b) {
    if (a.length !== b.length) core.panic("gpu.dot: length mismatch");
    let sum = 0;
    for (let i = 0; i < a.length; i++) sum += a[i] * b[i];
    return sum;
  };
  gpu.matmul = function (a, b) {
    const m = a.length;
    const n = b[0].length;
    const k = b.length;
    if (a[0].length !== k) core.panic("gpu.matmul: incompatible matrices");
    const out = [];
    for (let i = 0; i < m; i++) {
      const row = [];
      for (let j = 0; j < n; j++) {
        let sum = 0;
        for (let p = 0; p < k; p++) sum += a[i][p] * b[p][j];
        row.push(sum);
      }
      out.push(row);
    }
    return out;
  };
  gpu.normalize = function (a) {
    const len = Math.sqrt(a.reduce((s, v) => s + v * v, 0));
    if (len === 0) return a.slice();
    return a.map((v) => v / len);
  };
  gpu.device_info = function () {
    return { tag: "gpu.device", name: "portable-cpu", lanes: ["js-fallback"], cores: 1 };
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);