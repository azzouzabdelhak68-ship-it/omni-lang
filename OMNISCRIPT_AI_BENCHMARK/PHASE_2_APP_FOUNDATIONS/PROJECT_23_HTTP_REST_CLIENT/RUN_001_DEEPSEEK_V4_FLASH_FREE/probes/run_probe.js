"use strict";
const fs = require("fs");
const vm = require("vm");

const html = fs.readFileSync(process.argv[2], "utf8");
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error("no script tag found"); process.exit(1); }

const sandbox = {
  console: console,
  document: {
    getElementById: () => ({ innerHTML: "" }),
    querySelectorAll: () => [],
  },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.self = sandbox;
vm.createContext(sandbox);
try {
  vm.runInContext(m[1], sandbox, { filename: "api_client.js" });
} catch (e) {
  console.error("EVAL ERROR:", e && e.message);
  process.exit(2);
}
const user = sandbox.parse_user('{"id":7,"name":"Ada","email":"ada@x.com"}');
console.log("parse_user =>", JSON.stringify(user));
const malformed = sandbox.omnisys.http.__parseUrl("inproc://api/users");
console.log("__parseUrl inproc =>", JSON.stringify(malformed));