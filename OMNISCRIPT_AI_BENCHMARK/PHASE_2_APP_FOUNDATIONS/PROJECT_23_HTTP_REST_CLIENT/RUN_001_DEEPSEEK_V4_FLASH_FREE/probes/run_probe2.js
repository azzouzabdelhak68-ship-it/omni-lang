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
  setTimeout,
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

(async () => {
  // register an in-process server AFTER eval (app block already ran; no network there)
  const http = sandbox.omnisys.http;
  const net = sandbox.omnisys.net;
  const server = net.server(function (req) {
    return net.response_json(200, { id: 1, name: "Grace", email: "grace@x.com" });
  });
  http.__registerInproc("api", server);

  const out = await sandbox.fetch();
  console.log("fetch() resolved =>", JSON.stringify(out));

  // now try a GET against the inproc server through http.get directly
  const res = http.get("inproc://api/users");
  console.log("http.get status =>", res.status, "body =>", res.body);
})().catch((e) => {
  console.error("HARNESS ERROR:", e && e.message);
  process.exit(3);
});