// Typed response parsing: array payload into a List of typed Users.
(function () {
  const users = parse_users('[{"id":1,"name":"A","email":"a@x.com"},{"id":2,"name":"B","email":"b@x.com"}]');
  globalThis.__RESULT__ = {
    count: users.length,
    firstId: users[0].id,
    firstName: users[0].name,
    secondEmail: users[1].email,
  };
})();