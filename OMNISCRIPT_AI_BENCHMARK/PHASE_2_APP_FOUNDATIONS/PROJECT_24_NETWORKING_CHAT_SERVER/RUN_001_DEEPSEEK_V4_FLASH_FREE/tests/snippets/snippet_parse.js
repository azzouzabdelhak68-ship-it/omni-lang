// Protocol parsing: pure parse_message produces the structured record
// (sender, channel, payload, timestamp); server-side send stamps a timestamp.
globalThis.__RESULT__ = (async () => {
  const parsed = parse_message(
    '{"sender":"nina","channel":"general","payload":"hi","timestamp":1723900000000}'
  );
  const srv = await start_server();
  await connect_client(srv, "nina", "general");
  await connect_client(srv, "omar", "general");
  const sendStatus = await send_message(srv, "nina", "general", "hello from nina");
  const fullLog = JSON.parse(JSON.parse(await get_messages(srv)).messages);
  const first = fullLog.length ? fullLog[0] : null;
  const second = fullLog.length > 1 ? fullLog[1] : null;
  return {
    parsedSender: parsed.sender,
    parsedChannel: parsed.channel,
    parsedPayload: parsed.payload,
    parsedTimestamp: parsed.timestamp,
    sendStatus: sendStatus,
    logCount: fullLog.length,
    storedSender: first ? first.sender : null,
    storedPayload: first ? first.payload : null,
    storedChannel: first ? first.channel : null,
    storedTimestampType: first ? typeof first.timestamp : null,
    storedTimestampPositive: first ? first.timestamp > 0 : null,
    orderSecondSender: second ? second.sender : null,
  };
})();