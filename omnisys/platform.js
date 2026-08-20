"use strict";
/**
 * OMNISYS.platform — native platform abstractions. The Node lane reports OS,
 * arch, env, monotonic time; `capabilities()` lists what the current lane can
 * do. Browser lane reports its own capabilities and raises for process ones.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const platform = (omnisys.platform = omnisys.platform || {});
  const core = omnisys.core;

  let nodeProcess = null;
  let nodeOs = null;
  if (typeof process !== "undefined" && process.versions && process.versions.node) {
    nodeProcess = process;
    if (typeof require !== "undefined") {
      try {
        nodeOs = require("os");
      } catch (e) {
        nodeOs = null;
      }
    }
  }

  platform.now = function () {
    return Date.now();
  };
  platform.os = function () {
    if (nodeOs) return nodeOs.platform();
    return "browser";
  };
  platform.arch = function () {
    if (nodeOs) return nodeOs.arch();
    return "js";
  };
  platform.env = function (key, defaultValue) {
    if (nodeProcess && nodeProcess.env && nodeProcess.env[String(key)] !== undefined) {
      return String(nodeProcess.env[String(key)]);
    }
    return defaultValue !== undefined ? String(defaultValue) : "";
  };
  platform.info = function () {
    return {
      os: platform.os(),
      arch: platform.arch(),
      node: nodeProcess ? nodeProcess.version : null,
      runtime: nodeProcess ? "node" : "browser",
    };
  };
  platform.sleep_ms = function (ms) {
    const end = Date.now() + Math.max(0, ms | 0);
    while (Date.now() < end) {
      // busy-wait (only for tiny sleeps; deterministic)
    }
    return ms;
  };
  platform.capabilities = function () {
    const caps = ["none"];
    if (nodeProcess) caps.push("process");
    if (typeof window !== "undefined") caps.push("graphics", "camera", "microphone");
    return caps;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);