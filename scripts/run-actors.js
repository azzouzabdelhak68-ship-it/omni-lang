"use strict";

/**
 * run-actors.js — run an OmniScript actor program end-to-end.
 *
 * Usage: node scripts/run-actors.js <emitted.html>
 *
 * The OmniScript JS emitter produces a self-contained HTML document. This
 * harness extracts the embedded <script>, binds the `sim.actor` runtime as the
 * global `sim`, stubs the browser DOM (`document`/`window`) the emitted
 * renderer expects, and executes the program in the current Node context.
 * `console.log` output (from `show` and behaviors) is forwarded to stdout.
 *
 * Exit codes: 0 success, 1 the actor program threw, 2 bad usage.
 */

const fs = require("fs");
const vm = require("vm");

const { createRuntime } = require("../simulation_engine/runtime.js");

const htmlPath = process.argv[2];
if (!htmlPath) {
  console.error("usage: node scripts/run-actors.js <emitted.html>");
  process.exit(2);
}

const html = fs.readFileSync(htmlPath, "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) {
  console.error("run-actors: no <script> block found in " + htmlPath);
  process.exit(2);
}
const code = match[1];

const logs = [];
global.console = Object.assign({}, console, {
  log: (...args) => {
    logs.push(args.map(String).join(" "));
  },
});
global.sim = createRuntime().sim;
global.document = {
  getElementById: () => ({ innerHTML: "" }),
  querySelectorAll: () => [],
};
global.window = new Proxy({}, { get: () => () => {} });

try {
  vm.runInThisContext(code, { filename: htmlPath });
} catch (err) {
  console.error("run-actors: actor program failed: " + (err && err.stack ? err.stack : err));
  process.exit(1);
}

if (logs.length) {
  process.stdout.write(logs.join("\n") + "\n");
}
process.exit(0);