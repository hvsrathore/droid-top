"""
DroidTop - Heterogeneous CPU Architecture & Frequency Collector.
Handles big.LITTLE / DynamIQ clusters, per-core frequencies, governors, and utilization history.
"""

import os
import glob
import time
from typing import Dict, List, Optional, Tuple


class CPUCluster:
    """Represents a hardware CPU frequency cluster (e.g. Little, Big, Prime)."""

    def __init__(self, policy_id: str, name: str, cpus: List[int], min_mhz: int, max_mhz: int, governor: str):
        self.policy_id = policy_id
        self.name = name
        self.cpus = cpus
        self.min_mhz = min_mhz
        self.max_mhz = max_mhz
        self.governor = governor
        self.last_time_in_state: Dict[int, int] = {}
        self.usage_pct: float = 0.0


class CPUCollector:
    """Collects CPU stats, core frequencies, cluster loads, and maintains history."""

    def __init__(self, history_size: int = 120):
        self.history_size = history_size
        self.cpu_history: List[float] = [0.0] * 20
        self.clusters: List[CPUCluster] = []
        self.core_min_max: Dict[int, Tuple[int, int]] = {}
        self.core_history: Dict[int, List[float]] = {}
        self.last_proc_stat: Dict[str, Tuple[int, int]] = {}  # cpu_id -> (work, total)
        self.proc_stat_available = False

        self._discover_clusters()
        self._check_proc_stat()

    def _discover_clusters(self):
        """Discover CPU clusters from /sys/devices/system/cpu/cpufreq/policy*."""
        policies = {}
        policy_dirs = sorted(glob.glob("/sys/devices/system/cpu/cpufreq/policy*"))

        for p in policy_dirs:
            pol_id = os.path.basename(p)
            cpus_f = os.path.join(p, "affected_cpus")
            min_f = os.path.join(p, "cpuinfo_min_freq")
            max_f = os.path.join(p, "cpuinfo_max_freq")
            gov_f = os.path.join(p, "scaling_governor")

            cpus = []
            if os.path.exists(cpus_f):
                try:
                    with open(cpus_f) as f:
                        cpus = [int(x) for x in f.read().split()]
                except Exception:
                    pass

            min_mhz = 0
            if os.path.exists(min_f):
                try:
                    with open(min_f) as f:
                        min_mhz = int(f.read().strip()) // 1000
                except Exception:
                    pass

            max_mhz = 0
            if os.path.exists(max_f):
                try:
                    with open(max_f) as f:
                        max_mhz = int(f.read().strip()) // 1000
                except Exception:
                    pass

            gov = ""
            if os.path.exists(gov_f):
                try:
                    with open(gov_f) as f:
                        gov = f.read().strip()
                except Exception:
                    pass

            policies[pol_id] = {
                "cpus": cpus,
                "min": min_mhz,
                "max": max_mhz,
                "gov": gov,
            }
            for cpu in cpus:
                self.core_min_max[cpu] = (min_mhz, max_mhz)
                self.core_history[cpu] = [0.0] * 15

        # Heuristic cluster naming by max frequency
        sorted_pols = sorted(policies.items(), key=lambda x: (x[1]["max"], len(x[1]["cpus"])))
        if len(sorted_pols) == 3:
            names = ["Little (Efficiency)", "Big (Performance)", "Prime (Super)"]
        elif len(sorted_pols) == 2:
            names = ["Little (Efficiency)", "Big (Performance)"]
        else:
            names = [f"Cluster {i}" for i in range(len(sorted_pols))]

        self.clusters = []
        for i, (pol_id, d) in enumerate(sorted_pols):
            name = names[i] if i < len(names) else f"Cluster {i}"
            cluster = CPUCluster(
                policy_id=pol_id,
                name=name,
                cpus=d["cpus"],
                min_mhz=d["min"],
                max_mhz=d["max"],
                governor=d["gov"],
            )
            self.clusters.append(cluster)

        # Fallback if no cpufreq policies found
        if not self.clusters:
            # Check present cores
            cores = self._get_present_cores()
            for c in cores:
                self.core_min_max[c] = (400, 2400)
                self.core_history[c] = [0.0] * 15
            self.clusters.append(CPUCluster("policy0", "CPU", cores, 400, 2400, "unknown"))

    def _get_present_cores(self) -> List[int]:
        path = "/sys/devices/system/cpu/present"
        if os.path.exists(path):
            try:
                with open(path) as f:
                    content = f.read().strip()
                # e.g. "0-7"
                if "-" in content:
                    start, end = content.split("-")
                    return list(range(int(start), int(end) + 1))
            except Exception:
                pass
        return list(range(os.cpu_count() or 4))

    def _check_proc_stat(self):
        try:
            with open("/proc/stat", "r") as f:
                f.readline()
            self.proc_stat_available = True
        except Exception:
            self.proc_stat_available = False

    def _read_time_in_state(self, policy_id: str) -> Dict[int, int]:
        path = f"/sys/devices/system/cpu/cpufreq/{policy_id}/stats/time_in_state"
        d = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) == 2:
                            d[int(parts[0])] = int(parts[1])
            except Exception:
                pass
        return d

    def update(self) -> Dict:
        """Fetch current CPU metrics and update histories."""
        cores_info = []
        all_cores = sorted(self.core_min_max.keys())
        if not all_cores:
            all_cores = self._get_present_cores()

        # 1. Read per-core frequencies
        for c in all_cores:
            freq_path = f"/sys/devices/system/cpu/cpu{c}/cpufreq/scaling_cur_freq"
            mhz = 0
            if os.path.exists(freq_path):
                try:
                    with open(freq_path) as f:
                        mhz = int(f.read().strip()) // 1000
                except Exception:
                    pass

            min_mhz, max_mhz = self.core_min_max.get(c, (400, 2400))
            if max_mhz > min_mhz:
                pct = max(0.0, min(100.0, ((mhz - min_mhz) / (max_mhz - min_mhz)) * 100.0))
            else:
                pct = 0.0

            if c not in self.core_history:
                self.core_history[c] = [0.0] * 15
            self.core_history[c].append(pct)
            if len(self.core_history[c]) > 20:
                self.core_history[c].pop(0)

            cores_info.append({
                "core": c,
                "mhz": mhz,
                "min_mhz": min_mhz,
                "max_mhz": max_mhz,
                "pct": pct,
                "history": list(self.core_history[c]),
            })

        # 2. Cluster Loads
        total_cluster_weighted = 0.0
        total_cluster_weight = 0

        for cluster in self.clusters:
            tis = self._read_time_in_state(cluster.policy_id)
            if tis and cluster.last_time_in_state:
                # Calculate active vs idle deltas
                deltas = {}
                for freq, ticks in tis.items():
                    prev = cluster.last_time_in_state.get(freq, ticks)
                    diff = max(0, ticks - prev)
                    if diff > 0:
                        deltas[freq] = diff

                total_ticks = sum(deltas.values())
                if total_ticks > 0 and cluster.max_mhz > 0:
                    # Weighted frequency load
                    work = sum(freq * ticks for freq, ticks in deltas.items())
                    max_work = (cluster.max_mhz * 1000) * total_ticks
                    cluster.usage_pct = min(100.0, (work / max_work) * 100.0) if max_work > 0 else 0.0
                else:
                    cluster.usage_pct = 0.0
            else:
                # Fallback: average of core pct in this cluster
                c_pcts = [ci["pct"] for ci in cores_info if ci["core"] in cluster.cpus]
                cluster.usage_pct = sum(c_pcts) / len(c_pcts) if c_pcts else 0.0

            if tis:
                cluster.last_time_in_state = tis

            weight = len(cluster.cpus)
            total_cluster_weighted += cluster.usage_pct * weight
            total_cluster_weight += weight

        # 3. Overall CPU utilization
        if total_cluster_weight > 0:
            overall_pct = total_cluster_weighted / total_cluster_weight
        elif cores_info:
            overall_pct = sum(ci["pct"] for ci in cores_info) / len(cores_info)
        else:
            overall_pct = 0.0

        self.cpu_history.append(overall_pct)
        if len(self.cpu_history) > self.history_size:
            self.cpu_history.pop(0)

        return {
            "overall_pct": overall_pct,
            "history": list(self.cpu_history),
            "cores": cores_info,
            "clusters": [
                {
                    "name": cl.name,
                    "policy": cl.policy_id,
                    "cpus": cl.cpus,
                    "min_mhz": cl.min_mhz,
                    "max_mhz": cl.max_mhz,
                    "gov": cl.governor,
                    "usage_pct": cl.usage_pct,
                }
                for cl in self.clusters
            ],
            "total_cores": len(cores_info),
        }
