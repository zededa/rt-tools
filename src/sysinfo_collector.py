import os
import platform
import subprocess
import json
from datetime import datetime
from glob import glob


class SystemInfoCollector:
    def __init__(self, output_file="system_info.json"):
        self.output_file = output_file
        self.info = {"timestamp": datetime.now().isoformat()}

    def run_cmd(self, cmd):
        """Run shell command safely and return output."""
        try:
            return subprocess.check_output(
                cmd, shell=True, text=True, stderr=subprocess.DEVNULL
            ).strip()
        except subprocess.CalledProcessError:
            return "N/A"

    # === Basic Info ===
    def collect_os_info(self):
        self.info["os"] = {
            "name": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "distribution": self.run_cmd("cat /etc/os-release"),
            "architecture": platform.machine(),
            "hostname": platform.node(),
        }

    def collect_kernel_info(self):
        self.info["kernel"] = {
            "uname": self.run_cmd("uname -a"),
            "cmdline": self.run_cmd("cat /proc/cmdline"),
        }

    def collect_cpu_info(self):
        self.info["cpu"] = {
            "lscpu": self.run_cmd("lscpu"),
            "numa": self.run_cmd("numactl --hardware"),
            "cpuinfo": self.run_cmd("cat /proc/cpuinfo"),
        }

    def collect_memory_info(self):
        self.info["memory"] = {"meminfo": self.run_cmd("cat /proc/meminfo")}

    def collect_bios_info(self):
        self.info["bios"] = {"dmidecode": self.run_cmd("sudo dmidecode -t bios")}

    def collect_power_info(self):
        self.info["power"] = {
            "governor": self.run_cmd(
                "cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | uniq"
            ),
            "cpupower": self.run_cmd("cpupower frequency-info"),
        }

    def collect_pqos_info(self):
        self.info["pqos"] = self.run_cmd("pqos -s")

    def collect_interrupts(self):
        self.info["interrupts"] = self.run_cmd("cat /proc/interrupts")

    def collect_services(self):
        self.info["services"] = self.run_cmd(
            "systemctl list-units --type=service --state=running"
        )

    def collect_network_info(self):
        interfaces = self.run_cmd("ls /sys/class/net").split()
        self.info["network"] = {}
        for iface in interfaces:
            self.info["network"][iface] = {
                "driver": self.run_cmd(f"ethtool -i {iface}"),
                "offload": self.run_cmd(f"ethtool -k {iface}"),
            }

    def collect_clock_info(self):
        self.info["clock"] = {
            "clocksource": self.run_cmd(
                "cat /sys/devices/system/clocksource/clocksource0/current_clocksource"
            ),
            "ntp": self.run_cmd("timedatectl status"),
        }

    def collect_irq_affinity(self):
        """Collect IRQ to CPU affinity mappings."""
        irq_affinity = {}
        for path in glob("/proc/irq/[0-9]*/smp_affinity_list"):
            irq = path.split("/")[3]
            try:
                with open(path) as f:
                    irq_affinity[irq] = f.read().strip()
            except Exception:
                irq_affinity[irq] = "N/A"
        self.info["irq_affinity"] = irq_affinity

    def collect_cstate_pstate_info(self):
        """Collect CPU idle (C-state) and performance (P-state) info."""
        cstate_info = {}
        for cpu_dir in glob("/sys/devices/system/cpu/cpu[0-9]*"):
            cpu = os.path.basename(cpu_dir)
            idle_dir = os.path.join(cpu_dir, "cpuidle")
            if os.path.isdir(idle_dir):
                states = {}
                for state_dir in glob(os.path.join(idle_dir, "state*")):
                    try:
                        with open(os.path.join(state_dir, "name")) as f:
                            name = f.read().strip()
                        with open(os.path.join(state_dir, "latency")) as f:
                            latency = f.read().strip()
                        states[name] = {"latency_us": latency}
                    except Exception:
                        continue
                cstate_info[cpu] = states

        pstate_info = {}
        intel_pstate_dir = "/sys/devices/system/cpu/intel_pstate"
        if os.path.isdir(intel_pstate_dir):
            for file in os.listdir(intel_pstate_dir):
                try:
                    with open(os.path.join(intel_pstate_dir, file)) as f:
                        pstate_info[file] = f.read().strip()
                except Exception:
                    continue

        self.info["power_states"] = {"cstates": cstate_info, "pstates": pstate_info}

    def collect_isolated_cpus(self):
        """Detect isolated CPUs via sysfs or kernel cmdline."""
        isolated = "N/A"
        if os.path.exists("/sys/devices/system/cpu/isolated"):
            with open("/sys/devices/system/cpu/isolated") as f:
                isolated = f.read().strip()
        else:
            cmdline = self.run_cmd("cat /proc/cmdline")
            if "isolcpus=" in cmdline:
                isolated = cmdline.split("isolcpus=")[1].split()[0].split(",")
        self.info["isolated_cpus"] = isolated

    def dump_to_file(self, path=None, as_text=False):
        """Dump collected info into a JSON or text file."""
        output_path = path or self.output_file
        if as_text:
            # human-readable plain text
            with open(output_path, "w") as f:
                for key, value in self.info.items():
                    f.write(f"== {key.upper()} ==\n")
                    f.write(json.dumps(value, indent=4))
                    f.write("\n\n")
        else:
            # structured JSON
            with open(output_path, "w") as f:
                json.dump(self.info, f, indent=4)

        print(f"[+] System information dumped to {output_path}")

    def gather_all(self):
        """Collect all available system information."""
        self.collect_os_info()
        self.collect_kernel_info()
        self.collect_cpu_info()
        self.collect_memory_info()
        self.collect_bios_info()
        self.collect_power_info()
        self.collect_pqos_info()
        self.collect_interrupts()
        self.collect_services()
        self.collect_network_info()
        self.collect_clock_info()
        self.collect_irq_affinity()
        self.collect_cstate_pstate_info()
        self.collect_isolated_cpus()

        return self.info
