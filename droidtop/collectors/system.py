"""
DroidTop - Android System & Hardware Information Collector.
Reads Android build properties, kernel sysinfo, uptime, and load averages.
"""

import os
import subprocess
import ctypes
from typing import Dict, Tuple, Optional


class SysInfoStruct(ctypes.Structure):
    _fields_ = [
        ("uptime", ctypes.c_long),
        ("loads", ctypes.c_ulong * 3),
        ("totalram", ctypes.c_ulong),
        ("freeram", ctypes.c_ulong),
        ("sharedram", ctypes.c_ulong),
        ("bufferram", ctypes.c_ulong),
        ("totalswap", ctypes.c_ulong),
        ("freeswap", ctypes.c_ulong),
        ("procs", ctypes.c_ushort),
        ("pad", ctypes.c_ushort),
        ("totalhigh", ctypes.c_ulong),
        ("freehigh", ctypes.c_ulong),
        ("mem_unit", ctypes.c_uint),
    ]


class SystemCollector:
    """Collects static device details and realtime uptime/load averages."""

    def __init__(self):
        self._libc = None
        try:
            self._libc = ctypes.CDLL(None)
        except Exception:
            pass

        # Cache static device properties
        self.props = self._read_all_props()
        self.brand = self.props.get("ro.product.brand", "Android")
        self.model = self.props.get("ro.product.model", "Generic")
        self.device = self.props.get("ro.product.device", "")
        self.android_version = self.props.get("ro.build.version.release", "Unknown")
        self.sdk_version = self.props.get("ro.build.version.sdk", "")
        self.soc_model = self.props.get("ro.soc.model", "")
        self.soc_name = self.props.get("ro.product.cpu_info", "") or self.soc_model or "ARM64"
        self.security_patch = self.props.get("ro.build.version.security_patch", "")
        self.battery_cycle_count = self.props.get("persist.sys.BatteryCycleCount", "")

        uname = os.uname()
        self.hostname = uname.nodename
        self.kernel_release = uname.release
        self.machine = uname.machine

    def _read_all_props(self) -> Dict[str, str]:
        """Read all Android properties via getprop."""
        props = {}
        try:
            p = subprocess.run(["getprop"], capture_output=True, text=True, timeout=2)
            for line in p.stdout.splitlines():
                if line.startswith("[") and "]: [" in line:
                    k, v = line.split("]: [", 1)
                    props[k.strip("[] ")] = v.rstrip("]")
        except Exception:
            pass
        return props

    def get_live_stats(self) -> Dict:
        """Fetch current uptime, load averages, and kernel task count."""
        uptime_sec = 0
        loads = (0.0, 0.0, 0.0)
        procs_count = 0

        if self._libc and hasattr(self._libc, "sysinfo"):
            try:
                info = SysInfoStruct()
                if self._libc.sysinfo(ctypes.byref(info)) == 0:
                    uptime_sec = int(info.uptime)
                    loads = (
                        info.loads[0] / 65536.0,
                        info.loads[1] / 65536.0,
                        info.loads[2] / 65536.0,
                    )
                    procs_count = int(info.procs)
            except Exception:
                pass

        # Fallback for uptime if sysinfo returned 0
        if uptime_sec == 0:
            try:
                with open("/proc/uptime", "r") as f:
                    uptime_sec = int(float(f.read().split()[0]))
            except Exception:
                pass

        # Format uptime string
        days = uptime_sec // 86400
        hours = (uptime_sec % 86400) // 3600
        mins = (uptime_sec % 3600) // 60
        secs = uptime_sec % 60
        if days > 0:
            uptime_str = f"{days}d {hours}h {mins}m"
        elif hours > 0:
            uptime_str = f"{hours}h {mins}m {secs}s"
        else:
            uptime_str = f"{mins}m {secs}s"

        return {
            "uptime_sec": uptime_sec,
            "uptime_str": uptime_str,
            "loads": loads,
            "kernel_procs": procs_count,
            "brand": self.brand,
            "model": self.model,
            "soc": self.soc_name,
            "soc_code": self.soc_model,
            "android": self.android_version,
            "sdk": self.sdk_version,
            "kernel": self.kernel_release,
            "arch": self.machine,
            "hostname": self.hostname,
        }
