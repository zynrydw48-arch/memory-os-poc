import psutil
import pytest

from memoryos.background.resource_monitor import (
    HIGH_RAM_CEILING_BYTES,
    LOW_BATTERY_PERCENT_THRESHOLD,
    PauseReason,
    ResourceMonitor,
)


class FakePowerState:
    def __init__(
        self,
        battery_saver: bool = False,
        fullscreen: bool = False,
        plugged_in: bool = True,
        percent: int | None = None,
    ):
        self.battery_saver = battery_saver
        self.fullscreen = fullscreen
        self.plugged_in = plugged_in
        self.percent = percent

    def is_battery_saver_enabled(self) -> bool:
        return self.battery_saver

    def battery_percent(self) -> int | None:
        return self.percent

    def is_plugged_in(self) -> bool:
        return self.plugged_in

    def is_fullscreen_app_active(self) -> bool:
        return self.fullscreen


class RaisingPowerState:
    def is_battery_saver_enabled(self):
        raise RuntimeError("boom")

    def battery_percent(self):
        raise RuntimeError("boom")

    def is_plugged_in(self):
        raise RuntimeError("boom")

    def is_fullscreen_app_active(self):
        raise RuntimeError("boom")


@pytest.fixture(autouse=True)
def stable_cpu(monkeypatch):
    """Default all tests to a low, stable CPU reading unless overridden."""
    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=None: 10.0)


def test_all_normal_returns_none():
    monitor = ResourceMonitor(power_state=FakePowerState())
    assert monitor.decide() == PauseReason.NONE


def test_battery_saver_takes_highest_priority():
    monitor = ResourceMonitor(power_state=FakePowerState(battery_saver=True, fullscreen=True))
    assert monitor.decide() == PauseReason.BATTERY_SAVER


def test_fullscreen_detected():
    monitor = ResourceMonitor(power_state=FakePowerState(fullscreen=True))
    assert monitor.decide() == PauseReason.FULLSCREEN_APP_DETECTED


def test_low_battery_when_unplugged_and_below_threshold():
    monitor = ResourceMonitor(
        power_state=FakePowerState(plugged_in=False, percent=LOW_BATTERY_PERCENT_THRESHOLD - 1)
    )
    assert monitor.decide() == PauseReason.LOW_BATTERY


def test_battery_above_threshold_is_fine_even_unplugged():
    monitor = ResourceMonitor(
        power_state=FakePowerState(plugged_in=False, percent=LOW_BATTERY_PERCENT_THRESHOLD + 10)
    )
    assert monitor.decide() == PauseReason.NONE


def test_low_battery_ignored_while_plugged_in():
    monitor = ResourceMonitor(power_state=FakePowerState(plugged_in=True, percent=5))
    assert monitor.decide() == PauseReason.NONE


def test_high_cpu_requires_consecutive_samples(monkeypatch):
    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=None: 95.0)
    monitor = ResourceMonitor(power_state=FakePowerState())

    assert monitor.decide() == PauseReason.NONE  # first high sample: not yet a streak
    assert monitor.decide() == PauseReason.HIGH_CPU  # second consecutive high sample


def test_high_cpu_streak_resets_on_a_normal_sample(monkeypatch):
    # Leading 0.0 is consumed by ResourceMonitor.__init__'s priming call.
    readings = iter([0.0, 95.0, 95.0, 10.0, 95.0])
    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=None: next(readings))
    monitor = ResourceMonitor(power_state=FakePowerState())

    assert monitor.decide() == PauseReason.NONE
    assert monitor.decide() == PauseReason.HIGH_CPU
    assert monitor.decide() == PauseReason.NONE  # streak reset
    assert monitor.decide() == PauseReason.NONE  # only one high sample since reset


def test_high_ram_triggers_low_ram_reason(monkeypatch):
    class FakeMemInfo:
        rss = HIGH_RAM_CEILING_BYTES + 1

    class FakeProcess:
        def memory_info(self):
            return FakeMemInfo()

    monkeypatch.setattr(psutil, "Process", lambda: FakeProcess())
    monitor = ResourceMonitor(power_state=FakePowerState())
    assert monitor.decide() == PauseReason.LOW_RAM


def test_power_state_errors_fail_open_not_raise():
    monitor = ResourceMonitor(power_state=RaisingPowerState())
    assert monitor.decide() == PauseReason.NONE


def test_cpu_check_error_fails_open(monkeypatch):
    def raising_cpu_percent(interval=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(psutil, "cpu_percent", raising_cpu_percent)
    monitor = ResourceMonitor(power_state=FakePowerState())
    assert monitor.decide() == PauseReason.NONE


class _FakeOwnProcess:
    """Stands in for psutil.Process() -- only cpu_percent() is used by
    _check_high_cpu(), matching how FakePowerState only implements what's
    actually called."""

    def __init__(self, cpu_percent: float):
        self._cpu_percent = cpu_percent

    def cpu_percent(self, interval=None) -> float:
        return self._cpu_percent


def test_high_system_cpu_from_our_own_process_does_not_pause(monkeypatch):
    # Sprint 8.5: parallel indexing intentionally drives system-wide CPU to
    # 95%, but MemoryOS itself accounts for essentially all of it -- other
    # processes are barely using the CPU, so this must not pause.
    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=None: 95.0)
    monkeypatch.setattr(psutil, "Process", lambda: _FakeOwnProcess(cpu_percent=93.0))
    monitor = ResourceMonitor(power_state=FakePowerState())

    assert monitor.decide() == PauseReason.NONE
    assert monitor.decide() == PauseReason.NONE  # still fine on a second consecutive sample


def test_high_system_cpu_from_other_process_still_pauses(monkeypatch):
    # Something else (not MemoryOS) is genuinely hogging the CPU -- the
    # original "protect the user's foreground work" intent must still hold.
    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=None: 95.0)
    monkeypatch.setattr(psutil, "Process", lambda: _FakeOwnProcess(cpu_percent=5.0))
    monitor = ResourceMonitor(power_state=FakePowerState())

    assert monitor.decide() == PauseReason.NONE  # first high sample: not yet a streak
    assert monitor.decide() == PauseReason.HIGH_CPU  # second consecutive high sample
