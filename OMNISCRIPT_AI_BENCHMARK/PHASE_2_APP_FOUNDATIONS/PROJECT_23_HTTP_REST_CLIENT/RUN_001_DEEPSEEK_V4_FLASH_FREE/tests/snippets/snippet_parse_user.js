// Typed response parsing: single object payload.
(function () {
  const u = parse_user('{"id":7,"name":"Grace","email":"grace@x.com"}');
  globalThis.__RESULT__ = {
    id: u.id,
    name: u.name,
    email: u.email,
  };
})();