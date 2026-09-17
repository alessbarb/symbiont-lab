// Observatory-only aggregation of exported facts. Never infer an edge or
// lineage record without an underlying runtime event.
const MAX_EVENTS = 4096;
function createCommunicationAggregator(maxEvents = MAX_EVENTS) {
  const events = new Map(); const groundingEvents = new Map(); let historyTruncated = false; let earliestAvailableTick = null;
  function ingest(telemetry, sourceInstanceId = "local") {
    if (!telemetry || !Array.isArray(telemetry.events)) return;
    telemetry.events.forEach(event => {
      if (!event?.eventId || events.has(`${sourceInstanceId}:${event.eventId}`)) return;
      events.set(`${sourceInstanceId}:${event.eventId}`, { ...event, sourceInstanceId });
    });
    (Array.isArray(telemetry.groundingEvents) ? telemetry.groundingEvents : []).forEach(event => {
      if (!event?.eventId || groundingEvents.has(`${sourceInstanceId}:${event.eventId}`)) return;
      groundingEvents.set(`${sourceInstanceId}:${event.eventId}`, { ...event, sourceInstanceId });
    });
    if (telemetry.historyTruncated === true && Number.isInteger(telemetry.earliestAvailableTick)) {
      for (const [key, event] of events) {
        if (event.sourceInstanceId === sourceInstanceId && event.tick < telemetry.earliestAvailableTick) events.delete(key);
      }
      for (const [key, event] of groundingEvents) {
        if (event.sourceInstanceId === sourceInstanceId && event.tick < telemetry.earliestAvailableTick) groundingEvents.delete(key);
      }
    }
    historyTruncated ||= telemetry.historyTruncated === true;
    const ticks = [...events.values()].map(event => event.tick).filter(Number.isInteger);
    earliestAvailableTick = ticks.length ? Math.min(...ticks) : (telemetry.earliestAvailableTick ?? null);
    while (events.size > maxEvents) { events.delete(events.keys().next().value); historyTruncated = true; }
  }
  function snapshot() {
    const list = [...events.values()].sort((a, b) => a.tick - b.tick || a.eventId.localeCompare(b.eventId));
    const grounding = [...groundingEvents.values()].sort((a, b) => a.tick - b.tick || a.eventId.localeCompare(b.eventId));
    const edgeMap = new Map();
    list.filter(event => ["DELIVER", "RECEIVE", "RETRANSMIT"].includes(event.kind)).forEach(event => {
      const key = `${event.senderId}\0${event.receiverId}`;
      const edge = edgeMap.get(key) ?? { senderId: event.senderId, receiverId: event.receiverId, count: 0, firstTick: event.tick, lastTick: event.tick, messages: new Set() };
      edge.count++; edge.firstTick = Math.min(edge.firstTick, event.tick); edge.lastTick = Math.max(edge.lastTick, event.tick); edge.messages.add(event.messageId); edgeMap.set(key, edge);
    });
    return { events: list, groundingEvents: grounding,
      edges: [...edgeMap.values()].map(edge => ({ ...edge, messages: [...edge.messages].sort() })),
      messages: aggregateMessages(list), timeline: deriveTimeline(list), summary: summarize(list),
      historyTruncated, earliestAvailableTick };
  }
  function clear() { events.clear(); groundingEvents.clear(); historyTruncated = false; earliestAvailableTick = null; }
  return { ingest, snapshot, clear };
}
function deriveTimeline(events) {
  const first = new Map(); const seen = new Map();
  events.forEach(event => {
    const key = event.messageId;
    if (!first.has(key)) first.set(key, event);
    if (!seen.has(key)) seen.set(key, new Set());
    seen.get(key).add(event.senderId);
  });
  const rows = [];
  first.forEach((event, messageId) => rows.push({ kind: "FIRST_EMISSION", tick: event.tick, messageId, organismId: event.senderId }));
  seen.forEach((senders, messageId) => { if (senders.size > 1) {
    const event = events.find(item => item.messageId === messageId && item.senderId !== first.get(messageId)?.senderId);
    if (event) rows.push({ kind: "FIRST_MULTI_SENDER_USE", tick: event.tick, messageId, organismId: event.senderId });
  }});
  return rows.sort((a, b) => a.tick - b.tick || a.messageId.localeCompare(b.messageId));
}
function summarize(events) {
  const messages = events.filter(event => ["DELIVER", "RECEIVE", "RETRANSMIT"].includes(event.kind));
  const silent = events.filter(event => event.kind === "SILENCE").length;
  return { communicationEvents: events.length, deliveredEvents: messages.length, silenceEvents: silent,
    communicatingOrganisms: new Set(messages.flatMap(event => [event.senderId, event.receiverId])).size,
    uniqueSymbols: new Set(messages.flatMap(event => event.symbols ?? [])).size,
    uniqueMessages: new Set(messages.map(event => event.messageId)).size,
    meanMessageLength: messages.length ? messages.reduce((sum, event) => sum + (event.messageLength ?? event.symbols?.length ?? 0), 0) / messages.length : 0,
    deliveryRate: events.length ? messages.length / events.length : 0 };
}
function aggregateMessages(events) {
  const map = new Map();
  events.forEach(event => {
    const row = map.get(event.messageId) ?? { messageId: event.messageId, symbols: event.symbols, firstTick: event.tick, lastTick: event.tick, useCount: 0, senders: new Set(), receivers: new Set(), retransmissions: 0, cost: 0 };
    row.useCount++; row.firstTick = Math.min(row.firstTick, event.tick); row.lastTick = Math.max(row.lastTick, event.tick); row.senders.add(event.senderId); row.receivers.add(event.receiverId); row.cost += event.cost;
    if (event.kind === "RETRANSMIT") row.retransmissions++;
    map.set(event.messageId, row);
  });
  return [...map.values()].map(row => ({ ...row, senders: [...row.senders].sort(), receivers: [...row.receivers].sort() }));
}
function aggregateCommunicationTelemetry(telemetry, sourceInstanceId = "local") {
  const aggregator = createCommunicationAggregator();
  aggregator.ingest(telemetry, sourceInstanceId);
  return aggregator.snapshot();
}
export { aggregateCommunicationTelemetry, createCommunicationAggregator };
