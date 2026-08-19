// End-to-end network path: POST body routing through create_user.
globalThis.__RESULT__ = (async () => {
  const net = omnisys.net;
  const http = omnisys.http;
  let captured = null;
  const server = net.server(function (req) {
    captured = { method: req.method, path: req.path, body: req.body };
    return net.response_json(201, { id: 9, name: "Grace", email: "grace@x.com" });
  });
  http.__registerInproc("api", server);
  const out = await create_user(
    "inproc://api",
    { id: 9, name: "Grace", email: "grace@x.com" },
    1000
  );
  return {
    code: out.code,
    capturedMethod: captured.method,
    capturedPath: captured.path,
    capturedBody: captured.body,
    bodyIsJson: JSON.parse(captured.body).email === "grace@x.com",
  };
})();