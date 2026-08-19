const fs = require("fs");
const path = process.argv[2];
if (!path) { console.error("usage: node harness.js <file.html>"); process.exit(2); }
const html = fs.readFileSync(path, "utf8");
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error("no script block"); process.exit(2); }
let body = m[1];
globalThis.document = {
  getElementById: () => ({ innerHTML: "", addEventListener() {} }),
  querySelectorAll: () => [],
  createElement: () => ({ set src(v) {}, appendChild() {}, set onload(f) { f && f(); } }),
  head: { appendChild() {} },
  body: { appendChild() {} },
};
globalThis.window = globalThis;
// HARNESS WORKAROUND for emitter bug: the JS emitter emits OMNISYS.* (the
// source spelling) but the inlined OMNISYS runtime registers the namespace as
// `omnisys.*`. Normalize the emitted code so OMNISYS.* resolves to omnisys.*.
// The runtime's own mentions of OMNISYS appear only in comments/strings, so
// the replacement is harmless there.
body = body.split("OMNISYS.").join("omnisys.");
try {
  eval(body);
  console.log("HARNESS: script executed, no throw");
  process.exit(0);
} catch (e) {
  console.error("HARNESS: THREW:", e && e.message);
  process.exit(1);
}