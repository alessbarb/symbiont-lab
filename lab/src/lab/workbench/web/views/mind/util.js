import { clamp01, finiteNumber, shortId } from '../shared/format.js';

export { clamp01, finiteNumber, shortId };

export function pct(value) {
  return `${Math.round(clamp01(value) * 100)}%`;
}

export function classRatio(value, maximum) {
  const number = finiteNumber(value, 0);
  return maximum > 0 ? clamp01(number / maximum) : 0;
}

export function hashStr(value) {
  const text = String(value ?? '');
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = (Math.imul(31, hash) + text.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}
