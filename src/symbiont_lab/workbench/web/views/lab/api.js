function readFormValues(form) {
  const output = {};
  new FormData(form).forEach((value, key) => {
    output[key] = value;
  });
  return output;
}

function baseExperimentPayload(form) {
  const payload = readFormValues(form);
  return {
    title: payload.title || 'Untitled experiment',
    hypothesis: payload.hypothesis || '',
    success_criteria: payload.success_criteria || '',
    notes: payload.notes || '',
    hosts: Number(payload.hosts || 100),
    steps: Number(payload.steps || 300),
    seed: Number(payload.seed || 7),
    threat_rate: Number(payload.threat_rate || 0.018),
    poison_fraction: Number(payload.poison_fraction || 0.08),
    heterogeneity: Number(payload.heterogeneity || 0.12),
    drift_step: payload.drift_step === '' ? null : Number(payload.drift_step || 0),
    drift_fraction: Number(payload.drift_fraction || 0.35),
    drift_magnitude: Number(payload.drift_magnitude || 0.22),
    delay: Number(payload.delay || 0.04),
  };
}

async function postJson(path, body, fallbackError) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || fallbackError);
  }
  return data;
}

export async function submitExperiment(form) {
  return postJson(
    '/api/experiments/start',
    baseExperimentPayload(form),
    'Unable to start experiment.',
  );
}

export async function submitStudy(form) {
  const base = baseExperimentPayload(form);
  const payload = readFormValues(form);
  return postJson(
    '/api/studies/start',
    {
      ...base,
      study_title: payload.study_title || 'Comparative study',
      parameter: payload.parameter || 'poison_fraction',
      baseline: Number(payload.baseline || 0),
      variant: Number(payload.variant || 0.12),
      seeds: (payload.seeds || '3,7,11')
        .split(',')
        .map((item) => Number(item.trim()))
        .filter((item) => Number.isFinite(item)),
    },
    'Unable to start study.',
  );
}
