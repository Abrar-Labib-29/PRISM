"""
iValue PRISM — System Information & Host Diagnostics Utilities
SRS References: §10.7, §11.4, §8.1.10, §6.9
Implementation Plan: TASK-P1.3

This module provides resource monitoring (RAM/CPU metrics via psutil),
Windows single-instance application guards (named mutex via ctypes),
and OS accessibility detection (reduced motion / SPI_GETCLIENTAREAANIMATION).
"""

import atexit
import ctypes
import logging
import os
from typing import Optional
import psutil

_sys_logger = logging.getLogger("prism.system")

# Mutex handle kept alive at module level to prevent garbage collection
_MUTEX_HANDLE: Optional[int] = None

# Win32 SystemParametersInfo constants
SPI_GETCLIENTAREAANIMATION = 0x1042
ERROR_ALREADY_EXISTS = 183
ERROR_ACCESS_DENIED = 5


def get_ram_usage_mb() -> float:
    """
    Returns the current process Resident Set Size (RSS) memory consumption in megabytes.
    Per SRS §10.7, §11.4.
    """
    try:
        process = psutil.Process(os.getpid())
        return float(process.memory_info().rss / (1024.0 * 1024.0))
    except Exception as e:
        _sys_logger.warning(f"Failed to get process RAM usage: {e}")
        return 0.0


def get_system_ram_mb() -> float:
    """
    Returns total system RAM used across all host processes in megabytes.
    Per SRS §10.7, §11.4.
    """
    try:
        return float(psutil.virtual_memory().used / (1024.0 * 1024.0))
    except Exception as e:
        _sys_logger.warning(f"Failed to get system RAM usage: {e}")
        return 0.0


def get_total_system_ram_mb() -> float:
    """
    Returns total physical host RAM installed in megabytes.
    """
    try:
        return float(psutil.virtual_memory().total / (1024.0 * 1024.0))
    except Exception as e:
        _sys_logger.warning(f"Failed to get total physical RAM: {e}")
        return 0.0


def get_available_system_ram_mb() -> float:
    """
    Returns available host RAM without paging in megabytes.
    """
    try:
        return float(psutil.virtual_memory().available / (1024.0 * 1024.0))
    except Exception as e:
        _sys_logger.warning(f"Failed to get available RAM: {e}")
        return 0.0


def get_cpu_percent(interval: Optional[float] = None) -> float:
    """
    Returns current host CPU utilization percentage.
    """
    try:
        return float(psutil.cpu_percent(interval=interval))
    except Exception as e:
        _sys_logger.warning(f"Failed to get CPU percent: {e}")
        return 0.0


def verify_single_instance(mutex_name: str = "Global\\iValue_PRISM") -> bool:
    """
    Attempts to create a Windows named mutex via ctypes.windll.kernel32.CreateMutexW.
    Returns True if this is the first running instance, False if another instance holds the mutex.
    Per SRS §10.7: single-instance guard.
    """
    global _MUTEX_HANDLE

    # On non-Windows OS (or during tests in non-NT environments), gracefully pass
    if os.name != "nt":
        return True

    if _MUTEX_HANDLE is not None:
        # Mutex is already held by the current process
        return True

    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = kernel32.GetLastError()

        if last_error in (ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED):
            if handle:
                kernel32.CloseHandle(handle)
            return False

        if not handle:
            return False

        _MUTEX_HANDLE = handle
        return True
    except Exception as e:
        _sys_logger.warning(f"verify_single_instance failed with exception: {e}")
        # Default to True to prevent locking users out on unexpected API errors
        return True


def release_single_instance() -> None:
    """
    Closes the Windows named mutex handle if held by this process.
    """
    global _MUTEX_HANDLE
    if os.name == "nt" and _MUTEX_HANDLE:
        try:
            ctypes.windll.kernel32.CloseHandle(_MUTEX_HANDLE)
        except Exception:
            pass
        _MUTEX_HANDLE = None


# Ensure mutex cleanup on normal interpreter exit
atexit.register(release_single_instance)


def check_reduced_motion() -> bool:
    """
    Checks Windows SPI_GETCLIENTAREAANIMATION via ctypes.windll.user32.SystemParametersInfoW.
    Returns True if client area animations are disabled (reduced motion mode).
    Per SRS §8.1.10, §6.9.
    """
    if os.name != "nt":
        return False

    try:
        anim_enabled = ctypes.c_bool()
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETCLIENTAREAANIMATION,
            0,
            ctypes.byref(anim_enabled),
            0,
        )
        if result == 0:
            # Call failed; default to standard motion
            return False
        # If animation is enabled, reduced motion is False.
        # If animation is disabled, reduced motion is True.
        return not bool(anim_enabled.value)
    except Exception as e:
        _sys_logger.warning(f"check_reduced_motion failed with exception: {e}")
        return False
