"""
DroidTop - Interactive Process Collector & Signal Manager.
Monitors process list, CPU%, memory usage, threads, filter queries, and signal handling.
"""

import os
import time
import signal
import shutil
import pwd
from typing import Dict, List, Optional, Tuple


class ProcessInfo:
    """Represents a snapshot of a running process."""

    def __init__(
        self,
        pid: int,
        name: str,
        user: str,
        state: str,
        threads: int,
        rss_mb: float,
        cpu_pct: float,
        mem_pct: float,
        cmdline: str,
    ):
        self.pid = pid
        self.name = name
        self.user = user
        self.state = state
        self.threads = threads
        self.rss_mb = rss_mb
        self.cpu_pct = cpu_pct
        self.mem_pct = mem_pct
        self.cmdline = cmdline

    def matches_filter(self, query: str) -> bool:
        if not query:
            return True
        q = query.lower()
        return (
            q in str(self.pid)
            or q in self.name.lower()
            or q in self.cmdline.lower()
            or q in self.user.lower()
        )


class ProcessCollector:
    """Collects and calculates real-time process statistics."""

    SORT_COLUMNS = ["CPU%", "MEM%", "PID", "NAME", "THREADS"]

    def __init__(self):
        self.prev_times: Dict[int, Tuple[int, float]] = {}  # pid -> (ticks, timestamp)
        self.clk_tck = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
        self.uid_cache: Dict[int, str] = {}
        self.sort_by = "CPU%"
        self.sort_desc = True
        self.filter_query = ""
        self.has_su = shutil.which("su") is not None
        self.is_root = (os.geteuid() == 0) if hasattr(os, "geteuid") else False

    def _get_username(self, uid: int) -> str:
        if uid in self.uid_cache:
            return self.uid_cache[uid]
        try:
            name = pwd.getpwuid(uid).pw_name
        except Exception:
            name = f"u_{uid}"
        self.uid_cache[uid] = name
        return name

    def update(self, total_ram_mb: float = 12000.0) -> List[ProcessInfo]:
        """Scan /proc, compute deltas, and return sorted, filtered processes."""
        now = time.time()
        procs: List[ProcessInfo] = []
        new_times: Dict[int, Tuple[int, float]] = {}

        try:
            pids = [int(p) for p in os.listdir("/proc") if p.isdigit()]
        except Exception:
            pids = []

        for pid in pids:
            stat_path = f"/proc/{pid}/stat"
            if not os.path.exists(stat_path):
                continue
            try:
                with open(stat_path, "r") as f:
                    content = f.read()

                # Robust parsing: comm is between first '(' and last ')'
                lparen = content.find("(")
                rparen = content.rfind(")")
                if lparen == -1 or rparen == -1:
                    continue
                comm = content[lparen + 1:rparen]
                rest = content[rparen + 2:].split()

                state = rest[0]
                utime = int(rest[11])
                stime = int(rest[12])
                rss_pages = int(rest[21])
                total_ticks = utime + stime

                # CPU% Calculation
                cpu_pct = 0.0
                if pid in self.prev_times:
                    prev_ticks, prev_t = self.prev_times[pid]
                    dt = now - prev_t
                    if dt > 0.1:
                        dticks = total_ticks - prev_ticks
                        cpu_pct = max(0.0, ((dticks / self.clk_tck) / dt) * 100.0)

                new_times[pid] = (total_ticks, now)

                # Threads
                threads = 1
                task_dir = f"/proc/{pid}/task"
                if os.path.isdir(task_dir):
                    try:
                        threads = len(os.listdir(task_dir))
                    except Exception:
                        pass

                # Cmdline
                cmdline = ""
                cmdline_path = f"/proc/{pid}/cmdline"
                if os.path.exists(cmdline_path):
                    try:
                        with open(cmdline_path, "rb") as f:
                            raw_cmd = f.read().replace(b"\x00", b" ").strip()
                            cmdline = raw_cmd.decode("utf-8", errors="replace")
                    except Exception:
                        pass
                if not cmdline:
                    cmdline = f"[{comm}]"
                else:
                    cmdline = cmdline.replace("\n", " ").replace("\r", " ")

                # UID / User
                uid = 0
                try:
                    uid = os.stat(stat_path).st_uid
                except Exception:
                    pass
                user = self._get_username(uid)

                rss_mb = (rss_pages * 4096.0) / (1024.0 * 1024.0)
                mem_pct = (rss_mb / total_ram_mb * 100.0) if total_ram_mb > 0 else 0.0

                p_info = ProcessInfo(
                    pid=pid,
                    name=comm,
                    user=user,
                    state=state,
                    threads=threads,
                    rss_mb=rss_mb,
                    cpu_pct=cpu_pct,
                    mem_pct=mem_pct,
                    cmdline=cmdline,
                )
                procs.append(p_info)
            except Exception:
                continue

        self.prev_times = new_times

        # Filter
        if self.filter_query:
            procs = [p for p in procs if p.matches_filter(self.filter_query)]

        # Sort
        if self.sort_by == "CPU%":
            procs.sort(key=lambda x: x.cpu_pct, reverse=self.sort_desc)
        elif self.sort_by == "MEM%":
            procs.sort(key=lambda x: x.rss_mb, reverse=self.sort_desc)
        elif self.sort_by == "PID":
            procs.sort(key=lambda x: x.pid, reverse=self.sort_desc)
        elif self.sort_by == "NAME":
            procs.sort(key=lambda x: x.name.lower(), reverse=self.sort_desc)
        elif self.sort_by == "THREADS":
            procs.sort(key=lambda x: x.threads, reverse=self.sort_desc)

        return procs

    def cycle_sort(self):
        """Cycle through available sort columns."""
        idx = self.SORT_COLUMNS.index(self.sort_by)
        self.sort_by = self.SORT_COLUMNS[(idx + 1) % len(self.SORT_COLUMNS)]

    def toggle_sort_direction(self):
        """Toggle ascending / descending sort."""
        self.sort_desc = not self.sort_desc

    def send_signal(self, pid: int, sig: int) -> Tuple[bool, str]:
        """Send a signal to a process."""
        try:
            os.kill(pid, sig)
            sig_name = signal.Signals(sig).name
            return (True, f"Sent {sig_name} to PID {pid}")
        except ProcessLookupError:
            return (False, f"PID {pid} not found")
        except PermissionError:
            return (False, f"Permission denied for PID {pid}")
        except Exception as e:
            return (False, str(e))
