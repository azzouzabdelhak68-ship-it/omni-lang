"use strict";

/**
 * run-omnisys.js — run an OmniScript program that imports OMNISYS.
 *
 * Usage: node scripts/run-omnisys.js <emitted.html>
 *
 * Extracts the embedded <script> of an emitted HTML file, binds the browser
 * DOM stubs the JS emitter expects, and executes the program in the current
 * Node context. The OMNISYS runtime is normally inlined by the emitter; when
 * a program was built without inlining, `omnisys` is bound from the Node
 * runtime aggregator as a fallback.
 *
 * Exit codes: 0 success, 1 the program threw, 2 bad usage.
 */

const fs = require("fs");
const vm = require("vm");

const htmlPath = process.argv[2];
if (!htmlPath) {
  console.error("usage: node scripts/run-omnisys.js <emitted.html>");
  process.exit(2);
}

const html = fs.readFileSync(htmlPath, "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) {
  console.error("run-omnisys: no <script> block found in " + htmlPath);
  process.exit(2);
}
const code = match[1];

const logs = [];
global.console = Object.assign({}, console, {
  log: (...args) => {
    logs.push(args.map(String).join(" "));
  },
});
global.document = {
  getElementById: () => ({ innerHTML: "", addEventListener: () => {} }),
  querySelectorAll: () => [],
};
// Browsers expose `name` as the implicit window.name global (default "").
// Emitted programs read it before any program assignment, so bind it here.
global.name = "";
global.window = new Proxy({}, { get: () => () => {} });

// Flat `sim.*` programs (v5.3/v3.4 ECS + actor) call `sim.*` without imports;
// the emitter never inlines this Node runtime, so bind it here.
try {
  global.sim = require("../simulation_engine/runtime.js").createRuntime().sim;
} catch (e) {
  // ignore: programs that do not use the flat sim.* API do not need it
}

if (code.indexOf("OMNISYS runtime") === -1) {
  try {
    global.omnisys = require("../omnisys/runtime.js");
  } catch (e) {
    console.error("run-omnisys: failed to bind omnisys runtime: " + e);
    process.exit(2);
  }
}

try {
  vm.runInThisContext(code, { filename: htmlPath });
} catch (err) {
  console.error("run-omnisys: program failed: " + (err && err.stack ? err.stack : err));
  process.exit(1);
}

if (logs.length) {
  process.stdout.write(logs.join("\n") + "\n");
}
process.exit(0);