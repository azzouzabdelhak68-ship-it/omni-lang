// End-to-end timeout enforcement: a slow stub server exceeds the budget.
globalThis.__RESULT__ = (async () => {
  const net = omnisys.net;
  const http = omnisys.http;
  const slowServer = net.server(function (req) {
    const end = Date.now() + 40;
    while (Date.now() < end) {}
    return net.response_json(200, { id: 1 });
  });
  http.__registerInproc("slow", slowServer);
  const out = await fetch_users("inproc://slow", 5);
  const fast = await fetch_users("inproc://slow", 100000);
  return { slowCode: out.code, fastCode: fast.code };
})();