# Deployment

This directory contains the explicit host-owner deployment material for the
Symbiont Experimental Organism v1 release. Deployment is intentionally not
self-installing and does not grant the organism additional host capabilities.

## Release contract

- Package version: `1.0.0`.
- Scientific cut: `experimental-organism-v1` (tagging and publication are
  performed separately from preparing this tree).
- Historical tag `v0.80.16` remains immutable.
- The user service stores bounded local state below
  `~/.local/state/symbiont`.
- The unit is local and foreground-visible under the user's systemd instance;
  it does not perform peer discovery, network exchange, or automatic
  installation.

## Install the user service

After installing the package from the release artifact (or from a local wheel
while the release is being prepared), an owner may install and start the unit:

```bash
python -m pip install --user symbiont-lab==1.0.0
install -Dm644 deploy/systemd/symbiont.service \
  ~/.config/systemd/user/symbiont.service
systemctl --user daemon-reload
systemctl --user enable --now symbiont.service
```

The service is not enabled by package installation alone. The owner must
explicitly choose to install and start it.

## Verify and operate

```bash
python -c 'import symbiont, symbiont_lab; print(symbiont.__version__, symbiont_lab.__version__)'
systemctl --user status symbiont.service
journalctl --user -u symbiont.service
```

If `systemd-analyze` is available, verify the unit before enabling it:

```bash
systemd-analyze --user verify ~/.config/systemd/user/symbiont.service
```

Updates are explicit: install the intended package version, then restart the
user service. To stop and remove the service:

```bash
systemctl --user disable --now symbiont.service
rm ~/.config/systemd/user/symbiont.service
systemctl --user daemon-reload
```

The unit's hardening directives (`NoNewPrivileges`, `PrivateTmp`,
`ProtectSystem`, `ProtectHome`, and `ReadWritePaths`) are part of the safety
contract. Changes to them require a separately reviewed security decision;
they are not release-version switches.
