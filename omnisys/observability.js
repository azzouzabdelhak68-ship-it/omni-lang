"use strict";
/**
 * OMNISYS.observability — logging, metrics, tracing, profiling. In-process
 * collector with a JSON snapshot. Portable; no external I/O.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const observability = (omnisys.observability = omnisys.observability || {});

  const state = { logs: [], metrics: {}, traces: [], nextTrace: 1 };

  observability.clear = function () {
    state.logs = [];
    state.metrics = {};
    state.traces = [];
    return null;
  };
  observability.log = function (level, message, fields) {
    state.logs.push({ level: String(level), message: String(message), fields: fields || {}, at: Date.now() });
    return null;
  };
  observability.info = function (message, fields) {
    return observability.log("info", message, fields);
  };
  observability.warn = function (message, fields) {
    return observability.log("warn", message, fields);
  };
  observability.error = function (message, fields) {
    return observability.log("error", message, fields);
  };
  observability.metric = function (name, value) {
    state.metrics[String(name)] = Number(value);
    return null;
  };
  observability.metric_value = function (name) {
    return state.metrics[String(name)] !== undefined ? state.metrics[String(name)] : 0;
  };
  observability.trace_begin = function (name) {
    const id = state.nextTrace++;
    state.traces.push({ id: id, name: String(name), start: Date.now(), end: null, fields: {} });
    return id;
  };
  observability.trace_end = function (id, fields) {
    const trace = state.traces.find((t) => t.id === id);
    if (trace) {
      trace.end = Date.now();
      trace.duration = trace.end - trace.start;
      trace.fields = fields || {};
    }
    return null;
  };
  observability.snapshot = function () {
    return {
      logs: state.logs.slice(),
      metrics: Object.assign({}, state.metrics),
      traces: state.traces.map((t) => Object.assign({}, t)),
    };
  };
  observability.profile = function (fn, iterations) {
    const n = Math.max(1, iterations | 0);
    const start = Date.now();
    for (let i = 0; i < n; i++) fn();
    return Date.now() - start;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);