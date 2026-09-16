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


def test_loop_and_ram_devices_are_filtered():
    provider = LinuxSurfaceProvider()
    table = Path("/proc/diskstats")

    with _provider_over(table), patch.object(Path, "is_file", lambda self: self == table):
        content = "7 0 loop0 10 0\n1 0 ram0 20 0\n8 0 sda 100 0\n"
        with patch.object(Path, "read_text", return_value=content):
            caps = provider.discover()

    locators = [provider._opaque_id("table:/proc/diskstats:sda:2")]
    assert any(c.capability_id in locators for c in caps)
    loop_ids = [c.capability_id for c in caps if "loop0" in getattr(c, "capability_id", "")]
    assert len(loop_ids) == 0
    ram_ids = [c.capability_id for c in caps if "ram0" in getattr(c, "capability_id", "")]
    assert len(ram_ids) == 0


def test_entropy_surface_discovery_and_sampling():
    provider = LinuxSurfaceProvider()
    entropy_path = Path("/proc/sys/kernel/random/entropy_avail")

    def mock_is_file(self):
        return self == entropy_path

    with patch.multiple(LinuxSurfaceProvider, _TABLE_FILES=(), _SYS_PATTERNS=()), \
         patch.object(Path, "is_file", mock_is_file), \
         patch.object(Path, "read_text", return_value="256\n"):
        caps = provider.discover()
        entropy_id = provider._opaque_id("proc-entropy")
        assert any(c.capability_id == entropy_id for c in caps)
        readings = {r.capability_id: r for r in provider.sample(caps)}
        assert readings[entropy_id].value == 256.0


def test_hardware_sysfs_cpu_and_gpu_patterns():
    provider = LinuxSurfaceProvider()
    cpu_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    gpu_path = Path("/sys/class/drm/card1/gt_cur_freq_mhz")

    def mock_is_file(self):
        return self in (cpu_path, gpu_path)

    def mock_glob(self, pattern):
        if "scaling_cur_freq" in pattern:
            return [cpu_path]
        if "gt_cur_freq_mhz" in pattern:
            return [gpu_path]
        return []

    def mock_read_text(self, *args, **kwargs):
        if self == cpu_path:
            return "2800000\n"
        if self == gpu_path:
            return "350\n"
        return ""

    with patch.multiple(LinuxSurfaceProvider, _TABLE_FILES=()), \
         patch.object(Path, "is_file", mock_is_file), \
         patch.object(Path, "glob", mock_glob), \
         patch.object(Path, "read_text", mock_read_text):
        caps = provider.discover()
        cpu_id = provider._opaque_id(f"sys-scalar:{cpu_path.as_posix()}")
        gpu_id = provider._opaque_id(f"sys-scalar:{gpu_path.as_posix()}")
        assert any(c.capability_id == cpu_id for c in caps)
        assert any(c.capability_id == gpu_id for c in caps)

        readings = {r.capability_id: r for r in provider.sample(caps)}
        assert readings[cpu_id].value == 2800000.0
        assert readings[gpu_id].value == 350.0

