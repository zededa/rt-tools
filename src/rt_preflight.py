"""RT pre-flight validation.

Runs at container startup to verify the host kernel and cgroup
environment are properly configured for real-time benchmarks.

Usage:
    from src.rt_preflight import run_preflight
    run_preflight()          # logs results, raises on FAIL
    run_preflight(strict=False)  # logs results, never raises
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class Status(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    name: str
    status: Status
    message: str
    detail: str = ""


@dataclass
class PreflightReport:
    results: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    @property
    def passed(self) -> bool:
        return all(r.status != Status.FAIL for r in self.results)

    def summary(self) -> str:
        lines = [
            "",
            "=" * 64,
            "  RT PRE-FLIGHT CHECK",
            "=" * 64,
        ]
        for r in self.results:
            icon = {
                Status.PASS: "\u2705",
                Status.WARN: "\u26a0\ufe0f ",
                Status.FAIL: "\u274c",
                Status.SKIP: "\u23ed\ufe0f ",
            }.get(r.status, "?")
            lines.append(f"  {icon} [{r.status.value:4s}] {r.name}: {r.message}")
            if r.detail:
                for dl in r.detail.strip().splitlines():
                    lines.append(f"           {dl}")
        lines.append("=" * 64)
        n_pass = sum(1 for r in self.results if r.status == Status.PASS)
        n_warn = sum(1 for r in self.results if r.status == Status.WARN)
        n_fail = sum(1 for r in self.results if r.status == Status.FAIL)
        n_skip = sum(1 for r in self.results if r.status == Status.SKIP)
        lines.append(
            f"  Total: {len(self.results)}  "
            f"Pass: {n_pass}  Warn: {n_warn}  Fail: {n_fail}  Skip: {n_skip}"
        )
        verdict = "READY" if self.passed else "NOT READY"
        lines.append(f"  Verdict: {verdict}")
        lines.append("=" * 64)
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(path: str | Path) -> Optional[str]:
    """Read a file, return None if missing / unreadable."""
    try:
        return Path(path).read_text().strip()
    except (OSError, PermissionError):
        return None


def _cmdline() -> str:
    return _read("/proc/cmdline") or ""


def _cmdline_param(name: str) -> Optional[str]:
    """Extract value of name=<value> from /proc/cmdline, or None."""
    m = re.search(rf"(?:^|\s){re.escape(name)}=(\S+)", _cmdline())
    return m.group(1) if m else None


def _cmdline_has(name: str) -> bool:
    """Check if a param (with or without value) exists in cmdline."""
    return bool(re.search(rf"(?:^|\s){re.escape(name)}(?:=|\s|$)", _cmdline()))


def _max_cpu_id() -> int:
    """Return the highest possible CPU id from the kernel.

    Reads ``/sys/devices/system/cpu/possible`` (e.g. ``0-127``).
    Falls back to ``os.cpu_count() - 1``.
    """
    possible = _read("/sys/devices/system/cpu/possible")
    if possible:
        # e.g. "0-127" — take the last number
        m = re.search(r"(\d+)\s*$", possible)
        if m:
            return int(m.group(1))
    n = os.cpu_count()
    return (n - 1) if n and n > 0 else 0


def _parse_cpulist(s: str) -> set[int]:
    """Parse '1-3,5,7-9' into {1,2,3,5,7,8,9}.

    Supports open-ended ranges: ``1-N`` means CPU 1 through the last
    available CPU (read from ``/sys/devices/system/cpu/possible``).

    Non-numeric tokens (e.g. 'managed_irq', 'domain') are silently
    skipped so that ``isolcpus=managed_irq,domain,2-5`` works.
    """
    cpus: set[int] = set()
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            try:
                lo = int(lo_s)
            except ValueError:
                continue
            hi_s = hi_s.strip()
            if hi_s.upper() == "N" or hi_s == "":
                hi = _max_cpu_id()
            else:
                try:
                    hi = int(hi_s)
                except ValueError:
                    continue
            cpus.update(range(lo, hi + 1))
        else:
            try:
                cpus.add(int(part))
            except ValueError:
                continue
    return cpus


def _parse_isolcpus_flags(param: str) -> tuple[set[str], str]:
    """Parse isolcpus value into (flags, cpu_list_str).

    isolcpus can be:
      - ``isolcpus=2-5``              → flags={}, cpulist="2-5"
      - ``isolcpus=managed_irq,2-5``  → flags={"managed_irq"}, cpulist="2-5"
      - ``isolcpus=managed_irq,domain,io_queue,2-5``
                                      → flags={"managed_irq","domain","io_queue"}, cpulist="2-5"
    """
    known_flags = {"managed_irq", "domain", "io_queue"}
    flags: set[str] = set()
    cpu_parts: list[str] = []

    for token in param.split(","):
        token = token.strip()
        if token in known_flags:
            flags.add(token)
        elif token:
            cpu_parts.append(token)

    return flags, ",".join(cpu_parts)


def _kernel_version() -> tuple[int, int]:
    """Return (major, minor) kernel version from /proc/version.

    Falls back to (0, 0) if parsing fails.
    """
    version_str = _read("/proc/version") or ""
    m = re.search(r"Linux version (\d+)\.(\d+)", version_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def _get_container_cpus() -> Optional[str]:
    """Read the cpuset that this container is allowed to use."""
    for p in (
        Path("/sys/fs/cgroup/cpuset.cpus.effective"),
        Path("/sys/fs/cgroup/cpuset/cpuset.cpus"),
        Path("/sys/fs/cgroup/cpuset/cpuset.effective_cpus"),
    ):
        content = _read(p)
        if content:
            return content
    return None


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_preempt_rt() -> CheckResult:
    """Verify kernel is PREEMPT_RT."""
    name = "PREEMPT_RT kernel"

    # Method 1: /sys/kernel/realtime
    rt_flag = _read("/sys/kernel/realtime")
    if rt_flag == "1":
        uname = _read("/proc/version") or ""
        return CheckResult(
            name,
            Status.PASS,
            "RT kernel confirmed",
            detail=uname.split()[0:3].__repr__() if uname else "",
        )

    # Method 2: uname string
    version = _read("/proc/version") or ""
    if "PREEMPT_RT" in version:
        return CheckResult(
            name, Status.PASS, "RT kernel (from /proc/version)", detail=version[:120]
        )

    if "PREEMPT" in version:
        return CheckResult(
            name, Status.WARN, "PREEMPT kernel but not PREEMPT_RT", detail=version[:120]
        )

    return CheckResult(
        name,
        Status.FAIL,
        "Kernel does not appear to be PREEMPT_RT",
        detail=version[:120],
    )


def check_isolcpus() -> CheckResult:
    """Check that isolcpus is set with recommended flags and covers container CPUs."""
    name = "CPU isolation (isolcpus)"

    isolated_param = _cmdline_param("isolcpus")
    if not isolated_param:
        # Also check sysfs
        isolated_sysfs = _read("/sys/devices/system/cpu/isolated")
        if isolated_sysfs:
            isolated_param = isolated_sysfs
        else:
            return CheckResult(
                name, Status.WARN, "isolcpus not found in cmdline or sysfs"
            )

    # Parse flags and CPU list from isolcpus value
    flags, cpulist_str = _parse_isolcpus_flags(isolated_param)
    # If the value came from sysfs it's just a cpu list, no flags
    isolated_set = (
        _parse_cpulist(cpulist_str) if cpulist_str else _parse_cpulist(isolated_param)
    )

    warnings: list[str] = []

    # Check for recommended flags.
    # When any flags are present, 'domain' is NOT implied — it must be
    # specified explicitly.  Without flags isolcpus defaults to
    # domain isolation, but adding e.g. managed_irq alone disables
    # that default.
    missing_flags: list[str] = []
    if "managed_irq" not in flags:
        missing_flags.append("managed_irq")
    if "domain" not in flags:
        missing_flags.append("domain")

    if missing_flags:
        warnings.append(
            f"{', '.join(missing_flags)} flag(s) missing from isolcpus.  "
            "Note: when any flag is specified, 'domain' is no longer "
            "implied and must be listed explicitly.  Recommended: "
            "isolcpus=managed_irq,domain,<cpulist>"
        )

    kmaj, kmin = _kernel_version()
    if (kmaj, kmin) >= (6, 17) and "io_queue" not in flags:
        warnings.append(
            f"io_queue flag missing (kernel {kmaj}.{kmin} supports it) — "
            "block-layer IO completion queues may still land on isolated "
            "cores.  Recommended: isolcpus=managed_irq,domain,io_queue,<cpulist>"
        )

    # Verify container CPUs are in the isolated set
    container_cpus_str = _get_container_cpus()
    if not container_cpus_str:
        msg = f"isolcpus={isolated_param} (could not read container cpuset)"
        if warnings:
            return CheckResult(
                name,
                Status.WARN,
                msg,
                detail="\n".join(warnings),
            )
        return CheckResult(
            name,
            Status.PASS,
            msg,
            detail="Cannot verify overlap — cgroup cpuset not readable",
        )

    container_set = _parse_cpulist(container_cpus_str)
    not_isolated = container_set - isolated_set
    if not_isolated:
        warnings.insert(
            0,
            f"Container CPUs {sorted(not_isolated)} are NOT in "
            f"isolcpus={isolated_param}",
        )
        return CheckResult(
            name,
            Status.WARN,
            f"Container CPUs {sorted(not_isolated)} are NOT in isolcpus={isolated_param}",
            detail=f"Container cpuset: {container_cpus_str}\n"
            f"Isolated: {isolated_param}\n" + "\n".join(warnings),
        )

    detail = f"isolcpus={isolated_param}"
    if warnings:
        detail += "\n" + "\n".join(warnings)
        return CheckResult(
            name,
            Status.WARN,
            f"All container CPUs isolated but missing recommended flags",
            detail=detail,
        )

    return CheckResult(
        name,
        Status.PASS,
        f"All container CPUs ({container_cpus_str}) are isolated",
        detail=detail,
    )


def check_nohz_full() -> CheckResult:
    """Check nohz_full covers our container cores."""
    name = "Tickless (nohz_full)"

    nohz = _cmdline_param("nohz_full")
    if not nohz:
        return CheckResult(
            name, Status.WARN, "nohz_full not set — timer tick will interrupt RT cores"
        )

    nohz_set = _parse_cpulist(nohz)
    container_cpus_str = _get_container_cpus()
    if not container_cpus_str:
        return CheckResult(
            name, Status.PASS, f"nohz_full={nohz} (cannot verify container overlap)"
        )

    container_set = _parse_cpulist(container_cpus_str)
    missing = container_set - nohz_set
    if missing:
        return CheckResult(
            name,
            Status.WARN,
            f"Container CPUs {sorted(missing)} not in nohz_full={nohz}",
            detail="These cores will still receive timer ticks",
        )

    return CheckResult(
        name,
        Status.PASS,
        f"All container CPUs ({container_cpus_str}) are tickless",
        detail=f"nohz_full={nohz}",
    )


def check_rcu_nocbs() -> CheckResult:
    """Check rcu_nocbs covers our container cores."""
    name = "RCU offloading (rcu_nocbs)"

    rcu = _cmdline_param("rcu_nocbs")
    if not rcu:
        return CheckResult(
            name, Status.WARN, "rcu_nocbs not set — RCU callbacks may run on RT cores"
        )

    rcu_set = _parse_cpulist(rcu)
    container_cpus_str = _get_container_cpus()
    if not container_cpus_str:
        return CheckResult(
            name, Status.PASS, f"rcu_nocbs={rcu} (cannot verify container overlap)"
        )

    container_set = _parse_cpulist(container_cpus_str)
    missing = container_set - rcu_set
    if missing:
        return CheckResult(
            name,
            Status.WARN,
            f"Container CPUs {sorted(missing)} not in rcu_nocbs={rcu}",
        )

    return CheckResult(
        name,
        Status.PASS,
        f"All container CPUs ({container_cpus_str}) have RCU callbacks offloaded",
        detail=f"rcu_nocbs={rcu}",
    )


def check_irqaffinity() -> CheckResult:
    """Check irqaffinity is set to housekeeping cores only."""
    name = "IRQ affinity (irqaffinity)"

    affinity = _cmdline_param("irqaffinity")
    if not affinity:
        return CheckResult(
            name,
            Status.WARN,
            "irqaffinity not set in cmdline — IRQs may land on RT cores",
        )

    affinity_set = _parse_cpulist(affinity)
    container_cpus_str = _get_container_cpus()
    if container_cpus_str:
        container_set = _parse_cpulist(container_cpus_str)
        overlap = container_set & affinity_set
        if overlap:
            return CheckResult(
                name,
                Status.WARN,
                f"irqaffinity={affinity} overlaps container CPUs {sorted(overlap)}",
                detail="IRQs may be routed to RT cores",
            )

    return CheckResult(
        name, Status.PASS, f"IRQs pinned to housekeeping cores ({affinity})"
    )


def check_cstates() -> CheckResult:
    """Verify C-states are disabled."""
    name = "C-states disabled"

    cstate_params = [
        "intel.max_cstate",
        "intel_idle.max_cstate",
        "processor.max_cstate",
        "processor_idle.max_cstate",
    ]

    cmdline = _cmdline()
    found = {}
    for param in cstate_params:
        val = _cmdline_param(param)
        if val is not None:
            found[param] = val

    if not found:
        return CheckResult(
            name,
            Status.WARN,
            "No max_cstate parameters found in cmdline",
            detail="C-states may cause latency spikes",
        )

    non_zero = {k: v for k, v in found.items() if v != "0"}
    if non_zero:
        return CheckResult(
            name,
            Status.WARN,
            f"Some max_cstate params are not 0: {non_zero}",
            detail="\n".join(f"  {k}={v}" for k, v in found.items()),
        )

    detail = "\n".join(f"  {k}={v}" for k, v in found.items())
    return CheckResult(
        name, Status.PASS, "All C-states disabled via kernel cmdline", detail=detail
    )


def check_intel_pstate() -> CheckResult:
    """Check intel_pstate is disabled (allows direct freq control)."""
    name = "Intel P-state driver"

    val = _cmdline_param("intel_pstate")
    if val == "disable":
        return CheckResult(name, Status.PASS, "intel_pstate=disable (good for RT)")

    if val:
        return CheckResult(
            name,
            Status.WARN,
            f"intel_pstate={val} — consider intel_pstate=disable for RT",
        )

    # Check if the driver is active
    pstate_dir = Path("/sys/devices/system/cpu/intel_pstate")
    if pstate_dir.is_dir():
        return CheckResult(
            name, Status.WARN, "intel_pstate driver is active — frequency may fluctuate"
        )

    return CheckResult(name, Status.PASS, "intel_pstate not active")


def check_cpu_governor() -> CheckResult:
    """Check CPU frequency governor on container cores."""
    name = "CPU frequency governor"

    container_cpus_str = _get_container_cpus()
    if not container_cpus_str:
        return CheckResult(name, Status.SKIP, "Cannot determine container CPUs")

    governors: dict[str, list[int]] = {}
    for cpu in sorted(_parse_cpulist(container_cpus_str)):
        gov = _read(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor")
        if gov:
            governors.setdefault(gov, []).append(cpu)

    if not governors:
        # intel_pstate=disable + no cpufreq driver = no governor file
        pstate_val = _cmdline_param("intel_pstate")
        if pstate_val == "disable":
            return CheckResult(
                name,
                Status.PASS,
                "No cpufreq governor (intel_pstate disabled, frequency is fixed)",
            )
        return CheckResult(
            name, Status.SKIP, "Could not read governor for any container CPU"
        )

    if set(governors.keys()) == {"performance"}:
        return CheckResult(
            name, Status.PASS, "All container CPUs on 'performance' governor"
        )

    detail_lines = []
    for gov, cpus in sorted(governors.items()):
        detail_lines.append(f"  {gov}: CPUs {cpus}")
    non_perf = {g for g in governors if g != "performance"}
    return CheckResult(
        name,
        Status.WARN,
        f"Non-performance governors found: {non_perf}",
        detail="\n".join(detail_lines),
    )


def check_clocksource() -> CheckResult:
    """Verify clocksource is TSC."""
    name = "Clocksource"

    current = _read("/sys/devices/system/clocksource/clocksource0/current_clocksource")
    if not current:
        return CheckResult(name, Status.SKIP, "Cannot read current clocksource")

    available = (
        _read("/sys/devices/system/clocksource/clocksource0/available_clocksource")
        or ""
    )

    if current == "tsc":
        return CheckResult(
            name, Status.PASS, "Clocksource is TSC", detail=f"Available: {available}"
        )

    return CheckResult(
        name,
        Status.WARN,
        f"Clocksource is '{current}' (TSC preferred for RT)",
        detail=f"Available: {available}",
    )


def check_numa_balancing() -> CheckResult:
    """Check NUMA balancing is disabled."""
    name = "NUMA balancing"

    val = _cmdline_param("numa_balancing")
    if val == "disable":
        return CheckResult(name, Status.PASS, "NUMA balancing disabled via cmdline")

    sysctl = _read("/proc/sys/kernel/numa_balancing")
    if sysctl == "0":
        return CheckResult(name, Status.PASS, "NUMA balancing disabled (sysctl)")

    if sysctl == "1":
        return CheckResult(
            name,
            Status.WARN,
            "NUMA balancing is enabled — may cause latency jitter",
            detail="Set numa_balancing=disable on kernel cmdline",
        )

    return CheckResult(name, Status.SKIP, "Cannot determine NUMA balancing state")


def check_split_lock() -> CheckResult:
    """Check split_lock_detect is off."""
    name = "Split-lock detection"

    val = _cmdline_param("split_lock_detect")
    if val == "off":
        return CheckResult(name, Status.PASS, "split_lock_detect=off")

    if val:
        return CheckResult(
            name,
            Status.WARN,
            f"split_lock_detect={val} — may cause unexpected #AC exceptions",
        )

    return CheckResult(name, Status.WARN, "split_lock_detect not set in cmdline")


def check_hugepages() -> CheckResult:
    """Check hugepages are allocated."""
    name = "Hugepages"

    cmdline_val = _cmdline_param("hugepages")
    nr = _read("/proc/sys/vm/nr_hugepages")
    free = _read("/proc/meminfo")

    hp_info = ""
    if free:
        for line in free.splitlines():
            if "Huge" in line:
                hp_info += f"  {line.strip()}\n"

    if cmdline_val and int(cmdline_val) > 0:
        return CheckResult(
            name,
            Status.PASS,
            f"hugepages={cmdline_val} configured",
            detail=hp_info.rstrip(),
        )

    if nr and int(nr) > 0:
        return CheckResult(
            name, Status.PASS, f"{nr} hugepages available", detail=hp_info.rstrip()
        )

    return CheckResult(name, Status.WARN, "No hugepages configured")


def check_container_cpuset() -> CheckResult:
    """Report which CPUs this container is pinned to."""
    name = "Container cpuset"

    cpus = _get_container_cpus()
    if not cpus:
        return CheckResult(
            name,
            Status.FAIL,
            "Cannot detect container CPU assignment",
            detail="Checked cgroup v1 and v2 cpuset paths",
        )

    cpu_set = _parse_cpulist(cpus)
    return CheckResult(
        name, Status.PASS, f"Pinned to CPUs: {cpus} ({len(cpu_set)} cores)"
    )


def check_kernel_thread_priorities() -> CheckResult:
    """Scan for kernel threads running at priority >= 90 that could interfere."""
    name = "Kernel thread priorities"

    container_cpus_str = _get_container_cpus()
    container_set = _parse_cpulist(container_cpus_str) if container_cpus_str else None

    high_prio: list[str] = []
    proc = Path("/proc")
    for pid_dir in proc.iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            comm = (pid_dir / "comm").read_text().strip()
            sched_lines = (pid_dir / "sched").read_text().splitlines()
            # Check if it's an RT task by reading /proc/<pid>/stat
            stat = (pid_dir / "stat").read_text()
            # Field 41 is the policy (1=FIFO, 2=RR) and field 18 is priority
            fields = stat.rsplit(")", 1)[-1].split()
            # fields[0] = state, fields[15] = priority, fields[38] = rt_priority, fields[39] = policy
            if len(fields) > 39:
                rt_prio = int(
                    fields[37]
                )  # rt_priority (0-indexed from field after ')')
                policy = int(fields[38])
                if policy in (1, 2) and rt_prio >= 90:
                    # Check CPU affinity if possible
                    try:
                        affinity = os.sched_getaffinity(int(pid_dir.name))
                        if container_set and affinity & container_set:
                            high_prio.append(
                                f"PID {pid_dir.name} ({comm}): "
                                f"policy={'FIFO' if policy == 1 else 'RR'} "
                                f"prio={rt_prio} cpus={sorted(affinity & container_set)}"
                            )
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError, ValueError, IndexError):
            continue

    if not high_prio:
        return CheckResult(
            name, Status.PASS, "No competing high-priority RT threads on container CPUs"
        )

    return CheckResult(
        name,
        Status.WARN,
        f"{len(high_prio)} kernel thread(s) at RT priority >= 90 on container CPUs",
        detail="\n".join(high_prio),
    )


def check_capabilities() -> CheckResult:
    """Report container Linux capabilities and verify RT-required ones."""
    name = "Container capabilities"

    # All known Linux capabilities (as of kernel 6.x)
    _CAP_NAMES = {
        0: "CAP_CHOWN",
        1: "CAP_DAC_OVERRIDE",
        2: "CAP_DAC_READ_SEARCH",
        3: "CAP_FOWNER",
        4: "CAP_FSETID",
        5: "CAP_KILL",
        6: "CAP_SETGID",
        7: "CAP_SETUID",
        8: "CAP_SETPCAP",
        9: "CAP_LINUX_IMMUTABLE",
        10: "CAP_NET_BIND_SERVICE",
        11: "CAP_NET_BROADCAST",
        12: "CAP_NET_ADMIN",
        13: "CAP_NET_RAW",
        14: "CAP_IPC_LOCK",
        15: "CAP_IPC_OWNER",
        16: "CAP_SYS_MODULE",
        17: "CAP_SYS_RAWIO",
        18: "CAP_SYS_CHROOT",
        19: "CAP_SYS_PTRACE",
        20: "CAP_SYS_PACCT",
        21: "CAP_SYS_ADMIN",
        22: "CAP_SYS_BOOT",
        23: "CAP_SYS_NICE",
        24: "CAP_SYS_RESOURCE",
        25: "CAP_SYS_TIME",
        26: "CAP_SYS_TTY_CONFIG",
        27: "CAP_MKNOD",
        28: "CAP_LEASE",
        29: "CAP_AUDIT_WRITE",
        30: "CAP_AUDIT_CONTROL",
        31: "CAP_SETFCAP",
        32: "CAP_MAC_OVERRIDE",
        33: "CAP_MAC_ADMIN",
        34: "CAP_SYSLOG",
        35: "CAP_WAKE_ALARM",
        36: "CAP_BLOCK_SUSPEND",
        37: "CAP_AUDIT_READ",
        38: "CAP_PERFMON",
        39: "CAP_BPF",
        40: "CAP_CHECKPOINT_RESTORE",
    }

    # Capabilities required for RT benchmarks
    _RT_REQUIRED = {
        23: "CAP_SYS_NICE",  # chrt, sched_setscheduler, RT priorities
        14: "CAP_IPC_LOCK",  # mlockall, locking memory pages
        21: "CAP_SYS_ADMIN",  # cgroup, /dev access, various RT ops
    }

    # Nice to have for RT
    _RT_OPTIONAL = {
        17: "CAP_SYS_RAWIO",  # MSR access (SMI counters, etc.)
        24: "CAP_SYS_RESOURCE",  # override RLIMIT_RTPRIO
        12: "CAP_NET_ADMIN",  # network tuning, IRQ affinity
    }

    status_text = _read("/proc/self/status")
    if not status_text:
        return CheckResult(name, Status.SKIP, "Cannot read /proc/self/status")

    # Parse CapEff (effective), CapPrm (permitted), CapBnd (bounding)
    caps: dict[str, int] = {}
    for line in status_text.splitlines():
        for field in ("CapEff", "CapPrm", "CapBnd"):
            if line.startswith(f"{field}:"):
                caps[field] = int(line.split(":")[1].strip(), 16)

    cap_eff = caps.get("CapEff", 0)

    def _decode(bitmask: int) -> list[str]:
        found = []
        for bit in range(41):
            if bitmask & (1 << bit):
                found.append(_CAP_NAMES.get(bit, f"CAP_{bit}"))
        return found

    effective = _decode(cap_eff)

    # Check required caps
    missing_required = []
    for bit, cap_name in _RT_REQUIRED.items():
        if not (cap_eff & (1 << bit)):
            missing_required.append(cap_name)

    missing_optional = []
    for bit, cap_name in _RT_OPTIONAL.items():
        if not (cap_eff & (1 << bit)):
            missing_optional.append(cap_name)

    # Build detail: show all effective caps
    detail_lines = [f"Effective ({len(effective)}): {', '.join(effective)}"]
    if missing_optional:
        detail_lines.append(f"Optional missing: {', '.join(missing_optional)}")

    detail = "\n".join(detail_lines)

    if missing_required:
        return CheckResult(
            name,
            Status.FAIL,
            f"Missing required RT capabilities: {', '.join(missing_required)}",
            detail=detail,
        )

    if missing_optional:
        return CheckResult(
            name,
            Status.WARN,
            f"All required caps present, optional missing: {', '.join(missing_optional)}",
            detail=detail,
        )

    return CheckResult(
        name,
        Status.PASS,
        f"All RT capabilities present ({len(effective)} total effective)",
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    check_container_cpuset,
    check_capabilities,
    check_preempt_rt,
    check_isolcpus,
    check_nohz_full,
    check_rcu_nocbs,
    check_irqaffinity,
    check_cstates,
    check_intel_pstate,
    check_cpu_governor,
    check_clocksource,
    check_numa_balancing,
    check_split_lock,
    check_hugepages,
    check_kernel_thread_priorities,
]


def run_preflight(strict: bool = True) -> PreflightReport:
    """Run all pre-flight checks.

    Args:
        strict: If True, raise RuntimeError when any check FAILs.

    Returns:
        PreflightReport with all results.
    """
    report = PreflightReport()

    for check_fn in ALL_CHECKS:
        try:
            result = check_fn()
        except Exception as exc:
            result = CheckResult(
                name=check_fn.__doc__ or check_fn.__name__,
                status=Status.SKIP,
                message=f"Check raised exception: {exc}",
            )
        report.add(result)

    summary = report.summary()
    # Always print to stdout so it's visible in container logs
    print(summary)
    # Also log it
    log.info(summary)

    if strict and not report.passed:
        raise RuntimeError(
            "RT pre-flight checks failed. "
            "Fix the issues above or pass strict=False to skip."
        )

    return report


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, format="%(levelname)s %(name)s - %(message)s"
    )
    run_preflight(strict=False)
