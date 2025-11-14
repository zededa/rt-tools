import argparse
import os
import subprocess
import sys
import io
import hydra
import csv

from omegaconf import DictConfig, OmegaConf
from tqdm import tqdm
from pathlib import Path
from typing import List, Optional
from subprocess import CompletedProcess, Popen

from src.test_output_parser import (
    build_caterpillar_parser,
    build_cyclictest_parser,
    MegabenchParser,
)
from src.metrics import (
    CPUmonitor,
    InterruptMonitor,
    MemInfoMonitor,
    SoftIrqMonitor,
    CpuStatMonitor,
)
from src.sysinfo_collector import SystemInfoCollector


class DockerTestRunner:
    """Manages Docker-based test execution with resource allocation."""

    EXCLUDED_DIRS = {"docs", "stressor"}

    def __init__(self, config: DictConfig):
        self.tests = self._discover_tests()
        self.config = config

    def _discover_tests(self) -> List[str]:
        """Discover available test directories."""
        tests = []
        for item in Path(".").iterdir():
            if item.is_dir() and item.name not in self.EXCLUDED_DIRS:
                tests.append(item.name)

        return sorted(tests)

    def build(self) -> int:
        """Build all Docker images for tests."""
        print("Running build command...")

        print("Building base image...")
        if (
            self._run_command(
                [
                    "docker",
                    "build",
                    "-f",
                    "Dockerfile.base",
                    "-t",
                    "eci-base:latest",
                    ".",
                ]
            )
            == None
        ):
            return 1

        print("Building stressor...")
        if (
            self._run_command(
                [
                    "docker",
                    "build",
                    "-f",
                    "stressor/Dockerfile",
                    "-t",
                    "stressor:latest",
                    "stressor/.",
                ]
            )
            == None
        ):
            return 1

        for test in self.tests:
            print(f"Building test {test}...")
            if not self._build_test(test):
                return 1

        return 0

    def _build_test(self, test: str) -> bool:
        """Build a specific test image."""
        if test == "codesys-opcua-pubsub":
            print("Building Codesys-opcua-client")
            cmd = [
                "docker",
                "build",
                "-f",
                f"{test}/opcua-client/Dockerfile",
                "-t",
                "codesys-opcua-client:latest",
                "--build-arg",
                "CDS_VERSION=4.11.0.0",
                "--build-arg",
                "APP_DEB=codesys-opcua-benchmark",
                f"{test}/opcua-client/.",
            ]
            if self._run_command(cmd) == None:
                return False

            print("Building Codesys-opcua-server")
            cmd = [
                "docker",
                "build",
                "-f",
                f"{test}/opcua-server/Dockerfile",
                "-t",
                "codesys-opcua-server:latest",
                # XXX: wrong arg??
                "--build-arg",
                "CONFIG=opcsvr-pubsub.yaml",
                "--build-arg",
                "APP-opcsvr",
                f"{test}/opcua-server/.",
            ]

            return self._run_command(cmd) != None

        elif test == "codesys-jitter-benchmark":
            cmd = [
                "docker",
                "build",
                "-f",
                f"{test}/Dockerfile",
                "-t",
                f"{test}:latest",
                "--build-arg",
                "CDS_VERSION=4.11.0.0",
                "--build-arg",
                "APP_DEB=codesys-eci-benchmark",
                f"{test}/.",
            ]
            return self._run_command(cmd) != None

        else:
            cmd = [
                "docker",
                "build",
                "-f",
                f"{test}/Dockerfile",
                "-t",
                f"{test}:latest",
                f"./{test}",
            ]
            return self._run_command(cmd) != None

    def run_test(
        self, test: str, l3_cache_mask: str, t_core: str, stressor: bool = False
    ) -> int:
        """Run a specific test with given parameters."""
        if test not in self.tests:
            print(f"Error: '{test}' is not a valid test")
            return 1

        if stressor:
            self._start_stressor()

        print(f"Running {test} with:")
        print(f"  L3 Cache Mask: {l3_cache_mask}")
        print(f"  Target Core(s): {t_core}")
        print(f"  Stressor: {stressor}")

        docker_cmd = self._build_base_docker_command(test, t_core)

        if test == "caterpillar":
            return self._run_caterpillar(
                docker_cmd, l3_cache_mask, t_core, self.config.benchmark_output_path
            )
        elif test == "cyclictest":
            return self._run_cyclictest(
                docker_cmd, l3_cache_mask, t_core, self.config.benchmark_output_path
            )
        elif test == "codesys-jitter-benchmark":
            return self._run_codesys_jitter(docker_cmd, l3_cache_mask, t_core)
        elif test == "codesys-opcua-pubsub":
            return self._run_codesys_opcua(docker_cmd, l3_cache_mask, t_core)
        elif test == "iperf3":
            return self._run_iperf3(docker_cmd, l3_cache_mask, t_core)
        elif test == "mega-benchmark":
            return self._run_megabench(docker_cmd, t_core)
        else:
            print(f"Error: Test '{test}' is not implemented")
            return 1

    def _build_base_docker_command(self, test: str, t_core: str) -> List[str]:
        """Build the base Docker command with common options."""
        return [
            "sudo",
            "docker",
            "run",
            "--rm",
            "--privileged",
            f"--cpuset-cpus={t_core}",
            "-v",
            "/sys/fs/resctrl:/sys/fs/resctrl",
            "-v",
            "/dev/cpu_dma_latency:/dev/cpu_dma_latency",
            "--cap-add=SYS_NICE",
            "--cap-add=IPC_LOCK",
            f"--name",
            test,
        ]

    def _run_caterpillar(
        self, base_cmd: List[str], l3_cache_mask: str, t_core: str, path: str
    ) -> int:
        """Run caterpillar test."""
        cmd = base_cmd + [
            "caterpillar:latest",
            "/bin/bash",
            "-c",
            f'stdbuf -oL -eL /usr/sbin/rdtset -t "l3={l3_cache_mask};cpu={t_core}" '
            f"-c {t_core} -k /opt/benchmarking/caterpillar/caterpillar -c {t_core} -s {self.config.caterpillar.n_cycles}",
        ]

        print(" ".join(cmd))
        process = self._run_interactive_command(cmd)
        assert process.stdout is not None

        pbar = tqdm(total=self.config.caterpillar.n_cycles)
        parser = build_caterpillar_parser()
        with open(path, "w") as f:
            prelude = parser.prelude()
            if prelude is not None:
                f.write(prelude)

            for line in process.stdout:
                parsed = parser.parse(line)
                if parsed is not None:
                    pbar.update(1)
                    f.write(parsed)
        pbar.close()

        return process.wait()

    def _run_cyclictest(
        self, base_cmd: List[str], l3_cache_mask: str, t_core: str, path: str
    ) -> int:
        """Run cyclictest."""
        cmd = base_cmd + [
            "cyclictest:latest",
            "/bin/bash",
            "-c",
            f'stdbuf -oL -eL /usr/sbin/rdtset -t "l3={l3_cache_mask};cpu={t_core}" -c {t_core} '
            f"-k /usr/bin/cyclictest --threads -t 1 -p 99 -l 100000 -d 1 -D 0 -i 100000 -a {t_core}",
        ]
        print(" ".join(cmd))

        process = self._run_interactive_command(cmd)
        assert process.stdout is not None

        pbar = tqdm(total=400000)
        last_c_value = 0
        parser = build_cyclictest_parser()
        with open(path, "w") as f:
            prelude = parser.prelude()
            if prelude is not None:
                f.write(prelude)

            for line in process.stdout:
                print(line)
                parsed = parser.parse(line)

                if parsed is None:
                    continue

                f.write(parsed)

                try:
                    # Use csv reader to safely split by commas
                    reader = csv.DictReader(
                        io.StringIO(parsed),
                        fieldnames=parser.headers,
                    )
                    row = next(reader)
                    c_val = int(row["C"])

                    # --- Update tqdm only if C increases ---
                    if c_val > last_c_value:
                        pbar.update(c_val - last_c_value)
                        last_c_value = c_val

                except Exception as e:
                    # Optional: log or ignore malformed lines
                    print(f"Warning: could not parse C value: {e}")

        pbar.close()

        return process.wait()

    def _run_codesys_jitter(
        self, base_cmd: List[str], l3_cache_mask: str, t_core: str
    ) -> int:
        """Run Codesys jitter benchmark."""
        cmd = base_cmd + [
            "-p",
            "8080:8080",
            "-e",
            "DEBUGOUTPUT=1",
            "-e",
            "DEBUGLOGFILE=/tmp/codesyscontrol_debug.log",
            "-e",
            f"L3_CACHE_MASK={l3_cache_mask}",
            "-e",
            f"T_CORE={t_core}",
            "-d",
            "codesys-jitter-benchmark:latest",
            "/bin/bash",
            "-c",
            "/docker-entrypoint.sh",
        ]
        print(" ".join(cmd))
        result = self._run_command(cmd)

        # Get server IP
        try:
            server_ip = (
                subprocess.check_output(["hostname", "-I"], text=True)
                .strip()
                .split()[0]
            )
            print(f"Please go to {server_ip}:8080")
        except (subprocess.CalledProcessError, IndexError):
            print("Could not determine server IP")

        if result == None:
            return 1

        return result.returncode

    def _run_codesys_opcua(
        self, base_cmd: List[str], l3_cache_mask: str, t_core: str
    ) -> int:
        """Run Codesys OPC-UA PubSub test."""
        print("Starting codesys-opcua-pubsub")

        # Start OPC-UA server
        server_cmd = [
            "docker",
            "run",
            "-d",
            "--rm",
            "--privileged",
            "--name",
            "codesys-opcua-server",
            "-p",
            "4840:4841",
            "codesys-opcua-server:latest",
        ]
        if self._run_command(server_cmd) != 0:
            return 1

        # Wait for server to start
        subprocess.run(["sleep", "10"], check=False)

        # Start client
        cmd = base_cmd + [
            "-e",
            f"L3_CACHE_MASK={l3_cache_mask}",
            "-e",
            f"T_CORE={t_core}",
            "-p",
            "0.0.0.0:8081:8080/tcp",
            "-p",
            "0.0.0.0:8081:8080/udp",
            "codesys-opcua-client:latest",
            "/bin/bash",
            "-c",
            "/docker-entrypoint.sh",
        ]
        print(" ".join(cmd))
        result = self._run_command(cmd)

        # Stop server
        print("Stopping Codesys OPC-UA Server")
        self._run_command(["docker", "stop", "codesys-opcua-server"])

        if result == None:
            return 1

        return result.returncode

    def _run_iperf3(self, base_cmd: List[str], l3_cache_mask: str, t_core: str) -> int:
        """Run iperf3 test."""
        print("Starting iperf3")

        # Start iperf3 server
        server_cmd = [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name=iperf3-server",
            "-p",
            "5201:5201",
            "iperf3:latest",
            "-s",
        ]
        if self._run_command(server_cmd) != 0:
            return 1

        # Wait for server to start
        subprocess.run(["sleep", "5"], check=False)

        # Get server IP
        try:
            server_ip = subprocess.check_output(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{ .NetworkSettings.IPAddress }}",
                    "iperf3-server",
                ],
                text=True,
            ).strip()
        except subprocess.CalledProcessError:
            print("Error: Could not get iperf3 server IP")
            self._run_command(["docker", "stop", "iperf3-server"])
            return 1

        # Start client
        cmd = base_cmd + [
            "-e",
            f"L3_CACHE_MASK={l3_cache_mask}",
            "-e",
            f"T_CORE={t_core}",
            "iperf3:latest",
            "-c",
            server_ip,
        ]
        print(" ".join(cmd))
        result = self._run_command(cmd)

        # Stop server
        print("Stopping iperf3 Server")
        self._run_command(["docker", "stop", "iperf3-server"])

        if result == None:
            return 1

        return result.returncode

    def _run_megabench(self, base_cmd: List[str], t_core: str) -> int:
        self._run_caterpillar(
            base_cmd,
            self.config.megabench.no_cat_mask,
            self.config.megabench.no_cat_cores,
            self.config.megabench.caterpillar_no_cat,
        )

        self._run_caterpillar(
            base_cmd,
            self.config.megabench.cat_mask,
            self.config.megabench.cat_cores,
            self.config.megabench.caterpillar_cat,
        )

        self._run_cyclictest(
            base_cmd,
            self.config.megabench.no_cat_mask,
            self.config.megabench.no_cat_cores,
            self.config.megabench.cyclictest_no_cat,
        )

        self._run_cyclictest(
            base_cmd,
            self.config.megabench.cat_mask,
            self.config.megabench.cat_cores,
            self.config.megabench.cyclictest_cat,
        )

        return 0

    def _start_stressor(self) -> None:
        """Start the stressor container if not already running."""
        try:
            result = subprocess.check_output(
                ["docker", "ps", "-aq", "--filter", "name=stressor"], text=True
            ).strip()

            if result:
                print("Stressor is already running...skipping")
            else:
                print("Starting stressor container")
                self._run_command(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--rm",
                        "--name",
                        "stressor",
                        "stressor:latest",
                    ]
                )
        except subprocess.CalledProcessError:
            print("Warning: Could not check stressor status")

    @staticmethod
    def _run_command(cmd: List[str]) -> CompletedProcess | None:
        """Run a command and return its exit code."""
        try:
            result = subprocess.run(cmd, capture_output=True, check=False)
            return result
        except Exception as e:
            print(f"Error running command: {e}")
            return None

    @staticmethod
    def _run_interactive_command(cmd: List[str]) -> Popen[str]:
        process = Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        return process


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig):
    collector = SystemInfoCollector()
    collector.gather_all()
    collector.dump_to_file(cfg.sysinfo_collector_file)

    runner = DockerTestRunner(cfg)

    if cfg.run.command == "build":
        return runner.build()

    # Handle test commands
    if cfg.run.command not in runner.tests:
        print(f"Error: '{cfg.run.command}' is not a valid command")
        return 1

    cpu_monitor = CPUmonitor(cfg.cpu_monitor.path, cfg.cpu_monitor.interval)
    interrupt_monitor = InterruptMonitor(cfg.irq_monitor.path, cfg.irq_monitor.interval)
    meminfo_monitor = MemInfoMonitor(
        cfg.meminfo_monitor.path, cfg.meminfo_monitor.interval
    )
    softirq_monitor = SoftIrqMonitor(
        cfg.softirq_monitor.path, cfg.softirq_monitor.interval
    )
    cpustat_monitor = CpuStatMonitor(
        cfg.cpustat_monitor.path, cfg.softirq_monitor.interval
    )

    cpu_monitor.start()
    interrupt_monitor.start()
    meminfo_monitor.start()
    softirq_monitor.start()
    cpustat_monitor.start()

    return runner.run_test(
        cfg.run.command, cfg.run.llc_cache_mask, cfg.run.t_core, cfg.run.stressor
    )


if __name__ == "__main__":
    main()
