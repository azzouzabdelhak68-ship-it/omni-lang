// Error & timeout classification over stubbed responses.
(function () {
  const ok = classify_error(200, '{"id":1}', 5, 1000);
  const created = classify_error(201, '{"id":1}', 5, 1000);
  const notFound = classify_error(404, "nope", 5, 1000);
  const serverErr = classify_error(503, "boom", 5, 1000);
  const httpErr = classify_error(418, "teapot", 5, 1000);
  const connFail = classify_error(0, "", 5, 1000);
  const malformed = classify_error(200, "", 5, 1000);
  const timedOut = classify_error(200, '{"id":1}', 500, 100);
  globalThis.__RESULT__ = {
    ok: ok.code,
    created: created.code,
    notFound: notFound.code,
    serverErr: serverErr.code,
    httpErr: httpErr.code,
    connFail: connFail.code,
    malformed: malformed.code,
    timedOut: timedOut.code,
  };
})();