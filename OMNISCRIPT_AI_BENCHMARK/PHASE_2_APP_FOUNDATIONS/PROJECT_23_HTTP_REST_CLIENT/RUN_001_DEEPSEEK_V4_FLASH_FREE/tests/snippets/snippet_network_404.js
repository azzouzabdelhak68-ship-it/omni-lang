// End-to-end network path: HTTP 404 from the stub server.
globalThis.__RESULT__ = (async () => {
  const net = omnisys.net;
  const http = omnisys.http;
  const server = net.server(function (req) {
    return net.response(404, "missing");
  });
  http.__registerInproc("missing", server);
  const out = await fetch_users("inproc://missing", 1000);
  return { code: out.code, statusIsClassified: out.code === "not_found" };
})();