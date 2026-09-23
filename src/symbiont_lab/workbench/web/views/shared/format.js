import { escapeHtml } from './dom.js';

export function formatPercent(value, digits = 1, fallback = '—') {
  if (value == null || Number.isNaN(Number(value))) return fallback;
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

export function formatNumber(value, digits = 2, fallback = '—') {
  if (value == null || Number.isNaN(Number(value))) return fallback;
  return Number(value).toFixed(digits);
}

export function truncateHtml(value, max = 58) {
  const text = value == null ? '—' : String(value);
  const shortened = text.length > max ? `${text.slice(0, max - 1)}…` : text;
  return escapeHtml(shortened);
}

export function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

export function clamp01(value) {
  return Math.max(0, Math.min(1, finiteNumber(value, 0)));
}

export function shortId(value, head = 9, tail = 5) {
  const text = String(value ?? '');
  if (text.length <= head + tail + 1) return text;
  return `${text.slice(0, head)}…${text.slice(-tail)}`;
}
