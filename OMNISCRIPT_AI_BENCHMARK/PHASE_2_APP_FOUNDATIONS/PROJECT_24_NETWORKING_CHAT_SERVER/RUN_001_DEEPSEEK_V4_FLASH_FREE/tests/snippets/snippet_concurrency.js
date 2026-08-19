// Concurrency: the OMNISYS.net transport is synchronous and single-threaded,
// so arrivals are serialized by construction. This snippet simulates a burst
// of interleaved clients connecting and broadcasting, then verifies the
// registry and message log stayed consistent (no corruption, no lost
// updates). All requests complete in FIFO order because net.request invokes
// the handler synchronously.
globalThis.__RESULT__ = (async () => {
  const srv = await start_server();
  const out = { statuses: [] };
  const names = ["u01","u02","u03","u04","u05","u06","u07","u08","u09","u10"];

  // Burst A: every client joins the same channel (simulated concurrent joins).
  for (const n of names) {
    out.statuses.push(await connect_client(srv, n, "lobby"));
  }
  const registryAfterJoin = JSON.parse(await list_clients(srv));
  out.joinCount = registryAfterJoin.clients.split(",").filter(Boolean).length;

  // Duplicate join during the burst must still be rejected (idempotent check).
  out.duplicateInBurst = await connect_client(srv, "u05", "lobby");

  // Burst B: interleaved broadcasts; each sender except u01 is a recipient.
  for (const n of names.slice(1)) {
    out.statuses.push(await send_message(srv, n, "lobby", "hi from " + n));
  }
  const logAfter = JSON.parse(JSON.parse(await get_messages(srv)).messages);
  out.logCount = logAfter.length;
  out.lastSender = logAfter.length ? logAfter[logAfter.length - 1].sender : null;

  // Registry after the interleaved burst must still equal the join set.
  const registryAfter = JSON.parse(await list_clients(srv));
  out.registryStable = registryAfter.clients.split(",").length === out.joinCount;

  // All ten clients still present, in insertion order (map preserves order).
  out.registryTail = registryAfter.clients.split(",").slice(-2).join(",");
  return out;
})();