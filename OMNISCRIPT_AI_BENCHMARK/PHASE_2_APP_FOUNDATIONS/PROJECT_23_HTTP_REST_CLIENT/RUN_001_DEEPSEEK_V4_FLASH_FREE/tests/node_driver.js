"use strict";
// Node driver for the compiled OmniScript artifact.
// Usage: node node_driver.js <built.html> <snippet.js>
// - evals the artifact's <script> body in a VM sandbox (with DOM stubs)
// - evals the snippet in the same sandbox
// - prints JSON.stringify(sandbox.__RESULT__)
// Snippets must set globalThis.__RESULT__ to a JSON-serializable value.
const fs = require("fs");
const vm = require("vm");

const htmlPath = process.argv[2];
const snippetPath = process.argv[3];
if (!htmlPath || !snippetPath) {
  console.error("usage: node node_driver.js <html> <snippet.js>");
  process.exit(1);
}

const html = fs.readFileSync(htmlPath, "utf8");
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) {
  console.error("no script tag found in " + htmlPath);
  process.exit(1);
}

const sandbox = {
  console: {
    log: () => {},
    error: () => {},
    warn: () => {},
  },
  document: {
    getElementById: () => ({ innerHTML: "", addEventListener() {} }),
    querySelectorAll: () => [],
  },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.self = sandbox;
sandbox.__RESULT__ = null;
vm.createContext(sandbox);

try {
  vm.runInContext(m[1], sandbox, { filename: "api_client.js" });
  const snippet = fs.readFileSync(snippetPath, "utf8");
  vm.runInContext(snippet, sandbox, { filename: snippetPath });
} catch (e) {
  const msg = e && e.stack ? e.stack : String(e);
  console.error("HARNESS_ERROR: " + msg);
  process.exit(2);
}

(async () => {
  let result = sandbox.__RESULT__;
  if (result && typeof result.then === "function") {
    result = await result;
  }
  console.log(JSON.stringify(result));
})().catch((e) => {
  console.error("HARNESS_ERROR: " + (e && e.stack ? e.stack : e));
  process.exit(2);
});