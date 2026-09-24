/**
 * Stateless DOM coordinator for Mind tabs.
 * Rendering decisions stay in mind.js; this module owns only shell presentation.
 */
const TAB_IDS = ['overview', 'phenotype', 'sensory', 'cognition', 'motor', 'history'];

const WRAP_IDS = {
  overview: 'mind-overview-wrap',
  phenotype: 'mind-identity-wrap',
  sensory: 'mind-sensory-wrap',
  cognition: 'mind-cognition-wrap',
  motor: 'mind-motor-wrap',
  history: 'mind-history-wrap',
};

export function applyMindTab(tabId) {
  const activeTab = TAB_IDS.includes(tabId) ? tabId : 'overview';

  document.querySelectorAll('.mind-tab').forEach((button) => {
    const active = button.dataset.tab === activeTab;
    button.setAttribute('aria-pressed', String(active));
  });

  for (const id of TAB_IDS) {
    document.getElementById(WRAP_IDS[id])?.classList.toggle('hidden', id !== activeTab);
  }

  const workspace = document.getElementById('mind-workspace');
  if (workspace) workspace.dataset.activeTab = activeTab;

  const sensesPanel = document.getElementById('mind-senses-panel');
  if (sensesPanel) sensesPanel.hidden = activeTab !== 'sensory';

  const cognitionInspector = document.getElementById('mind-cognition-inspector');
  if (cognitionInspector) cognitionInspector.hidden = activeTab !== 'cognition';

  return activeTab;
}
