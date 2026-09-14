from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from symbiont.host.providers.linux_surfaces import LinuxSurfaceProvider


def _provider_over(table_path: Path):
    return patch.multiple(
        LinuxSurfaceProvider,
        _TABLE_FILES=(table_path,),
        _SYS_PATTERNS=(),
    )


def test_row_identity_survives_reordering():
    """Roadmap safety finding A03: a table row's identity must key on its
    own stable label, not its line position — otherwise reordering silently
    aliases one device's learned history onto a different device."""
    provider = LinuxSurfaceProvider()
    table = Path("/proc/diskstats")

    with _provider_over(table), patch.object(Path, "is_file", lambda self: self == table):
        with patch.object(Path, "read_text", return_value="8 0 sda 100 0\n8 16 sdb 900 0\n"):
            before_caps = provider.discover()
            before = {reading.capability_id: reading.value for reading in provider.sample(before_caps)}
        with patch.object(Path, "read_text", return_value="8 16 sdb 900 0\n8 0 sda 100 0\n"):
            after_caps = provider.discover()
            after = {reading.capability_id: reading.value for reading in provider.sample(after_caps)}

    sda_id = provider._opaque_id("table:/proc/diskstats:sda:2")
    sdb_id = provider._opaque_id("table:/proc/diskstats:sdb:2")

    assert before[sda_id] == 100.0
    assert before[sdb_id] == 900.0
    assert after[sda_id] == 100.0
    assert after[sdb_id] == 900.0
    assert set(before) == set(after)


def test_row_identity_reports_unavailable_when_its_label_disappears():
    provider = LinuxSurfaceProvider()
    table = Path("/proc/diskstats")

    with _provider_over(table), patch.object(Path, "is_file", lambda self: self == table):
        with patch.object(Path, "read_text", return_value="8 0 sda 100 0\n8 16 sdb 900 0\n"):
            caps = provider.discover()
        with patch.object(Path, "read_text", return_value="8 16 sdb 900 0\n"):
            readings = {reading.capability_id: reading for reading in provider.sample(caps)}

    sda_id = provider._opaque_id("table:/proc/diskstats:sda:2")
    assert readings[sda_id].value is None


def test_duplicate_row_labels_in_one_read_are_not_registered():
    provider = LinuxSurfaceProvider()
    table = Path("/proc/diskstats")

    with _provider_over(table), patch.object(Path, "is_file", lambda self: self == table):
        with patch.object(Path, "read_text", return_value="8 0 sda 100 0\n8 1 sda 200 0\n"):
            caps = provider.discover()

    # Only the first "sda" row is registered; a second row claiming the same
    # label is never silently merged with or overwritten by the first.
    sda_ids = [c.capability_id for c in caps if c.capability_id == provider._opaque_id("table:/proc/diskstats:sda:2")]
    assert len(sda_ids) == 1
