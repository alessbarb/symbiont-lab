import { MindStreams } from '../mind/streams.js';
import { applyTelemetryEvent } from '../mind/telemetry.js';
import { applyMindSnapshot } from '../mind/snapshot.js';
import { snap, streamState, tel } from '../mind/state.js';
import { recordMotorHistory } from './action-discovery-history.js';
import { renderActionDiscovery } from './action-discovery.js';

/**
 * Embodiment · Discovery tab controller.
 *
 * Reuses the existing Mind transport coordinator and passive observation
 * state (no new protocol, ADR-0010). The subscription exists only while the
 * tab is active, and rendering is coalesced to one DOM update per frame.
 */
export class ActionDiscoveryPanel {
  constructor() {
    this.root = null;
    this.streams = null;
    this.renderQueued = false;
  }

  activate(root) {
    this.root = root;
    if (!this.streams) {
      this.streams = new MindStreams({
        onTelemetry: (data, meta = {}) => this.ingestTelemetry(data, meta),
        onSnapshot: (snapshot, meta = {}) => this.ingestSnapshot(snapshot, meta),
        onSourceState: (next) => this.applySourceState(next),
      });
      this.streams.connect();
    }
    this.requestRender();
  }

  deactivate() {
    this.streams?.close();
    this.streams = null;
    this.root = null;
  }

  ingestTelemetry(data, meta) {
    if (!applyTelemetryEvent(data)) return;
    streamState.lastTelemetryAt = Date.now();
    streamState.telemetryTick = meta.frameTick ?? data.tick ?? streamState.telemetryTick;
    this.updateCoherence();
  }

  ingestSnapshot(snapshot, meta) {
    if (!applyMindSnapshot(snapshot)) return;
    streamState.lastSnapshotAt = Date.now();
    streamState.snapshotTick = meta.tick ?? snapshot?.tick ?? snapshot?.snapshot?.tick ?? null;
    this.updateCoherence();
    recordMotorHistory();
    this.requestRender();
  }

  applySourceState(next) {
    if (next.identityChanged) {
      for (const key of Object.keys(tel)) tel[key] = null;
      for (const key of Object.keys(snap)) snap[key] = Array.isArray(snap[key]) ? [] : null;
      streamState.telemetryTick = null;
      streamState.snapshotTick = null;
    }
    Object.assign(streamState, {
      status: next.status,
      source: next.source ?? null,
      instanceId: next.instanceId ?? null,
      runId: next.runId ?? null,
      stale: next.status !== 'live',
      reason: next.reason ?? null,
    });
    this.updateCoherence();
    this.requestRender();
  }

  updateCoherence() {
    streamState.coherent =
      streamState.telemetryTick != null &&
      streamState.snapshotTick != null &&
      streamState.telemetryTick === streamState.snapshotTick;
    if (streamState.status === 'live' && streamState.coherent) {
      streamState.lastCoherentFrameAt = Date.now();
      streamState.stale = false;
    }
  }

  requestRender() {
    if (this.renderQueued || !this.root) return;
    this.renderQueued = true;
    requestAnimationFrame(() => {
      this.renderQueued = false;
      if (this.root) renderActionDiscovery(this.root);
    });
  }
}
