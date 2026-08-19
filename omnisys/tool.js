"use strict";
/**
 * OMNISYS.tool — language-service tooling. The Node lane bridges to the
 * `omni` compiler CLI via subprocess (`omni check`/`omni explain`) so
 * diagnostics are the compiler's own. Lightweight lexer helpers are pure JS.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const tool = (omnisys.tool = omnisys.tool || {});
  const core = omnisys.core;

  let childProcess = null;
  if (typeof require !== "undefined") {
    try {
      childProcess = require("child_process");
    } catch (e) {
      childProcess = null;
    }
  }

  const KEYWORDS = new Set([
    "when", "end", "if", "else", "then", "fn", "return", "show", "uses", "reads", "writes",
    "pure", "UI", "scene", "require", "ensure", "and", "or", "not", "is", "type", "for",
    "in", "break", "continue", "import", "true", "false", "none", "box", "sphere", "cylinder",
    "plane", "light", "camera",
  ]);

  tool.tokenize = function (code) {
    const tokens = [];
    const pattern = /[A-Za-z_][A-Za-z0-9_]*|"[^"]*"|'[^']*'|\d+(?:\.\d+)?|=>|>=|<=|[<>=:+*/,.\[\]{}()-]|\s+/g;
    let match;
    while ((match = pattern.exec(String(code))) !== null) {
      const value = match[0];
      if (/^\s+$/.test(value)) continue;
      tokens.push({
        value: value,
        kind: KEYWORDS.has(value) ? "keyword" : /^\d/.test(value) ? "number" : /^["']/.test(value) ? "text" : "identifier",
      });
    }
    return tokens;
  };

  function runOmni(args) {
    if (!childProcess) core.panic("tool: the browser lane cannot run the omni CLI (uses process)");
    const python = process.env.OMNI_PYTHON || "python";
    const command = [python, "-m", "omni_compiler.cli"].concat(args);
    const result = childProcess.spawnSync(python, ["-m", "omni_compiler.cli"].concat(args), {
      encoding: "utf8",
      timeout: 15000,
    });
    return { status: result.status, stdout: result.stdout || "", stderr: result.stderr || "" };
  }

  tool.check = function (path) {
    const result = runOmni(["check", String(path)]);
    let parsed = null;
    try {
      parsed = JSON.parse(result.stdout);
    } catch (e) {
      parsed = null;
    }
    return { path: String(path), ok: result.status === 0, diagnostic: parsed, stderr: result.stderr };
  };
  tool.explain = function (path) {
    const result = runOmni(["explain", String(path)]);
    let parsed = null;
    try {
      parsed = JSON.parse(result.stdout);
    } catch (e) {
      parsed = null;
    }
    return { path: String(path), ok: result.status === 0, diagnostic: parsed, stderr: result.stderr };
  };

  tool.line_count = function (code) {
    return String(code).split("\n").length;
  };
  tool.identifier_count = function (code) {
    return tool.tokenize(code).filter((t) => t.kind === "identifier").length;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);