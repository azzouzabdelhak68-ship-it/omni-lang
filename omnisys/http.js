"use strict";
/**
 * OMNISYS.http — high-level HTTP client/server built on the OMNISYS.net
 * portable transport. `inproc://` URLs dispatch to a registered in-process
 * server (deterministic, testable); other URLs are routed through the
 * registered client transport escape.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const http = (omnisys.http = omnisys.http || {});
  const core = omnisys.core;

  const registry = {};

  function register(name, server) {
    registry[String(name)] = server;
    return server;
  }

  function parseUrl(url) {
    const text = String(url);
    if (text.startsWith("inproc://")) {
      const rest = text.slice("inproc://".length);
      const slash = rest.indexOf("/");
      if (slash === -1) return { host: rest, path: "/", scheme: "inproc" };
      return { host: rest.slice(0, slash), path: rest.slice(slash), scheme: "inproc" };
    }
    const m = text.match(/^([a-z][a-z0-9+.-]*):\/\/([^/]+)(.*)$/);
    if (!m) core.panic("http: malformed url: " + url);
    return { scheme: m[1], host: m[2], path: m[3] || "/" };
  }

  http.client = function () {
    return { tag: "http.client", transport: "portable" };
  };

  http.send = function (client, method, url, body, timeout) {
    return http.dispatch(method, url, body, timeout);
  };
  http.get = function (url, timeout) {
    return http.dispatch("GET", url, null, timeout);
  };
  http.post = function (url, body, timeout) {
    return http.dispatch("POST", url, body, timeout);
  };
  http.put = function (url, body, timeout) {
    return http.dispatch("PUT", url, body, timeout);
  };
  http.delete = function (url, timeout) {
    return http.dispatch("DELETE", url, null, timeout);
  };

  http.dispatch = function (method, url, body, timeout) {
    const target = parseUrl(url);
    const server = registry[target.host];
    if (target.scheme === "inproc" && server) {
      const net = omnisys.net;
      const result = net.request(server, method, target.path, body === undefined || body === null ? "" : String(body));
      return Promise.resolve(result);
    }
    if (typeof http.__transport === "function") {
      return http.__transport(method, url, body, timeout);
    }
    return Promise.reject(new Error("http: no transport for scheme '" + target.scheme + "' (register an inproc:// server or set http.__transport)"));
  };

  http.json_get = function (url, timeout) {
    const res = http.get(url, timeout);
    return JSON.parse(res.body);
  };
  http.json_post = function (url, value, timeout) {
    const res = http.post(url, JSON.stringify(value), timeout);
    return JSON.parse(res.body);
  };
  http.redirect = function (location, status) {
    return { status: status || 302, headers: { location: String(location) }, body: "" };
  };
  http.not_found = function (body) {
    return { status: 404, headers: {}, body: String(body) };
  };
  http.response = function (status, body) {
    return { status: status, headers: {}, body: String(body) };
  };
  http.response_json = function (status, value) {
    return { status: status, headers: { "content-type": "application/json" }, body: JSON.stringify(value) };
  };
  http.register = function (name, server) {
    return register(String(name), server);
  };

  // Test/escape hook: bind an in-process server to a host name.
  http.__registerInproc = register;
  http.__parseUrl = parseUrl;
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);