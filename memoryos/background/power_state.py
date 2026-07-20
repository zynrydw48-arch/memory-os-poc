"""Windows power/foreground-app state, behind a small Protocol so a future
macOS/Linux implementation (or a fake, for tests) never touches the resource
monitor or the indexing worker that consume this."""

import ctypes
from typing import Protocol

# GetSystemPowerStatus (kernel32) SystemStatusFlag bit: 1 = Battery Saver is on.
_BATTERY_SAVER_FLAG = 0x1
# BatteryFlag bit: 0x80 = "no system battery" (desktops report this).
_NO_BATTERY_FLAG = 0x80
# ACLineStatus: 1 = plugged into AC power.
_AC_LINE_STATUS_ONLINE = 1

# SHQueryUserNotificationState (shell32) result values that mean "a
# foreground app wants the screen/CPU to itself right now" -- this is the
# same Windows API apps use to decide whether to suppress notifications,
# repurposed here for the identical "should a background task stay quiet"
# question. Rejected alternatives: guessing from a process-name list
# (fragile, needs constant upkeep) or GPU-usage heuristics via a
# vendor-specific library like pynvml (NVIDIA-only).
_QUNS_BUSY = 2
_QUNS_RUNNING_D3D_FULL_SCREEN = 3
_QUNS_PRESENTATION_MODE = 4
_QUIET_TIME_STATES = {_QUNS_BUSY, _QUNS_RUNNING_D3D_FULL_SCREEN, _QUNS_PRESENTATION_MODE}


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


class PowerStateProvider(Protocol):
    def is_battery_saver_enabled(self) -> bool: ...
    def battery_percent(self) -> int | None: ...
    def is_plugged_in(self) -> bool: ...
    def is_fullscreen_app_active(self) -> bool: ...


class WindowsPowerStateProvider:
    def __init__(self):
        self._kernel32 = ctypes.windll.kernel32
        self._shell32 = ctypes.windll.shell32

    def _get_power_status(self) -> _SystemPowerStatus | None:
        status = _SystemPowerStatus()
        succeeded = self._kernel32.GetSystemPowerStatus(ctypes.byref(status))
        return status if succeeded else None

    def is_battery_saver_enabled(self) -> bool:
        status = self._get_power_status()
        if status is None:
            return False
        return bool(status.SystemStatusFlag & _BATTERY_SAVER_FLAG)

    def battery_percent(self) -> int | None:
        status = self._get_power_status()
        if status is None or status.BatteryFlag & _NO_BATTERY_FLAG:
            return None
        percent = status.BatteryLifePercent
        return percent if percent <= 100 else None  # 255 = "unknown" sentinel

    def is_plugged_in(self) -> bool:
        status = self._get_power_status()
        if status is None:
            return True  # fail open: don't assume battery-constrained
        return status.ACLineStatus == _AC_LINE_STATUS_ONLINE

    def is_fullscreen_app_active(self) -> bool:
        state = ctypes.c_int()
        result = self._shell32.SHQueryUserNotificationState(ctypes.byref(state))
        if result != 0:  # non-zero HRESULT means the call failed
            return False
        return state.value in _QUIET_TIME_STATES
