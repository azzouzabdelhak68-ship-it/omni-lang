// Request construction: GET with query string and headers.
(function () {
  const req = build_get_request("https://api.example.com", "page=1&size=10");
  globalThis.__RESULT__ = {
    method: req.method,
    url: req.url,
    headers: req.headers,
    body: req.body,
  };
})();