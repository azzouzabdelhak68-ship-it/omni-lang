"use strict";
/**
 * OMNISYS.test — assertions, deterministic property testing, benchmarking.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const testModule = (omnisys.test = omnisys.test || {});
  const core = omnisys.core;

  function fail(msg) {
    core.panic("test assertion failed: " + msg);
  }
  testModule.fail = function (msg) {
    fail(msg);
  };
  testModule.assert_true = function (cond, msg) {
    if (!cond) fail(msg || "expected true");
    return null;
  };
  testModule.assert_eq = function (actual, expected) {
    const a = JSON.stringify(actual);
    const b = JSON.stringify(expected);
    if (a !== b) fail("assert_eq: expected " + b + " got " + a);
    return null;
  };
  testModule.assert_throws = function (fn) {
    try {
      fn();
    } catch (e) {
      return true;
    }
    return false;
  };

  // Deterministic LCG so property runs are reproducible.
  function lcg(seed) {
    let s = seed >>> 0;
    return function () {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s;
    };
  }

  testModule.property = function (prop, samples) {
    const rand = lcg(12345);
    const n = Math.max(1, samples | 0);
    for (let i = 0; i < n; i++) {
      const value = rand() % 1000;
      if (!prop(value)) {
        fail("property failed at sample " + i + " with value " + value);
      }
    }
    return true;
  };

  testModule.bench = function (fn, iterations) {
    const n = Math.max(1, iterations | 0);
    const start = Date.now();
    for (let i = 0; i < n; i++) fn();
    return Date.now() - start;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);