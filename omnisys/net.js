"use strict";
/**
 * OMNISYS.net — networking. Portable core is an in-process, synchronous,
 * deterministic request/response model (server handler + middleware), which
 * is fully testable and used by OMNISYS.http. Real transport (TCP/TLS/HTTP on
 * the wire) is a future escape that keeps this same semantic API.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const net = (omnisys.net = omnisys.net || {});

  function makeResponse(status, body) {
    return { status: status, headers: {}, body: String(body) };
  }
  net.response = makeResponse;
  net.response_json = function (status, value) {
    return { status: status, headers: { "content-type": "application/json" }, body: JSON.stringify(value) };
  };
  net.status_of = function (response) {
    return response ? response.status : 0;
  };
  net.body_of = function (response) {
    return response ? response.body : "";
  };

  net.server = function (handler) {
    return { tag: "server", handler: handler, middlewares: [] };
  };
  net.start = function (server) {
    server.running = true;
    return server;
  };
  net.middleware = function (handler, middlewares) {
    let wrapped = handler;
    for (let i = middlewares.length - 1; i >= 0; i--) {
      const mw = middlewares[i];
      const next = wrapped;
      wrapped = function (req) {
        return mw(req, next);
      };
    }
    return function (req) {
      return wrapped(req);
    };
  };
  net.request = function (server, method, path, body) {
    if (!server.running) server.running = true;
    const req = {
      method: String(method).toUpperCase(),
      path: String(path),
      body: body === undefined || body === null ? "" : String(body),
      headers: {},
    };
    if (!server.handler) return makeResponse(501, "no handler");
    return server.handler(req);
  };
  net.get = function (server, path) {
    return net.request(server, "GET", path, null);
  };
  net.post = function (server, path, body) {
    return net.request(server, "POST", path, body);
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);