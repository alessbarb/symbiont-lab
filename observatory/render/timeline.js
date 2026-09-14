import { state } from "../state/store.js";
import { palette, eventColor } from "./svg.js";
import { availableEvents, comparisonFor } from "../state/selectors.js";
import { advance } from "../ui/controls.js";

function renderTimeline() {
  const track = document.querySelector("#event-track"); track.replaceChildren();
  const scrubber = document.querySelector("#scrubber");
  const positionEl = document.querySelector("#position");
  const timestampEl = document.querySelector("#timestamp");
  const isLiveReal = state.mode === "live" && state.source !== "demo";

  if (isLiveReal) {
    scrubber.disabled = true;
    const currentTick = state.realTick ?? state.tick ?? 0;
    positionEl.textContent = `Live · tick ${currentTick}`;
    timestampEl.textContent = "Live stream";

    const windowStart = Math.max(0, currentTick - 59);
    const windowSpan = Math.max(1, currentTick - windowStart);

    const recentEvents = state.liveEvents.filter(e => e.tick >= windowStart && e.tick <= currentTick);
    recentEvents.forEach(event => {
      const dot = document.createElement("i");
      dot.className = "event-dot";
      const pct = ((event.tick - windowStart) / windowSpan) * 100;
      dot.style.left = `${pct.toFixed(1)}%`;
      dot.style.background = eventColor(event.type);
      dot.style.opacity = event.type === "perception" ? "0.4" : "0.9";
      track.append(dot);
    });
    scrubber.min = String(windowStart);
    scrubber.max = String(currentTick);
    scrubber.value = String(currentTick);
  } else {
    scrubber.disabled = false;
    for (let i = 3; i < 60; i += 5) {
      const dot = document.createElement("i"); dot.className = "event-dot"; dot.style.left = `${(i / 59) * 100}%`; dot.style.background = [palette.cyan, palette.violet, palette.coral, palette.mint][i % 4]; track.append(dot);
    }
    const total = state.replay.length || 60;
    const position = state.replay.length ? state.replayIndex : (state.realTick ?? state.tick);
    scrubber.max = String(Math.max(0, total - 1));
    scrubber.value = String(position);
    positionEl.textContent = `${position + 1} / ${total}`;
    timestampEl.textContent = `10:${String(24 + Math.floor(state.tick / 2)).padStart(2, "0")}:${String((state.tick * 7) % 60).padStart(2, "0")}`;
  }
}

function renderHistory() {
  const filters = document.querySelector("#event-filters"); filters.replaceChildren();
  ["all", "perception", "attention", "revision", "contradiction"].forEach(type => {
    const button = document.createElement("button"); button.className = `event-filter${state.eventFilter === type ? " active" : ""}`; button.textContent = type[0].toUpperCase() + type.slice(1);
    button.addEventListener("click", () => { state.eventFilter = type; renderHistory(); }); filters.append(button);
  });
  const list = document.querySelector("#history-list"); list.replaceChildren(); const events = availableEvents();
  if (!events.length) { const empty = document.createElement("p"); empty.className = "history-empty"; empty.textContent = "No cognitive events match this view."; list.append(empty); }
  if (!events.some(e => e.id === state.selectedEvent?.id)) {
    state.selectedEvent = events.length ? events[events.length - 1] : null;
  }
  events.slice().reverse().slice(0, 120).forEach(event => {
    const button = document.createElement("button"); button.className = `history-event${state.selectedEvent?.id === event.id ? " active" : ""}`;
    const color = document.createElement("i"); color.className = "event-color"; color.style.background = eventColor(event.type);
    const time = document.createElement("time"); time.textContent = `t${event.tick}`;
    const label = document.createElement("span"); label.textContent = event.label;
    const delta = document.createElement("em"); delta.textContent = `${event.delta >= 0 ? "+" : ""}${event.delta.toFixed(2)}`; delta.className = event.delta < 0 ? "negative" : "positive";
    button.append(color, time, label, delta); button.addEventListener("click", () => { state.selectedEvent = event; if (Number.isInteger(event.replayIndex)) { state.replayIndex = event.replayIndex; advance(0); } renderHistory(); }); list.append(button);
  });
  renderEventDetail();
}

function renderEventDetail() {
  const detail = document.querySelector("#event-detail"); detail.replaceChildren(); const event = state.selectedEvent;
  if (!event) return;
  const title = document.createElement("h3"); title.textContent = event.label; const explanation = document.createElement("p"); explanation.textContent = event.explanation;
  detail.append(title, explanation);
  if (event.chain.length) { const heading = document.createElement("h3"); heading.textContent = "Causal chain"; const chain = document.createElement("ol"); chain.className = "causal-chain"; event.chain.forEach(text => { const item = document.createElement("li"); item.textContent = text; chain.append(item); }); detail.append(heading, chain); }
  const comparison = comparisonFor(event);
  if (comparison) {
    const box = document.createElement("div"); box.className = "comparison";
    const head = document.createElement("div"); head.className = "comparison-head"; ["What changed", "Earlier", "", "Now"].forEach(text => { const span = document.createElement("span"); span.textContent = text; head.append(span); }); box.append(head);
    [["Certainty",comparison.earlier.certainty,comparison.now.certainty],["Evidence",comparison.earlier.evidence_count,comparison.now.evidence_count],["Revisions",comparison.earlier.revision_count,comparison.now.revision_count]].forEach(([label,a,b]) => { const row=document.createElement("div"); row.className="comparison-row"; [label,String(a),"→",String(b)].forEach(value=>{const cell=document.createElement("b");cell.textContent=value;row.append(cell)}); box.append(row); });
    const note=document.createElement("p"); note.className="comparison-note"; note.textContent="Difference between marked snapshots only — not a quality or risk judgment."; box.append(note); detail.append(box);
  }
}

export { renderTimeline, renderHistory, renderEventDetail };
