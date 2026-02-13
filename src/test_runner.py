import csv
import io
import subprocess
import psutil
import time
import shlex

from typing import List, Optional
from omegaconf import DictConfig, OmegaConf
from pathlib import Path
from tqdm import tqdm
from subprocess import CompletedProcess, Popen
from src.pqos_manager import PQOSManager

from src.test_output_parser import (
    build_caterpillar_parser,
    build_cyclictest_parser,
    MegabenchParser,
)


def get_pid_psutil(process_name):
    found_pids = []
    # Iterate over all running processes
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            # Check if process name contains the query string
            if process_name in proc.info["name"]:
                found_pids.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return found_pids


class DockerTestRunner:
    """Manages Docker-based test execution with resource allocation."""

    def __init__(self, config: DictConfig):
        self.tests = [
            "cyclictest",
            "caterpillar",
            "iperf3",
            "codesys-jitter-benchmark",
            "codesys-opcua-pubsub",
        ]
        self.config = config

    def build(self) -> int:
        """Build all Docker images for tests."""
        print("Running build command...")

        print("Building base image...")
        if (
            self._run_command(
                [
                    "docker",
                    "build",
                    "--network=host",
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
                    "--network=host",
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
            self._build_test(test)

        return 0

    def _build_test(self, test: str) -> bool:
        """Build a specific test image."""
        if test == "codesys-opcua-pubsub":
            print("Building Codesys-opcua-client")
            cmd = [
                "docker",
                "build",
                "--network=host",
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
            if self._run_command(cmd) != 0:
                return False

            print("Building Codesys-opcua-server")
            cmd = [
                "docker",
                "build",
                "--network=host",
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

            return self._run_command(cmd) != 0

        elif test == "codesys-jitter-benchmark":
            cmd = [
                "docker",
                "build",
                "--network=host",
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
            return self._run_command(cmd) != 0

        else:
            cmd = [
                "docker",
                "build",
                "--network=host",
                "-f",
                f"{test}/Dockerfile",
                "-t",
                f"{test}:latest",
                f"./{test}",
            ]
            return self._run_command(cmd) != 0

    def run_test(self, test: str, t_core: str, stressor: bool = False) -> int:
        """Run a specific test with given parameters."""
        if test not in self.tests:
            print(f"Error: '{test}' is not a valid test")
            return 1

        if stressor:
            self._start_stressor()

        print(f"Running {test} with:")
        print(f"  Target Core(s): {t_core}")
        print(f"  Stressor: {stressor}")

        docker_cmd = self._build_base_docker_command(test, t_core)

        if test == "caterpillar":
            return self._run_caterpillar(
                docker_cmd, t_core, self.config.benchmark_output_path
            )
        elif test == "cyclictest":
            return self._run_cyclictest(
                docker_cmd,
                t_core,
                self.config.benchmark_output_path,
                self.config.cyclictest.loops,
            )
        elif test == "codesys-jitter-benchmark":
            return self._run_codesys_jitter(docker_cmd, t_core)
        elif test == "codesys-opcua-pubsub":
            return self._run_codesys_opcua(docker_cmd, t_core)
        elif test == "iperf3":
            return self._run_iperf3(docker_cmd, t_core)
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
            f"--cpuset-mems={self.config.run.numa_node}",
            "-v",
            "/sys/fs/cgroup:/sys/fs/cgroup",
            "-v",
            "/dev/cpu_dma_latency:/dev/cpu_dma_latency",
            "--cap-add=SYS_NICE",
            "--cap-add=IPC_LOCK",
            "--cap-add=SYS_ADMIN",
            "--ulimit",
            "rtprio=95:95",
            f"--name",
            test,
        ]

    def _run_caterpillar(self, base_cmd: List[str], t_core: str, path: str) -> int:
        """Run caterpillar test."""
        caterpillar_cmd = (
            "chrt -f 95 "
            f"/opt/benchmarking/caterpillar/caterpillar "
            f"-c {t_core} -s {self.config.caterpillar.n_cycles}"
        )
        if self.config.run.docker:
            rdtset_cmd = f"stdbuf -oL -eL " f"{caterpillar_cmd}"
            cmd = base_cmd + [
                "caterpillar:latest",
                "/bin/bash",
                "-c",
                rdtset_cmd,
            ]
        else:
            cmd = shlex.split(caterpillar_cmd)

        print(" ".join(cmd))
        try:
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

        except KeyboardInterrupt:
            process.terminate()
        finally:
            try:
                subprocess.run("docker stop $(docker ps -q)", shell=True, check=False)
            except Exception as e:
                print(f"Error stopping containers: {e}")

        return process.wait()

    def _run_cyclictest(
        self, base_cmd: List[str], t_core: str, path: str, cycles: str
    ) -> int:
        """Run cyclictest."""
        cyclictest_cmd = (
            # "chrt -r 95 "
            f"/usr/bin/cyclictest --threads -t 1 -p 95 "
            f"-l {cycles} -d 1 -D 0 -i {self.config.caterpillar.n_cycles} -a {t_core}"
        )
        if self.config.run.docker:
            rdtset_cmd = f"stdbuf -oL -eL " f"{cyclictest_cmd}"
            cmd = base_cmd + [
                "cyclictest:latest",
                "/bin/bash",
                "-c",
                rdtset_cmd,
            ]
        else:
            cmd = shlex.split(cyclictest_cmd)

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

    def _run_codesys_jitter(self, base_cmd: List[str], t_core: str) -> int:
        """Run Codesys jitter benchmark."""
        cmd = base_cmd + [
            "-p",
            "8080:8080",
            "-e",
            "DEBUGOUTPUT=1",
            "-e",
            "DEBUGLOGFILE=/tmp/codesyscontrol_debug.log",
            "-e",
            # f"L3_CACHE_MASK={l3_cache_mask}",
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

        return result

    def _run_codesys_opcua(self, base_cmd: List[str], t_core: str) -> int:
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
            # f"L3_CACHE_MASK={l3_cache_mask}",
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

        return result

    def _run_iperf3(self, base_cmd: List[str], t_core: str) -> int:
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
            # f"L3_CACHE_MASK={l3_cache_mask}",
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

        return result

    def _run_megabench(self, base_cmd: List[str], t_core: str) -> int:
        self._run_caterpillar(
            base_cmd,
            self.config.megabench.no_cat_cores,
            self.config.megabench.caterpillar_no_cat,
        )

        self._run_caterpillar(
            base_cmd,
            self.config.megabench.cat_cores,
            self.config.megabench.caterpillar_cat,
        )

        self._run_cyclictest(
            base_cmd,
            self.config.megabench.no_cat_cores,
            self.config.megabench.cyclictest_no_cat,
            self.config.cyclictest.loops,
        )

        self._run_cyclictest(
            base_cmd,
            self.config.megabench.cat_cores,
            self.config.megabench.cyclictest_cat,
            self.config.cyclictest.loops,
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
    def _run_command(cmd: List[str]) -> int:
        """Run a command and return its integer exit code (0 = success)."""
        print(f"DEBUG: Executing {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=False)
            return result.returncode
        except Exception as e:
            print(f"CRITICAL ERROR running command: {e}")
            return 1

    def _run_interactive_command(self, cmd: List[str]) -> Popen[str]:
        process = Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        if self.config.run.cat_clos_pinning.enable and self.config.pqos.enable:
            MAX_RETRIES = 5
            SLEEP_TIME = 2  # Seconds to wait between tries

            # 3. The Retry Logic
            pids = []

            for attempt in range(1, MAX_RETRIES + 1):
                print(f"Attempt {attempt}/{MAX_RETRIES}...")

                pids = get_pid_psutil(self.config.run.command)

                # Check if result is NOT empty
                if len(pids) > 0:
                    break

                print("Result was empty. Sleeping...")
                time.sleep(SLEEP_TIME)
            else:
                # This block executes only if the loop finishes without 'break'
                print("Failed: Max retries reached with empty results.")

            if len(pids) > 0:
                print(
                    f"Assigning {self.config.run.command} with PID(s) {pids} to CLOS {self.config.run.cat_clos_pinning.clos}"
                )
                manager = PQOSManager()
                manager.assign_pids_to_class(
                    self.config.run.cat_clos_pinning.clos, pids
                )

        return process
