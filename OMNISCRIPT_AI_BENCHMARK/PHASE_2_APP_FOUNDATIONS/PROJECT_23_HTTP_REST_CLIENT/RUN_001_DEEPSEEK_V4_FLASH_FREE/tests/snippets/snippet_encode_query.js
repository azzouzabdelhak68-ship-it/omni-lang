// Query string encoding via list_join.
(function () {
  const q = encode_query(["page=1", "size=10", "active=true"]);
  globalThis.__RESULT__ = { query: q };
})();