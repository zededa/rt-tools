import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

_CGROUP_V2_PATHS = (Path("/sys/fs/cgroup/cpuset.cpus.effective"),)

_CGROUP_V1_PATHS = (
    Path("/sys/fs/cgroup/cpuset/cpuset.cpus"),
    Path("/sys/fs/cgroup/cpuset/cpuset.effective_cpus"),
)


def detect_cpus() -> str:
    """Detect which CPUs this process/container is allowed to run on.

    Returns the cpuset string (e.g. "9,11" or "2-5").

    Prefers RT_BENCHMARK_CORES env var (set by entrypoint.sh) which
    excludes the housekeeping core. Falls back to cgroup, /proc/stat,
    or sysconf.
    """
    # Entrypoint sets this to the clean cores (excluding housekeeping)
    env_cores = os.environ.get("RT_BENCHMARK_CORES", "").strip()
    if env_cores:
        log.info("Detected CPUs from RT_BENCHMARK_CORES env: %s", env_cores)
        return env_cores

    for source, result in (
        ("cgroup-v2", _from_cgroup_v2),
        ("cgroup-v1", _from_cgroup_v1),
        ("/proc/stat", _from_proc_stat),
        ("sysconf", _from_sysconf),
    ):
        cpus = result()
        if cpus:
            log.info("Detected CPUs from %s: %s", source, cpus)
            return cpus
        log.debug("CPU detection via %s: not available", source)

    log.warning("Could not detect CPUs from any source")
    return ""


def _from_cgroup_v2() -> str | None:
    """Read allowed CPUs from cgroup v2 cpuset controller."""
    for p in _CGROUP_V2_PATHS:
        if p.is_file():
            content = p.read_text().strip()
            if content:
                return content
    return None


def _from_cgroup_v1() -> str | None:
    """Read allowed CPUs from cgroup v1 cpuset controller."""
    for p in _CGROUP_V1_PATHS:
        if p.is_file():
            content = p.read_text().strip()
            if content:
                return content
    return None


def _from_proc_stat() -> str | None:
    """Parse /proc/stat to find online CPU numbers and return as list."""
    p = Path("/proc/stat")
    if not p.is_file():
        return None
    cpus = []
    for line in p.read_text().splitlines():
        if line.startswith("cpu") and line[3:4].isdigit():
            # line looks like "cpu0 ..." — extract the number
            tag = line.split()[0]
            cpus.append(int(tag[3:]))
    if not cpus:
        return None
    return _compact(sorted(cpus))


def _from_sysconf() -> str | None:
    """Fall back to os.sysconf for online CPU count, return 0..N-1 range."""
    if not hasattr(os, "sysconf"):
        return None
    n = os.sysconf("SC_NPROCESSORS_ONLN")
    if n <= 0:
        n = os.sysconf("SC_NPROCESSORS_CONF")
    if n <= 0:
        return None
    return f"0-{n - 1}" if n > 1 else "0"


def _compact(cpus: list[int]) -> str:
    """Turn a sorted list of ints into a compact range string.

    e.g. [0, 1, 2, 5, 7, 8, 9] -> "0-2,5,7-9"
    """
    if not cpus:
        return ""
    ranges: list[str] = []
    start = prev = cpus[0]
    for c in cpus[1:]:
        if c == prev + 1:
            prev = c
        else:
            ranges.append(f"{start}-{prev}" if start != prev else str(start))
            start = prev = c
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ",".join(ranges)
