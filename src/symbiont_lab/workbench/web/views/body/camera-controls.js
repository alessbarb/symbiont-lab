/**
 * Observer-only camera toolbar for the Body view.
 * Keeps DOM controls outside the Three.js renderer lifecycle.
 */
export function mountBodyCameraControls(container, {
  isFollowing,
  onToggleFollow,
  onReset,
}) {
  const bar = document.createElement('div');
  bar.className = 'body-camera-bar';

  const followButton = document.createElement('button');
  followButton.type = 'button';
  followButton.className = 'body-camera-button body-camera-follow';

  const sync = () => {
    const following = Boolean(isFollowing());
    followButton.textContent = following ? '● Follow body' : '○ Free camera';
    followButton.classList.toggle('active', following);
    followButton.setAttribute('aria-pressed', String(following));
  };

  followButton.addEventListener('click', () => {
    onToggleFollow();
    sync();
  });

  const resetButton = document.createElement('button');
  resetButton.type = 'button';
  resetButton.className = 'body-camera-button';
  resetButton.textContent = 'Reset view';
  resetButton.addEventListener('click', onReset);

  bar.append(followButton, resetButton);
  container.appendChild(bar);
  sync();

  return {
    element: bar,
    followButton,
    sync,
    dispose() {
      bar.remove();
    },
  };
}
