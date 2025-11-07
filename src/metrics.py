import threading
import time
import csv
import psutil
from abc import ABC, abstractmethod


class Metric(ABC):
    """Abstract base class for all metrics."""

    def __init__(self, filename: str, interval: float = 1.0):
        self.filename = filename
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._file = None
        self._writer = None

    @abstractmethod
    def _monitor(self):
        """Metric collection logic running in a background thread."""
        pass

    def start(self):
        """Start monitoring in a separate thread."""
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self):
        """Stop monitoring and close the file."""
        self._stop_event.set()
        self._thread.join()
        if self._file:
            self._file.close()


class CPUmonitor(Metric):
    """Monitors per-core CPU temperatures and writes them to a CSV file."""

    def __init__(self, filename: str, interval: float = 1.0):
        super().__init__(filename, interval)

        # Detect available sensors
        temps = psutil.sensors_temperatures()
        if not temps:
            raise RuntimeError("No temperature sensors found on this system.")
        self.sensor_label = self._detect_cpu_sensor(temps)
        self.core_labels = [
            t.label or f"core_{i}" for i, t in enumerate(temps[self.sensor_label])
        ]

    def _detect_cpu_sensor(self, temps):
        for key in ["coretemp", "cpu-thermal", "k10temp", "acpitz"]:
            if key in temps:
                return key
        return list(temps.keys())[0]

    def _monitor(self):
        """Write per-core CPU temps periodically."""
        with open(self.filename, "a", newline="") as self._file:
            self._writer = csv.writer(self._file)
            if self._file.tell() == 0:
                self._writer.writerow(["timestamp"] + self.core_labels)
                self._file.flush()

            while not self._stop_event.is_set():
                temps = psutil.sensors_temperatures()
                sensor_data = temps.get(self.sensor_label, [])
                readings = [
                    t.current if hasattr(t, "current") else float("nan")
                    for t in sensor_data
                ]
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                self._writer.writerow([timestamp] + readings)
                self._file.flush()
                time.sleep(self.interval)


class InterruptMonitor(Metric):
    """Monitors interrupts from /proc/interrupts with per-CPU detail."""

    def __init__(self, filename: str, interval: float = 2.0):
        super().__init__(filename, interval)
        self.cpu_headers = self._parse_cpu_headers()

    def _parse_cpu_headers(self):
        """Extract CPU column headers from /proc/interrupts."""
        with open("/proc/interrupts", "r") as f:
            first_line = f.readline().strip()
        return first_line.split()

    def _read_interrupts(self):
        """Parse /proc/interrupts into structured rows."""
        with open("/proc/interrupts", "r") as f:
            lines = f.readlines()

        cpu_count = len(self.cpu_headers)
        data_rows = []

        for line in lines[1:]:
            parts = line.split()
            if not parts:
                continue
            irq_id = parts[0].rstrip(":")
            counts = parts[1 : 1 + cpu_count]
            tail = parts[1 + cpu_count :]
            desc = " ".join(tail) if tail else ""
            data_rows.append((irq_id, desc, counts))
        return data_rows

    def _monitor(self):
        """Periodically dump per-CPU interrupt counters."""
        with open(self.filename, "a", newline="") as self._file:
            self._writer = csv.writer(self._file)
            if self._file.tell() == 0:
                header = ["timestamp", "irq", "description"] + self.cpu_headers
                self._writer.writerow(header)
                self._file.flush()

            while not self._stop_event.is_set():
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                interrupt_data = self._read_interrupts()

                for irq_id, desc, counts in interrupt_data:
                    row = [timestamp, irq_id, desc] + counts
                    self._writer.writerow(row)

                self._file.flush()
                time.sleep(self.interval)


class MemInfoMonitor(Metric):
    """Monitors /proc/meminfo and writes key memory metrics to a CSV file."""

    def __init__(self, filename: str, interval: float = 2.0):
        super().__init__(filename, interval)
        # Collect all available memory fields from /proc/meminfo
        self.fields = self._read_meminfo().keys()

    def _read_meminfo(self):
        """Parse /proc/meminfo into a dict {field: value_in_kB}."""
        data = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                key, value, *_ = line.split()
                data[key.rstrip(":")] = int(value)
        return data

    def _monitor(self):
        """Periodically record memory information."""
        with open(self.filename, "a", newline="") as self._file:
            self._writer = csv.writer(self._file)
            if self._file.tell() == 0:
                header = ["timestamp"] + list(self.fields)
                self._writer.writerow(header)
                self._file.flush()

            while not self._stop_event.is_set():
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                meminfo = self._read_meminfo()
                row = [timestamp] + [meminfo.get(f, "") for f in self.fields]
                self._writer.writerow(row)
                self._file.flush()
                time.sleep(self.interval)


class SoftIrqMonitor(Metric):
    """Monitors /proc/softirqs and writes counts per CPU to a CSV file."""

    def __init__(self, filename: str, interval: float = 1.0):
        super().__init__(filename, interval)
        self.fields = self._read_softirqs().keys()

    def _read_softirqs(self):
        """Parse /proc/softirqs into {softirq_type: [counts per CPU]}."""
        data = {}
        with open("/proc/softirqs", "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        header = lines[0].split()
        ncpu = len(header) - 1
        for line in lines[1:]:
            parts = line.split()
            name = parts[0].rstrip(":")
            values = [int(v) for v in parts[1:]]
            if len(values) < ncpu:
                values += [0] * (ncpu - len(values))
            data[name] = values
        return data

    def _monitor(self):
        with open(self.filename, "a", newline="") as self._file:
            self._writer = csv.writer(self._file)
            if self._file.tell() == 0:
                # header: timestamp + all softirq_name@CPU#
                ncpu = len(next(iter(self._read_softirqs().values())))
                headers = ["timestamp"]
                for softirq in self.fields:
                    for i in range(ncpu):
                        headers.append(f"{softirq}_CPU{i}")
                self._writer.writerow(headers)
                self._file.flush()

            while not self._stop_event.is_set():
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                data = self._read_softirqs()
                ncpu = len(next(iter(data.values())))
                row = [timestamp]
                for softirq in self.fields:
                    row.extend(data[softirq][:ncpu])
                self._writer.writerow(row)
                self._file.flush()
                time.sleep(self.interval)


class CpuStatMonitor(Metric):
    """Monitors /proc/stat and records per-CPU and global statistics."""

    def __init__(self, filename: str, interval: float = 1.0):
        super().__init__(filename, interval)
        self.cpu_fields = [
            "user",
            "nice",
            "system",
            "idle",
            "iowait",
            "irq",
            "softirq",
            "steal",
            "guest",
            "guest_nice",
        ]

    def _read_cpustat(self):
        """Parse /proc/stat into dict with CPU and global counters."""
        stats = {}
        with open("/proc/stat", "r") as f:
            for line in f:
                parts = line.split()
                if parts[0].startswith("cpu"):
                    name = parts[0]
                    values = list(map(int, parts[1 : len(self.cpu_fields) + 1]))
                    stats[name] = values
                elif parts[0] in (
                    "ctxt",
                    "processes",
                    "procs_running",
                    "procs_blocked",
                ):
                    stats[parts[0]] = int(parts[1])
        return stats

    def _monitor(self):
        with open(self.filename, "a", newline="") as self._file:
            self._writer = csv.writer(self._file)
            if self._file.tell() == 0:
                # header: timestamp + per-CPU metrics + global counters
                header = ["timestamp"]
                cpu_sample = self._read_cpustat()
                for cpu, values in cpu_sample.items():
                    if cpu.startswith("cpu"):
                        for field in self.cpu_fields[: len(values)]:
                            header.append(f"{cpu}_{field}")
                for key in ["ctxt", "processes", "procs_running", "procs_blocked"]:
                    header.append(key)
                self._writer.writerow(header)
                self._file.flush()

            while not self._stop_event.is_set():
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                stats = self._read_cpustat()
                row = [timestamp]
                for cpu, values in stats.items():
                    if cpu.startswith("cpu"):
                        row.extend(values)
                for key in ["ctxt", "processes", "procs_running", "procs_blocked"]:
                    row.append(stats.get(key, ""))
                self._writer.writerow(row)
                self._file.flush()
                time.sleep(self.interval)
