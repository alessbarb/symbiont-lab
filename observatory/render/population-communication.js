import { state } from "../state/store.js";
import { aggregateCommunicationTelemetry } from "../communication/aggregator.js";

const filters = { sender: "", receiver: "", message: "", kind: "", minTick: "", maxTick: "", length: "" };
// Fleet aggregation is authoritative only while a real fleet is connected.
// A local snapshot may arrive in the same page and must remain visible even
// if the fleet transport has an empty/stale aggregate; neither path may
// invent edges or lineage.
function telemetry() {
  if (state.localCommunication?.events?.length) {
    return state.localCommunication ?? { events: [], groundingEvents: [], edges: [], messages: [], timeline: [], historyTruncated: false };
  }
  if (state.populationTelemetry?.events?.length) return aggregateCommunicationTelemetry(state.populationTelemetry);
  if (state.fleetConnected && Array.isArray(state.fleetInstances) && state.fleetInstances.length) {
    return state.fleetCommunication ?? { events: [], groundingEvents: [], edges: [], messages: [], timeline: [], historyTruncated: false };
  }
  return state.populationTelemetry ?? state.fleetCommunication ?? { events: [], groundingEvents: [], edges: [], messages: [], timeline: [], historyTruncated: false };
}
function esc(value) { const node = document.createElement("span"); node.textContent = String(value ?? ""); return node.innerHTML; }
function messageLabel(item) { return (item.symbols ?? []).map(symbol => esc(symbol)).join(" ") || "—"; }
function matches(event) {
  const message = messageLabel(event);
  return (!filters.sender || event.senderId === filters.sender) && (!filters.receiver || event.receiverId === filters.receiver)
    && (!filters.message || message.includes(filters.message) || event.messageId === filters.message)
    && (!filters.kind || event.kind === filters.kind) && (!filters.minTick || event.tick >= Number(filters.minTick))
    && (!filters.maxTick || event.tick <= Number(filters.maxTick)) && (!filters.length || event.messageLength === Number(filters.length));
}
function graph(edges) {
  if (!edges.length) return `<p class="telemetry-empty">No observed communication edges.</p>`;
  const ids = [...new Set(edges.flatMap(edge => [edge.senderId, edge.receiverId]))];
  const points = new Map(ids.map((id, index) => [id, { x: 70 + (index % 5) * 150, y: 45 + Math.floor(index / 5) * 80 }]));
  const lines = edges.map(edge => { const a = points.get(edge.senderId), b = points.get(edge.receiverId); return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" class="telemetry-edge" marker-end="url(#telemetry-arrow)"/><text x="${(a.x + b.x) / 2}" y="${(a.y + b.y) / 2 - 5}" class="telemetry-edge-label">${esc(edge.count)}</text>`; }).join("");
  const nodes = ids.map(id => { const p = points.get(id); return `<g><circle cx="${p.x}" cy="${p.y}" r="18" class="telemetry-node"/><text x="${p.x}" y="${p.y + 4}" text-anchor="middle" class="telemetry-node-label">${esc(id)}</text></g>`; }).join("");
  return `<svg class="communication-graph" viewBox="0 0 700 ${Math.max(120, Math.ceil(ids.length / 5) * 80)}" role="img" aria-label="Observed population communication graph"><defs><marker id="telemetry-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z"/></marker></defs>${lines}${nodes}</svg>`;
}
function renderPopulationCommunication() {
  const root = document.querySelector("#population-communication-panel"); if (!root) return;
  const data = telemetry(); const allEvents = data.events ?? []; const events = allEvents.filter(matches);
  const edges = (data.edges ?? []).filter(edge => !filters.sender || edge.senderId === filters.sender).filter(edge => !filters.receiver || edge.receiverId === filters.receiver);
  const messages = data.messages ?? []; const grounding = data.groundingEvents ?? [];
  const truncation = data.historyTruncated ? `<p class="telemetry-warning">History truncated · earliest available tick ${esc(data.earliestAvailableTick ?? "unknown")}</p>` : "";
  const controls = `<div class="telemetry-filters" aria-label="Communication telemetry filters"><label>Sender <input data-telemetry-filter="sender" value="${esc(filters.sender)}"></label><label>Receiver <input data-telemetry-filter="receiver" value="${esc(filters.receiver)}"></label><label>Message <input data-telemetry-filter="message" value="${esc(filters.message)}"></label><label>Event <select data-telemetry-filter="kind"><option value="">All</option>${["DELIVER", "RECEIVE", "RETRANSMIT", "EMIT", "SILENCE"].map(kind => `<option value="${kind}" ${filters.kind === kind ? "selected" : ""}>${kind}</option>`).join("")}</select></label><label>Tick ≥ <input type="number" min="0" data-telemetry-filter="minTick" value="${esc(filters.minTick)}"></label><label>Tick ≤ <input type="number" min="0" data-telemetry-filter="maxTick" value="${esc(filters.maxTick)}"></label><label>Length <input type="number" min="1" max="4" data-telemetry-filter="length" value="${esc(filters.length)}"></label></div>`;
  const eventRows = events.slice(-64).reverse().map(event => `<tr><td>${esc(event.tick)}</td><td>${esc(event.senderId)} → ${esc(event.receiverId)}</td><td>${esc(event.kind)}</td><td><code>${messageLabel(event)}</code></td><td>${esc(event.messageLength ?? event.symbols?.length)}</td><td>${esc(event.cost)}</td><td>${esc(event.deliveryStatus)}</td></tr>`).join("");
  const messageRows = messages.slice(0, 64).map(item => `<tr><td><code>${messageLabel(item)}</code></td><td>${esc(item.firstTick)}–${esc(item.lastTick)}</td><td>${esc(item.useCount)}</td><td>${esc(item.senders.length)}</td><td>${esc(item.receivers.length)}</td><td>${esc(item.retransmissions)}</td></tr>`).join("");
  const groundingRows = grounding.slice(-32).reverse().map(item => `<tr><td>${esc(item.tick)}</td><td>${esc(item.organismId)}</td><td><code>${esc(item.messageId)}</code></td><td>${esc(item.associationStrengthBefore)} → ${esc(item.associationStrengthAfter)}</td></tr>`).join("");
  const timeline = (data.timeline ?? []).slice(-32).reverse().map(item => `<li><b>t${esc(item.tick)}</b> ${esc(item.kind)} · <code>${esc(item.messageId)}</code> · ${esc(item.organismId)}</li>`).join("");
  root.innerHTML = `<div class="panel-heading"><h2>Population Communication</h2><p>Factual exported telemetry · read only</p></div>${truncation}${controls}<div class="communication-summary"><b>${events.length}</b> visible events · <b>${edges.length}</b> observed edges · <b>${messages.length}</b> messages</div><h3>Communication Live</h3><div class="table-scroll"><table class="telemetry-table"><thead><tr><th>Tick</th><th>Route</th><th>Event</th><th>Opaque message</th><th>Length</th><th>Cost</th><th>Delivery</th></tr></thead><tbody>${eventRows || `<tr><td colspan="7">No communication events in the available history.</td></tr>`}</tbody></table></div><h3>Population Communication Graph</h3>${graph(edges)}<div class="table-scroll"><table class="telemetry-table"><thead><tr><th>Observed edge</th><th>Events</th><th>Ticks</th><th>Messages</th></tr></thead><tbody>${edges.map(edge => `<tr><td>${esc(edge.senderId)} → ${esc(edge.receiverId)}</td><td>${esc(edge.count)}</td><td>${esc(edge.firstTick)}–${esc(edge.lastTick)}</td><td>${esc(edge.messages.join(", "))}</td></tr>`).join("") || `<tr><td colspan="4">No observed communication edges.</td></tr>`}</tbody></table></div><h3>Convention Explorer</h3><div class="table-scroll"><table class="telemetry-table"><thead><tr><th>Opaque message</th><th>Ticks</th><th>Uses</th><th>Senders</th><th>Receivers</th><th>Retransmissions</th></tr></thead><tbody>${messageRows || `<tr><td colspan="6">No messages in the available history.</td></tr>`}</tbody></table></div><h3>Grounding events</h3><div class="table-scroll"><table class="telemetry-table"><thead><tr><th>Tick</th><th>Organism</th><th>Message</th><th>Association</th></tr></thead><tbody>${groundingRows || `<tr><td colspan="4">No grounding events exported.</td></tr>`}</tbody></table></div><h3>Emergence Timeline</h3><ul class="telemetry-timeline">${timeline || "<li>No derived milestones in the available history.</li>"}</ul><p class="telemetry-disclaimer">Messages are opaque. Graph edges, lineage and milestones are derived only from exported events. No meaning or historical relation is inferred without an exported event.</p>`;
  root.querySelectorAll("[data-telemetry-filter]").forEach(input => input.addEventListener("input", event => { filters[event.target.dataset.telemetryFilter] = event.target.value; renderPopulationCommunication(); }));
}
export { renderPopulationCommunication };
