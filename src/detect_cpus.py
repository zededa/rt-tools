from pathlib import Path
import os


def detect_cpus() -> str:
    cpus = (
        _from_cgroup_v2()
        or _from_proc_stat()
        or _from_proc_cpuinfo()
        or _from_sysconf()
    )
    return str(cpus) if cpus else ""


def _from_cgroup_v2() -> int | None:
    p = Path("/sys/fs/cgroup/cpuset.cpus.effective")
    if not p.is_file():
        return None
    total = 0
    for part in p.read_text().strip().split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            total += int(hi) - int(lo) + 1
        else:
            total += 1
    return total or None


def _from_proc_stat() -> int | None:
    p = Path("/proc/stat")
    if not p.is_file():
        return None
    count = sum(
        1
        for line in p.read_text().splitlines()
        if line.startswith("cpu") and line[3:4].isdigit()
    )
    return count or None


def _from_proc_cpuinfo() -> int | None:
    p = Path("/proc/cpuinfo")
    if not p.is_file():
        return None
    count = sum(
        1 for line in p.read_text().splitlines() if line.startswith("processor")
    )
    return count or None


def _from_sysconf() -> int | None:
    n = os.sysconf("SC_NPROCESSORS_ONLN") if hasattr(os, "sysconf") else 0
    if n > 0:
        return n
    n = os.sysconf("SC_NPROCESSORS_CONF") if hasattr(os, "sysconf") else 0
    return n if n > 0 else None
