/**
 * Runtime state polling coordinator for the workbench shell.
 *
 * Keeps slow operational state separate from dense Body/Mind streams.
 * It prevents overlapping requests, aborts on stop, backs off after failures,
 * and polls less aggressively while the document is hidden.
 */
export class RuntimeStatePoller {
  constructor({
    url = '/api/state',
    activeIntervalMs = 2500,
    hiddenIntervalMs = 10000,
    maxBackoffMs = 30000,
    onState = () => {},
    onError = () => {},
  } = {}) {
    this.url = url;
    this.activeIntervalMs = activeIntervalMs;
    this.hiddenIntervalMs = hiddenIntervalMs;
    this.maxBackoffMs = maxBackoffMs;
    this.onState = onState;
    this.onError = onError;

    this.running = false;
    this.failures = 0;
    this.timer = null;
    this.controller = null;
    this.visibilityHandler = () => this._visibilityChanged();
    this.onlineHandler = () => this.refresh();
  }

  start() {
    if (this.running) return;
    this.running = true;
    document.addEventListener('visibilitychange', this.visibilityHandler);
    window.addEventListener('online', this.onlineHandler);
    this.refresh();
  }

  stop() {
    if (!this.running) return;
    this.running = false;
    document.removeEventListener('visibilitychange', this.visibilityHandler);
    window.removeEventListener('online', this.onlineHandler);
    if (this.timer !== null) {
      window.clearTimeout(this.timer);
      this.timer = null;
    }
    this.controller?.abort();
    this.controller = null;
  }

  async refresh() {
    if (!this.running || this.controller) return;

    if (this.timer !== null) {
      window.clearTimeout(this.timer);
      this.timer = null;
    }

    const controller = new AbortController();
    this.controller = controller;

    try {
      const response = await fetch(this.url, {
        cache: 'no-store',
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const state = await response.json();
      if (!this.running || controller.signal.aborted) return;

      this.failures = 0;
      this.onState(state);
    } catch (error) {
      if (!controller.signal.aborted && this.running) {
        this.failures += 1;
        this.onError(error);
      }
    } finally {
      if (this.controller === controller) this.controller = null;
      if (this.running) this._schedule();
    }
  }

  _baseInterval() {
    return document.hidden ? this.hiddenIntervalMs : this.activeIntervalMs;
  }

  _delay() {
    if (!this.failures) return this._baseInterval();
    return Math.min(
      this.maxBackoffMs,
      this._baseInterval() * (2 ** Math.min(this.failures - 1, 4)),
    );
  }

  _schedule(delay = this._delay()) {
    if (!this.running) return;
    if (this.timer !== null) window.clearTimeout(this.timer);
    this.timer = window.setTimeout(() => {
      this.timer = null;
      this.refresh();
    }, delay);
  }

  _visibilityChanged() {
    if (!this.running) return;
    if (!document.hidden) {
      this.refresh();
      return;
    }
    this._schedule();
  }
}
