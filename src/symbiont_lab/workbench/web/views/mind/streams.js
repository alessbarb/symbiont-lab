/**
 * Mind stream coordinator.
 *
 * Owns EventSource lifecycle and arbitration between the local Physics3D
 * snapshot stream and Observatory instance streams.
 */
export class MindStreams {
  constructor({
    onTelemetry,
    onSnapshot,
    onTopology,
    onWaiting,
    onSourceState,
  } = {}) {
    this.onTelemetry = onTelemetry ?? (() => {});
    this.onSnapshot = onSnapshot ?? (() => {});
    this.onTopology = onTopology ?? (() => {});
    this.onWaiting = onWaiting ?? (() => {});
    this.onSourceState = onSourceState ?? (() => {});

    this.organism = null;
    this.fleet = null;
    this.instance = null;
    this.activeInstance = null;
    this.activeRunId = null;
    this.localMindActive = false;
    this.closed = true;
    this.sourceIdentity = { source: null, instanceId: null, runId: null };
  }

  emitSourceState(status, next = {}) {
    const source = next.source ?? this.sourceIdentity.source ?? null;
    const instanceId = next.instanceId ?? this.sourceIdentity.instanceId ?? null;
    const runId = next.runId ?? this.sourceIdentity.runId ?? null;
    const identityChanged =
      source !== this.sourceIdentity.source ||
      instanceId !== this.sourceIdentity.instanceId ||
      runId !== this.sourceIdentity.runId;
    this.sourceIdentity = { source, instanceId, runId };
    this.onSourceState({
      status,
      source,
      instanceId,
      runId,
      reason: next.reason ?? null,
      identityChanged,
    });
  }

  connect() {
    this.closed = false;
    this.emitSourceState('waiting', { reason: 'connecting' });
    this.connectOrganism();
    this.connectFleet();
  }

  close() {
    this.closed = true;
    for (const key of ['organism', 'fleet', 'instance']) {
      const source = this[key];
      if (source) {
        try { source.close(); } catch {}
        this[key] = null;
      }
    }
    this.activeInstance = null;
    this.activeRunId = null;
    this.localMindActive = false;
    this.emitSourceState('disconnected', { source: null, instanceId: null, runId: null, reason: 'closed' });
  }

  connectOrganism() {
    if (this.organism) this.organism.close();
    this.organism = new EventSource('/api/organism');

    this.organism.addEventListener('message', (event) => {
      let data;
      try { data = JSON.parse(event.data); } catch { return; }
      if (!data?.type) return;

      if (data.type === 'observed_frame' && data.source === 'physics3d') {
        this.localMindActive = true;
        const frameRunId = data.run_id ?? data.runId ?? data.cognition?.run_id ?? null;
        const frameInstanceId = data.instance_id ?? data.instanceId ?? data.cognition?.instance_id ?? null;
        this.emitSourceState('live', {
          source: 'physics3d',
          instanceId: frameInstanceId,
          runId: frameRunId,
        });
        if (this.instance) {
          this.instance.close();
          this.instance = null;
        }
        this.activeInstance = null;
        this.activeRunId = null;
        for (const component of [data.body, data.cognition, data.vitals]) {
          if (component?.type) this.onTelemetry(component);
        }
        if (data.mind) {
          this.onSnapshot(data.mind, {
            source: 'physics3d',
            tick: data.tick ?? null,
            coherentFrame: true,
            instanceId: frameInstanceId,
            runId: frameRunId,
          });
        }
        return;
      }

      if (
        data.source === 'physics3d' &&
        ['body', 'cognition', 'vitals'].includes(data.type)
      ) {
        // Claim the local source immediately, but render Physics3D components
        // only through the coherent observed_frame. Body has its own consumer.
        this.localMindActive = true;
        if (this.instance) {
          this.instance.close();
          this.instance = null;
        }
        this.activeInstance = null;
        this.activeRunId = null;
        return;
      }

      if (data.type === 'mind_snapshot' && data.source === 'physics3d' && data.snapshot) {
        this.localMindActive = true;
        this.emitSourceState('live', {
          source: 'physics3d',
          instanceId: data.instance_id ?? null,
          runId: data.run_id ?? null,
        });
        if (this.instance) {
          this.instance.close();
          this.instance = null;
        }
        this.activeInstance = null;
        this.activeRunId = null;
        if (!data.coherent_frame_follows) {
          this.onSnapshot(data.snapshot, { source: 'physics3d' });
        }
        return;
      }

      if (!this.localMindActive && this.activeInstance && data.instance_id !== this.activeInstance) {
        return;
      }
      if (this.activeRunId && data.run_id && data.run_id !== this.activeRunId) {
        return;
      }
      if (!this.activeInstance) this.onWaiting(false, null);

      this.onTelemetry(data);
    });

    this.organism.onerror = () => {
      this.emitSourceState('stale', { reason: 'organism-stream-disconnected' });
      this.onWaiting(true, 'SSE /api/organism disconnected — retrying…');
    };
  }

  async connectFleet() {
    if (this.fleet) this.fleet.close();

    try {
      const response = await fetch('/api/state', { cache: 'no-store' });
      if (this.closed) return;
      if (response.ok) {
        const state = await response.json();
        const observatory = state?.sources?.observatory;
        if (observatory && observatory.available === false) {
          this.onWaiting(
            true,
            'Observatory is not available — local organism telemetry remains active.',
          );
          return;
        }
      }
    } catch {
      // Source discovery is advisory. The EventSource attempt below remains
      // the transport-level fallback for older or partially available servers.
    }

    if (this.closed) return;

    try {
      this.fleet = new EventSource('/fleet');
    } catch {
      this.onWaiting(
        true,
        'Observatory fleet is unavailable — showing local organism telemetry only.',
      );
      return;
    }

    this.fleet.onmessage = (event) => {
      let payload;
      try { payload = JSON.parse(event.data); } catch { return; }

      const instances = Array.isArray(payload.instances) ? payload.instances : [];
      const alive = instances.filter((item) => item.liveness === 'alive');
      if (this.localMindActive) return;

      const current = this.activeInstance
        ? alive.find((item) => item.instance_id === this.activeInstance)
        : null;

      if (current) {
        const nextRunId = current.run_id ?? null;
        this.emitSourceState('live', { source: 'observatory', instanceId: current.instance_id, runId: nextRunId });
        if (nextRunId !== this.activeRunId) {
          this.connectInstance(current.instance_id, nextRunId);
        }
        return;
      }

      if (this.activeInstance && this.instance) {
        this.instance.close();
        this.instance = null;
      }
      this.activeInstance = null;
      this.activeRunId = null;

      if (alive.length > 0) {
        this.connectInstance(alive[0].instance_id, alive[0].run_id ?? null);
      } else {
        this.emitSourceState('waiting', { source: null, instanceId: null, runId: null, reason: 'no-live-instance' });
        this.onWaiting(true, 'Waiting for a live Observatory instance…');
      }
    };

    this.fleet.onerror = () => {
      this.onWaiting(
        true,
        'Observatory fleet unavailable — fallback to the organism stream is active.',
      );
      if (this.fleet) {
        try { this.fleet.close(); } catch {}
        this.fleet = null;
      }
    };
  }

  connectInstance(instanceId, runId = null) {
    if (
      this.activeInstance === instanceId &&
      this.activeRunId === runId &&
      this.instance
    ) {
      return;
    }

    if (this.instance) this.instance.close();
    this.activeInstance = instanceId;
    this.activeRunId = runId;
    this.emitSourceState('live', { source: 'observatory', instanceId, runId });
    this.instance = new EventSource(`/instances/${instanceId}`);

    this.instance.onmessage = (event) => {
      let payload;
      try { payload = JSON.parse(event.data); } catch { return; }

      if (payload.run_id && this.activeRunId && payload.run_id !== this.activeRunId) {
        return;
      }
      if (payload.run_id && !this.activeRunId) this.activeRunId = payload.run_id;

      if (payload.snapshot) {
        this.onSnapshot(payload.snapshot, {
          source: 'observatory',
          instanceId,
          runId: this.activeRunId,
        });
      }
      if (payload.topology) {
        this.onTopology(payload.topology, {
          instanceId,
          runId: this.activeRunId,
        });
      }
    };

    this.instance.onerror = () => {
      this.emitSourceState('stale', { source: 'observatory', instanceId, runId: this.activeRunId, reason: 'instance-stream-disconnected' });
      this.onWaiting(true, `Connection to instance ${instanceId} lost — retrying…`);
    };
  }
}
