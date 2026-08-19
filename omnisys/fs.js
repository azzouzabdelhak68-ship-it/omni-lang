"use strict";
/**
 * OMNISYS.fs — filesystem (Node lane uses the sync fs API; the browser lane
 * reports capability errors via `omnisys.core.panic`). Path helpers are pure.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const fsModule = (omnisys.fs = omnisys.fs || {});
  const core = omnisys.core;

  let nodeFs = null;
  if (typeof require !== "undefined") {
    try {
      nodeFs = require("fs");
    } catch (e) {
      nodeFs = null;
    }
  }
  const nodePath = typeof require !== "undefined" ? (() => { try { return require("path"); } catch (e) { return null; } })() : null;

  function needNodeFs() {
    if (!nodeFs) core.panic("fs: the browser lane has no filesystem capability (target the native lane)");
    return nodeFs;
  }

  fsModule.read_file = function (path) {
    return needNodeFs().readFileSync(String(path), "utf8");
  };
  fsModule.write_file = function (path, text) {
    needNodeFs().writeFileSync(String(path), String(text), "utf8");
    return String(path);
  };
  fsModule.append_file = function (path, text) {
    needNodeFs().appendFileSync(String(path), String(text), "utf8");
    return String(path);
  };
  fsModule.delete_file = function (path) {
    try {
      needNodeFs().unlinkSync(String(path));
      return true;
    } catch (e) {
      return false;
    }
  };
  fsModule.file_exists = function (path) {
    return needNodeFs().existsSync(String(path));
  };
  fsModule.file_size = function (path) {
    try {
      return needNodeFs().statSync(String(path)).size;
    } catch (e) {
      return -1;
    }
  };
  fsModule.list_dir = function (path) {
    return needNodeFs().readdirSync(String(path));
  };
  fsModule.make_dir = function (path) {
    try {
      needNodeFs().mkdirSync(String(path), { recursive: true });
      return true;
    } catch (e) {
      return false;
    }
  };
  fsModule.remove_dir = function (path) {
    try {
      needNodeFs().rmSync(String(path), { recursive: true, force: true });
      return true;
    } catch (e) {
      return false;
    }
  };
  fsModule.rename_file = function (oldPath, newPath) {
    try {
      needNodeFs().renameSync(String(oldPath), String(newPath));
      return true;
    } catch (e) {
      return false;
    }
  };
  fsModule.copy_file = function (src, dst) {
    try {
      needNodeFs().copyFileSync(String(src), String(dst));
      return true;
    } catch (e) {
      return false;
    }
  };
  fsModule.join_path = function (a, b) {
    if (nodePath) return nodePath.join(String(a), String(b));
    return String(a).replace(/[\\/]+$/, "") + "/" + String(b);
  };
  fsModule.basename = function (path) {
    if (nodePath) return nodePath.basename(String(path));
    return String(path).split(/[\\/]/).pop();
  };
  fsModule.dirname = function (path) {
    if (nodePath) return nodePath.dirname(String(path));
    return String(path).split(/[\\/]/).slice(0, -1).join("/");
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);