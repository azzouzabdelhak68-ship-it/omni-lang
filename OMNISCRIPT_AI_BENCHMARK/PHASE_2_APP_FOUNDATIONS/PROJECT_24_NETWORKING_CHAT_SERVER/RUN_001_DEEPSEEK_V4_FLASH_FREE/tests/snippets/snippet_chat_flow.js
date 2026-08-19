// End-to-end chat server flow: lifecycle, live registry, channel-scoped
// broadcast, duplicate connect, disconnect, clean shutdown.
globalThis.__RESULT__ = (async () => {
  const srv = await start_server();
  const results = {};
  results.connectAlive = await connect_client(srv, "alice", "general");
  results.connectBob = await connect_client(srv, "bob", "general");
  results.connectCarol = await connect_client(srv, "carol", "general");
  results.connectDave = await connect_client(srv, "dave", "offtopic");
  const clientsBefore = JSON.parse(await list_clients(srv));
  results.duplicateAlice = await connect_client(srv, "alice", "general");

  // alice broadcasts to channel "general"; bob and carol are other
  // same-channel peers; dave (offtopic) and alice herself are excluded.
  const sendBody = JSON.stringify({
    sender: "alice",
    channel: "general",
    payload: "hello team",
  });
  results.sendStatus = await send_request(srv, "POST", "/send", sendBody);
  const broadcast = JSON.parse(await send_request_body(srv, "POST", "/send", sendBody));

  const generalLog = JSON.parse(JSON.parse(await read_channel(srv, "general")).messages);
  const offtopicLog = JSON.parse(JSON.parse(await read_channel(srv, "offtopic")).messages);

  results.disconnectBob = await disconnect_client(srv, "bob");
  const clientsAfter = JSON.parse(await list_clients(srv));
  results.disconnectGhost = await disconnect_client(srv, "ghost");

  results.shutdown = await shutdown_server(srv);
  results.afterShutdown = await connect_client(srv, "zoe", "general");

  return {
    statuses: results,
    clientsBefore: clientsBefore.clients,
    clientsAfter: clientsAfter.clients,
    broadcastOk: broadcast.ok,
    broadcastSender: broadcast.message.sender,
    broadcastChannel: broadcast.message.channel,
    broadcastPayload: broadcast.message.payload,
    broadcastTimestampType: typeof broadcast.message.timestamp,
    broadcastRecipients: broadcast.recipients,
    generalLogCount: generalLog.length,
    generalLogPayload: generalLog.length ? generalLog[0].payload : null,
    generalLogSender: generalLog.length ? generalLog[0].sender : null,
    generalLogTimestampType: generalLog.length ? typeof generalLog[0].timestamp : null,
    offtopicLogCount: offtopicLog.length,
  };
})();