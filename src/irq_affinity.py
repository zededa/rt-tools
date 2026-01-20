#! /usr/bin/env python3
import os
import glob
import sys
from typing import Set, List


def parse_cpu_list(cpu_list_str: str) -> Set[int]:
    cpus: Set[int] = set()
    try:
        for part in cpu_list_str.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                cpus.update(range(start, end + 1))
            else:
                cpus.add(int(part))
    except ValueError:
        print(f"Error: Invalid CPU format '{cpu_list_str}'", file=sys.stderr)
    return cpus


def set_irq_affinity(housekeeping_cores: str) -> None:
    """
    Moves IRQs and RCU threads to the specified housekeeping cores.
    :param housekeeping_cores: String representation of cores, e.g., "0-1"
    """
    print(f"Applying irq affinity configuration to cores: {housekeeping_cores}")

    # Checks if housekeeping_cores are in the right format
    # set is used for os.sched_setaffinity
    cpu_affinity_set: Set[int] = parse_cpu_list(housekeeping_cores)
    if not cpu_affinity_set:
        return

    # --- Part 1: IRQ Affinity ---
    search_pattern = "proc/irq/*/smp_affinity_list"
    count_irq = 0

    for file_path in glob.glob(search_pattern):
        try:
            parts = file_path.split(os.sep)
            # Path structure: /proc/irq/<irq_num>/smp_affinity_list
            irq_num = parts[-2]

            # Skip non-numeric IRQ names (like SUB directories)
            if not irq_num.isdigit():
                continue

            with open(file_path, "w") as f:
                f.write(f"{housekeeping_cores}\n")
                count_irq += 1
        except OSError:
            print(f"Error; failed to configure {file_path}")
            pass

    print(f" -> updated affinity for {count_irq} IRQs.")

    # --- Part 2: RCU Offloading ---
    count_rcu = 0
    pids = [p for p in os.listdir("/proc") if p.isdigit()]

    for pid in pids:
        try:
            pid_int = int(pid)
            with open(os.path.join("/proc", pid, "comm"), "r") as f:
                comm = f.read.strip()

            if "rcu" in comm:
                os.sched_setaffinity(pid_int, cpu_affinity_set)
                count_rcu += 1

        except (OSError, ValueError):
            print(f"Error: Failed to set {pid}")

    print(f" -> Pinned {count_rcu} RCU tasks to cores {housekeeping_cores}.")
