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
  } = {}) {
    this.onTelemetry = onTelemetry ?? (() => {});
    this.onSnapshot = onSnapshot ?? (() => {});
    this.onTopology = onTopology ?? (() => {});
    this.onWaiting = onWaiting ?? (() => {});

    this.organism = null;
    this.fleet = null;
    this.instance = null;
    this.activeInstance = null;
    this.activeRunId = null;
    this.localMindActive = false;
  }

  connect() {
    this.connectOrganism();
    this.connectFleet();
  }

  close() {
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
          });
        }
        return;
      }

      if (data.type === 'mind_snapshot' && data.source === 'physics3d' && data.snapshot) {
        this.localMindActive = true;
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
      this.onWaiting(true, 'SSE /api/organism disconnected — retrying…');
    };
  }

  connectFleet() {
    if (this.fleet) this.fleet.close();
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
      this.onWaiting(true, `Connection to instance ${instanceId} lost — retrying…`);
    };
  }
}
