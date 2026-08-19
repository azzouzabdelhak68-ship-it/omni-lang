// Request construction: POST with JSON body produced by serialize_body.
(function () {
  const body = serialize_body({ id: 42, name: "Ada", email: "ada@example.com" });
  const post = build_post_request("https://api.example.com/users", body);
  globalThis.__RESULT__ = {
    method: post.method,
    url: post.url,
    headers: post.headers,
    body: post.body,
    bodyIsJson: JSON.parse(post.body).id === 42,
  };
})();