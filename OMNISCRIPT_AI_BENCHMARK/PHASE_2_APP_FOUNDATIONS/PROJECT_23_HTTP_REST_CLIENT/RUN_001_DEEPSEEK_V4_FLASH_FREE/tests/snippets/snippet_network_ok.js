// End-to-end network path: GET via a registered inproc:// stub server.
globalThis.__RESULT__ = (async () => {
  const net = omnisys.net;
  const http = omnisys.http;
  const server = net.server(function (req) {
    return net.response_json(200, { id: 1, name: "Grace", email: "grace@x.com" });
  });
  http.__registerInproc("api", server);
  const out = await fetch_users("inproc://api", 1000);
  return {
    code: out.code,
    message: out.message,
    parsed: parse_user(
      "{\"id\":1,\"name\":\"Grace\",\"email\":\"grace@x.com\"}"
    ).name,
  };
})();