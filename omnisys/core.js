"use strict";
/**
 * OMNISYS.core — implicit root module (import OMNISYS).
 * Portable core: option/result wrappers, math, length helpers, panic.
 * Pure, dependency-free. Attaches to the global `omnisys` namespace so the
 * JS emitter can inline it (browser) and Node can require() it identically.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const core = (omnisys.core = omnisys.core || {});

  core.panic = function (msg) {
    throw new Error("[OMNISYS.core] " + String(msg));
  };

  core.identity = function (x) {
    return x;
  };

  core.type_of = function (x) {
    if (x === null) return "none";
    if (Array.isArray(x)) return "list";
    return typeof x;
  };

  core.option = function (value) {
    return { tag: "some", value: value };
  };
  core.some = core.option;
  core.none = function () {
    return { tag: "none" };
  };
  core.is_some = function (opt) {
    return opt && opt.tag === "some";
  };
  core.is_none = function (opt) {
    return opt && opt.tag === "none";
  };

  core.ok = function (value) {
    return { tag: "ok", value: value };
  };
  core.err = function (error) {
    return { tag: "err", error: error };
  };
  core.is_ok = function (res) {
    return res && res.tag === "ok";
  };
  core.is_err = function (res) {
    return res && res.tag === "err";
  };

  core.abs = function (x) {
    return Math.abs(x);
  };
  core.min = function (a, b) {
    return Math.min(a, b);
  };
  core.max = function (a, b) {
    return Math.max(a, b);
  };
  core.clamp = function (x, lo, hi) {
    return Math.min(Math.max(x, lo), hi);
  };
  core.round = function (x) {
    return Math.round(x);
  };
  core.floor = function (x) {
    return Math.floor(x);
  };
  core.ceil = function (x) {
    return Math.ceil(x);
  };
  core.sqrt = function (x) {
    return Math.sqrt(x);
  };

  core.length = function (x) {
    if (x == null) return 0;
    if (typeof x === "string" || Array.isArray(x)) return x.length;
    if (typeof x === "object") return Object.keys(x).length;
    return 0;
  };
  core.is_empty = function (x) {
    return core.length(x) === 0;
  };

  core.split = function (s, sep) {
    return String(s).split(String(sep));
  };
  core.char_at = function (s, i) {
    const str = String(s);
    const idx = Number(i);
    if (idx < 0 || idx >= str.length) return "";
    return str.charAt(idx);
  };
  core.substring = function (s, start, end) {
    const str = String(s);
    let a = Number(start);
    let b = end === undefined ? str.length : Number(end);
    if (a < 0) a = 0;
    if (b < 0) b = 0;
    if (a > b) { const t = a; a = b; b = t; }
    return str.substring(a, b);
  };
  core.to_number = function (s) {
    const n = Number(String(s).trim());
    return Number.isNaN(n) ? 0 : n;
  };

  core.VERSION = "6.0.0";
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);