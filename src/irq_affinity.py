#!/usr/bin/env python3
import os
import sys


def set_irq_affinity(core_list_str: str) -> None:
    """
    Sets IRQ and RCU affinity using the logic from the bash script:
    1. Parses /proc/interrupts (ignoring IRQ 0 and 2).
    2. Finds RCU processes via /proc and pins them.
    """
    print(f"--- Configuring Affinity for Cores: {core_list_str} ---")

    cpu_set = set()
    try:
        for part in core_list_str.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                cpu_set.update(range(start, end + 1))
            else:
                cpu_set.add(int(part))
    except ValueError:
        print(f"Error: Invalid CPU format '{core_list_str}'", file=sys.stderr)
        return

    irq_count = 0
    try:
        with open("/proc/interrupts", "r") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue

                # grep '^ *[0-9]*[0-9]:' | awk {'print $1'} | sed 's/:$//'
                irq_token = parts[0].rstrip(":")

                if not irq_token.isdigit():
                    continue

                irq_num = int(irq_token)

                # explicit checks to skip Timer (0) and Cascade (2)
                if irq_num == 0 or irq_num == 2:
                    continue

                # Apply affinity
                affinity_path = f"/proc/irq/{irq_num}/smp_affinity_list"
                if os.path.exists(affinity_path):
                    try:
                        with open(affinity_path, "w") as af:
                            af.write(core_list_str)
                            irq_count += 1
                    except OSError:
                        # Some IRQs listed in /interrupts might not be writable
                        pass

    except FileNotFoundError:
        print("Error: /proc/interrupts not found.")

    print(f" -> Set affinity for {irq_count} IRQs (Skipped 0 & 2).")

    rcu_count = 0
    pids = [p for p in os.listdir("/proc") if p.isdigit()]

    for pid in pids:
        try:
            pid_int = int(pid)
            with open(os.path.join("/proc", pid, "comm"), "r") as f:
                comm = f.read().strip()

            if "rcu" in comm:
                os.sched_setaffinity(pid_int, cpu_set)
                rcu_count += 1

        except (OSError, ValueError):
            # Process may have ended during the loop
            continue

    print(f" -> Pinned {rcu_count} RCU tasks.")
