"""Decides whether the background indexing worker should pause, and why.

Runs on the main thread on a QTimer (see memoryos/ui/main_window.py); the
worker itself never polls resources directly, it only reacts to
pause/resume requests derived from ResourceMonitor.decide().
"""

import logging
from enum import Enum, auto

import psutil

from memoryos.background.power_state import PowerStateProvider, WindowsPowerStateProvider

logger = logging.getLogger(__name__)

# Named thresholds -- no magic numbers.
HIGH_CPU_PERCENT_THRESHOLD = 85.0
HIGH_CPU_CONSECUTIVE_SAMPLES = 2  # avoid reacting to a single noisy spike
LOW_BATTERY_PERCENT_THRESHOLD = 20
HIGH_RAM_CEILING_BYTES = 6 * 1024 * 1024 * 1024  # 6 GB: circuit breaker, not a routine strategy


class PauseReason(Enum):
    NONE = auto()
    USER_REQUESTED = auto()
    BATTERY_SAVER = auto()
    FULLSCREEN_APP_DETECTED = auto()
    LOW_BATTERY = auto()
    HIGH_CPU = auto()
    LOW_RAM = auto()


class ResourceMonitor:
    def __init__(self, power_state: PowerStateProvider | None = None):
        self._power_state = power_state or WindowsPowerStateProvider()
        self._high_cpu_streak = 0
        # Sprint 8.5: a persistent Process handle -- psutil.Process.cpu_percent()
        # tracks usage since the *previous call on this same instance*, so a
        # fresh Process() object every call would always read ~0%. Must be
        # created once and reused, unlike the module-level psutil.cpu_percent()
        # below, which already tracks its own state across calls.
        self._own_process = psutil.Process()
        try:
            psutil.cpu_percent(interval=None)  # prime the internal counter
        except Exception:
            logger.exception("failed to prime CPU counter; first reading may be inaccurate")
        try:
            self._own_process.cpu_percent(interval=None)  # prime our own share too
        except Exception:
            logger.exception("failed to prime own-process CPU counter; first reading may be inaccurate")

    def decide(self) -> PauseReason:
        """Checked in priority order -- a fullscreen game matters more than a
        slightly elevated CPU reading. Any individual check failing is
        treated as 'assume normal' (fail open): a transient psutil/ctypes
        hiccup must never crash indexing or permanently block it."""
        if self._check_battery_saver():
            return PauseReason.BATTERY_SAVER
        if self._check_fullscreen():
            return PauseReason.FULLSCREEN_APP_DETECTED
        if self._check_low_battery():
            return PauseReason.LOW_BATTERY
        if self._check_high_cpu():
            return PauseReason.HIGH_CPU
        if self._check_high_ram():
            return PauseReason.LOW_RAM
        return PauseReason.NONE

    def _check_battery_saver(self) -> bool:
        try:
            return self._power_state.is_battery_saver_enabled()
        except Exception:
            logger.exception("battery saver check failed; assuming off")
            return False

    def _check_fullscreen(self) -> bool:
        try:
            return self._power_state.is_fullscreen_app_active()
        except Exception:
            logger.exception("fullscreen check failed; assuming inactive")
            return False

    def _check_low_battery(self) -> bool:
        try:
            if self._power_state.is_plugged_in():
                return False
            percent = self._power_state.battery_percent()
            return percent is not None and percent < LOW_BATTERY_PERCENT_THRESHOLD
        except Exception:
            logger.exception("battery level check failed; assuming fine")
            return False

    def _check_high_cpu(self) -> bool:
        """Sprint 8.5: parallel indexing intentionally drives CPU usage up --
        this measures load *other* processes are generating (system-wide
        minus our own share), not raw system-wide usage, so our own
        deliberate parallel work never triggers a false pause. The original
        intent (don't make the user's actual foreground work sluggish) is
        preserved: if something else is genuinely hogging the CPU, this still
        fires exactly as before."""
        try:
            system_cpu_percent = psutil.cpu_percent(interval=None)
            own_cpu_percent = self._own_process.cpu_percent(interval=None)
        except Exception:
            logger.exception("CPU check failed; assuming normal")
            return False

        other_processes_cpu_percent = max(0.0, system_cpu_percent - own_cpu_percent)
        if other_processes_cpu_percent >= HIGH_CPU_PERCENT_THRESHOLD:
            self._high_cpu_streak += 1
        else:
            self._high_cpu_streak = 0
        return self._high_cpu_streak >= HIGH_CPU_CONSECUTIVE_SAMPLES

    def _check_high_ram(self) -> bool:
        try:
            rss = psutil.Process().memory_info().rss
        except Exception:
            logger.exception("RAM check failed; assuming normal")
            return False
        return rss >= HIGH_RAM_CEILING_BYTES
