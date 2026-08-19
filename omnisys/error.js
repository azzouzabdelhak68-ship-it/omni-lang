"use strict";
/**
 * OMNISYS.error — structured error values with codes and context.
 * Portable: errors are plain JSON-friendly objects.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const errorModule = (omnisys.error = omnisys.error || {});
  const core = omnisys.core;

  function captureStack() {
    try {
      throw new Error();
    } catch (e) {
      return e.stack || "";
    }
  }

  errorModule.error = function (message) {
    return { tag: "error", message: String(message), code: "E-OMNI", context: {}, stack: captureStack() };
  };
  errorModule.error_code = function (message, code) {
    return { tag: "error", message: String(message), code: String(code), context: {}, stack: captureStack() };
  };
  errorModule.error_message = function (err) {
    return err && err.message !== undefined ? err.message : String(err);
  };
  errorModule.error_code_of = function (err) {
    return err && err.code !== undefined ? err.code : "";
  };
  errorModule.error_stack = function (err) {
    return err && err.stack !== undefined ? err.stack : "";
  };
  errorModule.error_with_context = function (err, key, value) {
    const out = Object.assign({}, err);
    out.context = Object.assign({}, err.context || {});
    out.context[String(key)] = value;
    return out;
  };
  errorModule.error_has_context = function (err, key) {
    return !!(err && err.context && Object.prototype.hasOwnProperty.call(err.context, String(key)));
  };
  errorModule.error_to_dict = function (err) {
    return {
      tag: "error",
      message: errorModule.error_message(err),
      code: errorModule.error_code_of(err),
      stack: errorModule.error_stack(err),
      context: (err && err.context) || {},
    };
  };
  errorModule.throw_error = function (err) {
    throw Object.assign(new Error(errorModule.error_message(err)), errorModule.error_to_dict(err));
  };
  errorModule.is_error = function (x) {
    return !!(x && x.tag === "error");
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);