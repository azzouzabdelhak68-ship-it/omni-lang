// Protocol validation: missing fields -> 400, duplicate connect -> 409,
// unconnected sender -> 404, unknown path -> 404, bad method -> 405.
globalThis.__RESULT__ = (async () => {
  const srv = await start_server();
  const out = {};
  out.connectEmpty = await send_request(srv, "POST", "/connect", "");
  out.connectNoChannel = await send_request(
    srv, "POST", "/connect",
    JSON.stringify({ client: "pia" })
  );
  out.connectOk = await connect_client(srv, "pia", "general");
  out.duplicate = await connect_client(srv, "pia", "general");
  out.sendNoSender = await send_request(srv, "POST", "/send", JSON.stringify({
    channel: "general", payload: "x",
  }));
  out.sendUnknownSender = await send_request(srv, "POST", "/send", JSON.stringify({
    sender: "ghost", channel: "general", payload: "x",
  }));
  out.readNoChannel = await send_request(srv, "POST", "/messages", JSON.stringify({}));
  out.unknownPath = await send_request(srv, "GET", "/nope", "");
  out.badMethod = await send_request(srv, "DELETE", "/clients", "");
  out.disconnectOk = await disconnect_client(srv, "pia");
  out.disconnectGhost = await disconnect_client(srv, "ghost");
  return out;
})();