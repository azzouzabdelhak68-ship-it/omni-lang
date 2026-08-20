const fs = require("fs");
const vm = require("vm");
const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) { console.error("no script block"); process.exit(2); }
const code = match[1];
const logs = [];
global.console = Object.assign({}, console, { log: (...a) => logs.push(a.map(String).join(" ")) });
global.document = { getElementById: () => ({ innerHTML: "", addEventListener: () => {} }), querySelectorAll: () => [] };
global.name = "";
global.window = new Proxy({}, { get: () => () => {} });
global.require = require;
try {
  vm.runInThisContext(code, { filename: htmlPath });
} catch (err) {
  console.error("SYNC FAIL: " + (err && err.stack ? err.stack : err));
  process.exit(1);
}
process.on("unhandledRejection", (reason, p) => {
  console.error("UNHANDLED REJECTION: " + (reason && reason.stack ? reason.stack : reason));
  console.log("LOGS SO FAR: " + JSON.stringify(logs));
  process.exit(2);
});
setTimeout(() => {
  console.log("FINAL LOGS: " + JSON.stringify(logs));
  process.exit(0);
}, 500);