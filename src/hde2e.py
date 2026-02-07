import getpass
import os
import json
import subprocess
import tarfile
import tempfile
from typing import List, Optional, Dict

from omegaconf import DictConfig
import paramiko

# Docker image defaults
DEFAULT_IMAGE_NAME = "codesyscontrol_virtuallinux"
DEFAULT_IMAGE_TAG = "4.18.0.0"
DEFAULT_IMAGE = f"{DEFAULT_IMAGE_NAME}:{DEFAULT_IMAGE_TAG}"
DEFAULT_NETWORK = "codesys_net1"
DEFAULT_SUBNET = "192.168.10.0/24"
DEFAULT_GATEWAY = "192.168.10.1"

# Capabilities required by the CODESYS runtime
DOCKER_CAPS = [
    "IPC_LOCK","NET_BROADCAST", "NET_RAW", "SETFCAP", "SETPCAP", "SYS_ADMIN",
    "SYS_MODULE", "SYS_NICE", "SYS_PTRACE", "SYS_RAWIO",
    "SYS_RESOURCE", "SYS_TIME",
]


class DockerHDE2E:
    """Manages building, transferring, and launching CODESYS HDE2E
    PLC containers — locally or on remote hosts via SSH.
    """

    def __init__(self, config: DictConfig):
        self.config = config
        self.hde2e_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'codesys-hde2e')
        )
        self.plc_dir = os.path.join(self.hde2e_dir, 'plc')
        self.configs_dir = os.path.join(self.hde2e_dir, 'configs')
        self._sudo_password: Optional[str] = None

    def _resolve_sudo_password(self) -> str:
        """Return the sudo password, prompting the user once if needed.

        Checks (in order):
        1. Cached value from a previous call.
        2. ``demo.control_system.ssh_password`` in the config.
        3. Interactive ``getpass`` prompt (cached for the session).
        """
        if self._sudo_password is not None:
            return self._sudo_password

        pw = self.config.demo.control_system.get("ssh_password")
        if not pw:
            pw = self.config.demo.io_system.get("ssh_password")
        if not pw:
            pw = getpass.getpass("[sudo] password for local commands: ")

        self._sudo_password = pw
        return pw

    def _sudo_cmd(self, cmd: str) -> str:
        """Wrap *cmd* so it runs under ``sudo -S`` with the password
        piped in.  This avoids interactive prompts that block automation.
        """
        pw = self._resolve_sudo_password()
        # Use printf to avoid issues with special chars in the password.
        return f"printf '%s\\n' '{pw}' | sudo -S {cmd}"
    def _realtime_core_control(self, instance_num: str) -> Optional[str]:
        """Return a CPU core list string for the real-time Control PLC instance."""
        # Example mapping: Control_PLC_01 → cores 0-3, Control_PLC_02 → cores 4-7
        t_cpus = self.config.demo.control_system.get("t_cpus")
        t_cpus = t_cpus.split(",")
        if len(t_cpus) < 4:
            print("[WARN] Not enough t_cpus specified for control_system. Expected at least 4.")
            return None
        if instance_num == "01":
            return f"{t_cpus[int(instance_num)-1]},{t_cpus[int(instance_num)]}" # cores 3,5
        elif instance_num == "02":
            return f"{t_cpus[int(instance_num)]},{t_cpus[len(t_cpus)-1]}" # cores 7,9
    def _realtime_core_io(self, instance_num: str) -> Optional[str]:
        """Return a CPU core list string for the real-time IO PLC instance."""
        # Example mapping: IO_PLC_01 → cores 8-11, IO_PLC_02 → cores 12-15
        t_cpus = self.config.demo.io_system.get("t_cpus")
        t_cpus = t_cpus.split(",")
        if len(t_cpus) < 2:
            print("[WARN] Not enough t_cpus specified for io_system. Expected at least 2.")
            return None
        return str(t_cpus[int(instance_num) - 1])
    #  Low-level helpers
    @staticmethod
    def _run_command(cmd: List[str], capture: bool = False) -> subprocess.CompletedProcess:
        """Run a local command. Returns the CompletedProcess object."""
        print(f"[CMD] {' '.join(cmd)}")
        return subprocess.run(cmd, check=False,
                              capture_output=capture, text=capture)

    @staticmethod
    def _run_ssh_command(ssh: paramiko.SSHClient, command: str,
                         timeout: int = 120) -> int:
        """Run a command on a remote host via SSH. Returns exit code."""
        print(f"[SSH] {command}")
        try:
            _stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if out:
                print(f"  stdout: {out}")
            if err:
                print(f"  stderr: {err}")
            return exit_status
        except Exception as exc:
            print(f"[ERROR] SSH command failed: {exc}")
            return 1

    def _ssh_connect(self, host: str, user: str,
                     password: Optional[str] = None,
                     port: int = 22) -> paramiko.SSHClient:
        """Open an SSH connection and return the client."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"[SSH] Connecting to {user}@{host}:{port} …")
        ssh.connect(hostname=host, username=user, password=password, port=port)
        return ssh

    #  Docker image build / save / transfer / load

    def build(self, image: str = DEFAULT_IMAGE) -> int:
        """Build the CODESYS Docker image locally."""
        print("[INFO] Building Docker image …")
        dockerfile = os.path.join(
            self.hde2e_dir,
            f"Dockerfile_codesyscontrol_virtuallinux_{DEFAULT_IMAGE_TAG}"
        )
        result = self._run_command([
            'docker', 'build',
            '-t', image,
            '-f', dockerfile,
            self.hde2e_dir,
        ])
        if result.returncode != 0:
            print("[ERROR] Docker build failed.")
            return 1
        print("[INFO] Docker image built successfully.")
        return 0

    def save_image(self, image: str = DEFAULT_IMAGE,
                   output_path: Optional[str] = None) -> str:
        """Save built image to a tarball, which can be transferred and loaded on a remote host."""
        if output_path is None:
            output_path = os.path.join(self.hde2e_dir, 'hde2e_image.tar')
        print(f"[INFO] Saving image {image} → {output_path} …")
        result = self._run_command(
            ['docker', 'save', '-o', output_path, image]
        )
        if result.returncode != 0:
            raise RuntimeError(f"docker save failed (rc={result.returncode})")
        return output_path

    @staticmethod
    def _sftp_put(ssh: paramiko.SSHClient, local: str, remote: str) -> None:
        """Transfer a file to the remote host via SFTP."""
        print(f"[SCP] {local}  →  {remote}")
        sftp = ssh.open_sftp()
        sftp.put(local, remote)
        sftp.close()

    def transfer_and_load_image(self, ssh: paramiko.SSHClient,
                                local_tar: str,
                                remote_tar: str = "/tmp/hde2e_image.tar") -> int:
        """SCP the image tarball to a remote host and ``docker load`` it."""
        self._sftp_put(ssh, local_tar, remote_tar)
        rc = self._run_ssh_command(ssh, f"docker load -i {remote_tar}")
        if rc != 0:
            print("[ERROR] docker load failed on remote host.")
        else:
            self._run_ssh_command(ssh, f"rm -f {remote_tar}")
        return rc

    #  Docker network (local or remote)
    @staticmethod
    def _docker_network_ensure(ssh: Optional[paramiko.SSHClient],
                               network: str, nic: str,
                               subnet: str = DEFAULT_SUBNET,
                               gateway: str = DEFAULT_GATEWAY) -> int:
        """Ensure a macvlan Docker network exists (locally or remote)."""

        def _run(cmd: str) -> int:
            if ssh:
                return DockerHDE2E._run_ssh_command(ssh, cmd)
            return subprocess.run(cmd, shell=True, check=False,
                                  capture_output=True, text=True).returncode

        # Check if already exists  (anchor the name so "net1" doesn't match "net10")
        check_cmd = (
            f'docker network ls --filter name=^{network}$ '
            f'--format "{{{{.Name}}}}"'
        )
        if ssh:
            _stdin, stdout, _stderr = ssh.exec_command(check_cmd)
            existing = stdout.read().decode().strip()
        else:
            res = subprocess.run(check_cmd, shell=True,
                                 capture_output=True, text=True)
            existing = res.stdout.strip()

        if existing == network:
            print(f"[INFO] Network '{network}' already exists.")
            return 0

        create_cmd = (
            f"docker network create -d macvlan "
            f"--subnet={subnet} --gateway={gateway} "
            f"-o parent={nic} {network}"
        )
        rc = _run(create_cmd)
        if rc != 0:
            print(f"[ERROR] Failed to create network '{network}'.")
        else:
            print(f"[INFO] Network '{network}' created.")
        return rc

    def _macvlan_shim_ensure(
        self,
        ssh: Optional[paramiko.SSHClient],
        nic: str,
        shim_ip: str,
        subnet: str = DEFAULT_SUBNET,
        shim_name: str = "macvlan-shim",
    ) -> int:
        """Create a macvlan shim interface so the **host** can reach
        containers on the macvlan network.

        After this, ``curl http://192.168.10.15:8080`` works from the host.
        Parameters
        ----------
        nic : str
            Parent NIC (same one used for the macvlan Docker network).
        shim_ip : str
            Host-side IP on the macvlan subnet, e.g. ``192.168.10.254``.
            Must **not** overlap with any container IP.
        """
        sudo_cmd = self._sudo_cmd

        def _run(cmd: str) -> int:
            if ssh:
                return DockerHDE2E._run_ssh_command(ssh, cmd)
            return subprocess.run(cmd, shell=True, check=False).returncode

        # Idempotent — skip if the interface already exists
        if _run(sudo_cmd(f"ip link show {shim_name} 2>/dev/null")) == 0:
            print(f"[INFO] Shim interface '{shim_name}' already exists.")
            return 0

        prefix = subnet.rsplit('/', 1)[-1]  # e.g. "24"

        cmds = [
            sudo_cmd(f"ip link add {shim_name} link {nic} type macvlan mode bridge"),
            sudo_cmd(f"ip addr add {shim_ip}/{prefix} dev {shim_name}"),
            sudo_cmd(f"ip link set {shim_name} up"),
        ]
        for cmd in cmds:
            if _run(cmd) != 0:
                print(f"[ERROR] Failed to create macvlan shim: {cmd}")
                return 1

        print(f"[INFO] Macvlan shim '{shim_name}' up at {shim_ip}")
        print(f"[INFO] Host can now reach containers on {subnet} ")
        return 0

    def _macvlan_shim_remove(
        self,
        ssh: Optional[paramiko.SSHClient],
        shim_name: str = "macvlan-shim",
    ) -> int:
        """Remove the macvlan shim interface."""
        sudo_cmd = self._sudo_cmd

        def _run(cmd: str) -> int:
            if ssh:
                return DockerHDE2E._run_ssh_command(ssh, cmd)
            return subprocess.run(cmd, shell=True, check=False).returncode

        if _run(sudo_cmd(f"ip link show {shim_name} 2>/dev/null")) != 0:
            return 0  # already gone
        rc = _run(sudo_cmd(f"ip link del {shim_name}"))
        if rc == 0:
            print(f"[INFO] Removed macvlan shim '{shim_name}'.")
        return rc

    #  Port forwarding via socat  (host IP → container IP)
    #
    #  Docker with iptables-nft actively manages the PREROUTING chain and
    #  removes non-Docker rules within seconds.  Instead of fighting that,
    #  we use socat as a lightweight userspace TCP proxy that Docker
    #  cannot interfere with.
    #
    #  Traffic flow:
    #    client → host_ip:<host_port> → socat → container_ip:<container_port>

    def _socat_forward(
        self,
        ssh: Optional[paramiko.SSHClient],
        host_port: int,
        container_ip: str,
        container_port: int = 8080,
        comment: str = "hde2e",
    ) -> int:
        """Start a socat process to proxy host_port → container_ip:container_port.

        Works reliably regardless of iptables/nftables backend or Docker
        chain management.  Requires the macvlan shim so the host can
        route to the container subnet.
        """

        def _run(cmd: str) -> int:
            if ssh:
                return DockerHDE2E._run_ssh_command(ssh, cmd)
            return subprocess.run(cmd, shell=True, check=False).returncode

        # Check if socat is available
        if _run("which socat >/dev/null 2>&1") != 0:
            print("[WARN] socat not installed — skipping port forward. "
                  "Install with: sudo apt-get install -y socat")
            return 1

        # Kill any existing socat on this host_port (idempotent)
        _run(f"pkill -f 'socat.*TCP-LISTEN:{host_port}' 2>/dev/null")

        # Start socat as a background daemon.
        #   fork         = handle multiple connections
        #   reuseaddr    = allow quick restart
        #   TCP:...      = connect to the macvlan container IP
        #   </dev/null   = detach stdin so the process survives SSH exit
        socat_cmd = (
            f"nohup socat "
            f"TCP-LISTEN:{host_port},fork,reuseaddr "
            f"TCP:{container_ip}:{container_port} "
            f"</dev/null >/dev/null 2>&1 &"
        )
        # sudo needed for ports < 1024
        cmd = self._sudo_cmd(socat_cmd) if host_port < 1024 else socat_cmd
        rc = _run(cmd)
        if rc != 0:
            print(f"[ERROR] socat forward failed: :{host_port} → {container_ip}:{container_port}")
            return 1

        print(f"[INFO] Forward :{host_port} → {container_ip}:{container_port} (socat)")
        return 0

    @staticmethod
    def _socat_remove_forwards(
        ssh: Optional[paramiko.SSHClient],
        comment: str = "hde2e",
    ) -> int:
        """Kill all socat TCP-LISTEN port-forward processes."""

        def _run(cmd: str) -> int:
            if ssh:
                return DockerHDE2E._run_ssh_command(ssh, cmd)
            return subprocess.run(cmd, shell=True, check=False).returncode

        _run("pkill -f 'socat TCP-LISTEN' 2>/dev/null")
        print("[INFO] Removed socat forwards.")
        return 0

    # ──────────────────────────────────────────────────────────────────
    #  Volume data: bundle, transfer, and prepare
    # ──────────────────────────────────────────────────────────────────

    def _extract_ip_from_config(self, app_type: str,
                                instance_num: str) -> Optional[str]:
        """Read the container IP from the instance-specific JSON config.

        The JSON structure uses the first ``pub`` entry's ``"ip"`` field.
        """
        if app_type == "control":
            cfg = os.path.join(
                self.configs_dir, "control",
                f"hdE2ELatencyConfig_Control_PLC_{instance_num}.json"
            )
            key = "controller"
        elif app_type == "io":
            cfg = os.path.join(
                self.configs_dir, "io",
                f"hdE2ELatencyConfig_IO_PLC_{instance_num}.json"
            )
            key = "io"
        else:
            return None

        if not os.path.isfile(cfg):
            print(f"[WARN] Config not found: {cfg}")
            return None

        with open(cfg) as fh:
            data = json.load(fh)

        try:
            return data[key][0]["pub"][0]["ip"]
        except (KeyError, IndexError):
            print(f"[WARN] Could not extract IP from {cfg}")
            return None

    def _create_data_bundle(self, container_name: str,
                            app_type: str,
                            instance_num: str) -> str:
        """Create a tar.gz with the full volume data for one PLC instance.

        Layout inside the tarball (mirrors ``~/dockerMount/{container}/``)::

            conf/codesyscontrol/                        ← .cfg files
            data/codesyscontrol/                        ← PLC app, certs, runtime
            data/codesyscontrol/PlcLogic/Config/        ← instance JSON config
        """
        plc_instance_dir = os.path.join(self.plc_dir, container_name)
        config_src_dir = os.path.join(self.configs_dir, app_type)

        if not os.path.isdir(plc_instance_dir):
            raise FileNotFoundError(
                f"Pre-provisioned PLC data not found: {plc_instance_dir}"
            )

        bundle_path = os.path.join(
            tempfile.gettempdir(), f"{container_name}_bundle.tar.gz"
        )
        print(f"[INFO] Creating data bundle → {bundle_path}")

        with tarfile.open(bundle_path, "w:gz") as tar:
            # 1) Pre-provisioned conf/ and data/ from plc/{container_name}/
            conf_src = os.path.join(plc_instance_dir, "conf", "codesyscontrol")
            data_src = os.path.join(plc_instance_dir, "data", "codesyscontrol")
            if os.path.isdir(conf_src):
                tar.add(conf_src, arcname="conf/codesyscontrol")
            if os.path.isdir(data_src):
                tar.add(data_src, arcname="data/codesyscontrol")

            # 2) Overlay .cfg files from configs/{app_type}/
            for cfg_file in self._glob_ext(config_src_dir, ".cfg"):
                tar.add(cfg_file,
                        arcname=f"conf/codesyscontrol/{os.path.basename(cfg_file)}")

            # 3) Instance JSON config → PlcLogic/Config/
            json_src, dest_name = None, None
            if app_type == "control":
                json_src = os.path.join(
                    config_src_dir,
                    f"hdE2ELatencyConfig_Control_PLC_{instance_num}.json")
                dest_name = "hdE2ELatencyConfig.json"
            elif app_type == "io":
                json_src = os.path.join(
                    config_src_dir,
                    f"hdE2ELatencyConfig_IO_PLC_{instance_num}.json")
                dest_name = "hdE2ELatencyConfigio.json"

            if json_src and os.path.isfile(json_src):
                tar.add(json_src,
                        arcname=f"data/codesyscontrol/PlcLogic/Config/{dest_name}")

        return bundle_path

    @staticmethod
    def _glob_ext(directory: str, ext: str) -> List[str]:
        """Return all files in *directory* ending with *ext*."""
        if not os.path.isdir(directory):
            return []
        return sorted(
            os.path.join(directory, f)
            for f in os.listdir(directory) if f.endswith(ext)
        )

    def _transfer_and_extract_bundle(self, ssh: paramiko.SSHClient,
                                     local_bundle: str,
                                     container_name: str) -> int:
        """SCP a data bundle and extract into ``~/dockerMount/{container}/``."""
        remote_bundle = f"/tmp/{container_name}_bundle.tar.gz"
        remote_mount = f"$HOME/dockerMount/{container_name}"

        self._sftp_put(ssh, local_bundle, remote_bundle)

        for cmd in [
            self._sudo_cmd(f"rm -rf {remote_mount}"),
            f"mkdir -p {remote_mount}",
            f"tar -xzf {remote_bundle} -C {remote_mount}",
            f"rm -f {remote_bundle}",
        ]:
            if self._run_ssh_command(ssh, cmd) != 0:
                print(f"[ERROR] Failed: {cmd}")
                return 1
        return 0

    # ──────────────────────────────────────────────────────────────────
    #  Build the full docker-run command string
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_docker_run_cmd(
        image: str,
        container_name: str,
        hostname: str,
        container_ip: str,
        network: str,
        conf_mount: str,
        data_mount: str,
        cpuset_cpus: Optional[str] = None,
        cpuset_mems: Optional[str] = None,
        rdt_env: Optional[Dict[str, str]] = None,
    ) -> str:

        cap_flags = " ".join(f"--cap-add {c}" for c in DOCKER_CAPS)

        parts = [
            "docker run -d -t",
            f"--network {network}",
            f"--ip {container_ip}",
            f"--name {container_name}",
            f"--hostname {hostname}",
        ]

        if cpuset_cpus:
            parts.append(f"--cpuset-cpus={cpuset_cpus}")
        if cpuset_mems:
            parts.append(f"--cpuset-mems={cpuset_mems}")
        if rdt_env:
            for key, val in rdt_env.items():
                parts.append(f"-e {key}={val}")

        parts += [
            f"-v {conf_mount}:/conf/codesyscontrol/",
            f"-v {data_mount}:/data/codesyscontrol/",
            cap_flags,
            image,
        ]

        return " ".join(parts)

    #  High-level launch: single PLC instance
    def launch_instance(
        self,
        app_type: str,                # "control" or "io"
        instance_num: str,             # "01", "02", …
        ssh: Optional[paramiko.SSHClient] = None,
        network: str = DEFAULT_NETWORK,
        nic: str = "enp3s0",
        image: str = DEFAULT_IMAGE,
        cpuset_cpus: Optional[str] = None,
        cpuset_mems: Optional[str] = None,
        rdt_env: Optional[Dict[str, str]] = None,
    ) -> int:
        """Launch a single PLC container, locally or on a remote host.

        * ``ssh=None``  → container starts on the **local** machine.
        * ``ssh=<client>`` → container starts on the **remote** host.
        """
        prefix = "Control_PLC" if app_type == "control" else "IO_PLC"
        container_name = f"{prefix}_{instance_num}"
        hostname = f"{app_type}-instance{instance_num}"

        # 1. Resolve the container IP from the JSON config
        container_ip = self._extract_ip_from_config(app_type, instance_num)

        cpuset_cpus = self._realtime_core_io(int(instance_num)) if app_type == "io" else self._realtime_core_control(instance_num)
        cpuset_mems = cpuset_mems or self.config.demo.get("cpuset_mems")
        if not container_ip:
            print(f"[ERROR] No IP found for {container_name}")
            return 1

        # 2. Ensure the Docker network exists
        if self._docker_network_ensure(ssh, network, nic) != 0:
            return 1

        # 3. Prepare volume data bundle
        print(f"[INFO] Preparing volume data for {container_name} …")
        bundle = self._create_data_bundle(container_name, app_type, instance_num)

        if ssh:
            if self._transfer_and_extract_bundle(ssh, bundle, container_name) != 0:
                return 1
            mount_base = f"$HOME/dockerMount/{container_name}"
        else:
            mount_base = os.path.expanduser(f"~/dockerMount/{container_name}")
            # Wipe the old mount directory — the CODESYS runtime runs as
            # root and rewrites files via sed -i, leaving them owned by
            # root.  On the next run extractall / open would fail with
            # PermissionError.  A clean slate avoids this entirely.
            if os.path.isdir(mount_base):
                subprocess.run(
                    self._sudo_cmd(f"rm -rf {mount_base}"),
                    shell=True, check=False
                )
            os.makedirs(mount_base, exist_ok=True)
            with tarfile.open(bundle, "r:gz") as tar:
                # Safely extract the tar archive, ensuring all members stay
                # within the intended mount_base directory to avoid
                # directory traversal and arbitrary file writes.
                def _is_within_directory(base_dir: str, target_path: str) -> bool:
                    base_dir_abs = os.path.abspath(base_dir)
                    target_abs = os.path.abspath(target_path)
                    return os.path.commonpath([base_dir_abs]) == os.path.commonpath(
                        [base_dir_abs, target_abs]
                    )

                def _safe_extract(tar_obj: tarfile.TarFile, path: str) -> None:
                    for member in tar_obj.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not _is_within_directory(path, member_path):
                            raise ValueError(
                                f"Unsafe path detected in tar archive entry: {member.name!r}"
                            )
                    tar_obj.extractall(path)

                _safe_extract(tar, mount_base)

        conf_mount = f"{mount_base}/conf/codesyscontrol"
        data_mount = f"{mount_base}/data/codesyscontrol"

        # 4. Remove any stale container with the same name
        rm_cmd = f"docker rm -f {container_name} 2>/dev/null || true"
        if ssh:
            self._run_ssh_command(ssh, rm_cmd)
        else:
            subprocess.run(rm_cmd, shell=True, check=False)

        # 5. Build and run the full docker command
        docker_cmd = self._build_docker_run_cmd(
            image=image,
            container_name=container_name,
            hostname=hostname,
            container_ip=container_ip,
            network=network,
            conf_mount=conf_mount,
            data_mount=data_mount,
            cpuset_cpus=cpuset_cpus,
            rdt_env=rdt_env,
        )

        print(f"[INFO] Launching {container_name} ({container_ip}) …")
        print(f"[INFO] Full command:\n  {docker_cmd}")

        if ssh:
            rc = self._run_ssh_command(ssh, docker_cmd)
        else:
            result = self._run_command(["bash", "-c", docker_cmd], capture=True)
            rc = result.returncode

        if rc != 0:
            print(f"[ERROR] Failed to start {container_name}.")
            return 1

        print(f"[INFO] ✓ {container_name} running at {container_ip}")

        # Set up socat port-forwarding (host_ip:ext_port → container_ip:port)
        # xso external clients can reach services via the host's real IP.
        port_forwards = self.config.demo.get("port_forwards", {})
        fwd_key = container_name  # e.g. "Control_PLC_01"
        if fwd_key in port_forwards:
            for mapping in port_forwards[fwd_key]:
                host_port = mapping["host_port"]
                cport = mapping.get("container_port", 8080)
                self._socat_forward(
                    ssh=ssh,
                    host_port=host_port,
                    container_ip=container_ip,
                    container_port=cport,
                )

        # Clean up local temp bundle
        os.remove(bundle)
        return 0

    #  Orchestration: bring up all Control or IO PLCs from config
    def start_control(self) -> int:
        """Bring up all Control PLC instances (local host)."""
        demo = self.config.demo
        nic = demo.control_system.nic

        # Create macvlan shim so the host can reach container IPs
        shim_ip = demo.control_system.get("shim_ip")
        if shim_ip is None:
            print("[INFO] 'shim_ip' not set for control_system in config")
            print("[INFO] Control PLCs may not be reachable from the host without it.")
            print("[INFO] Skipping macvlan shim setup for control PLCs.")
            print("[INFO] To fix this, set 'demo.control_system.shim_ip' to an unused IP on the macvlan subnet (e.g. 192.168.10.253).")
        else:
            self._macvlan_shim_ensure(ssh=None, nic=nic, shim_ip=shim_ip)

        for idx in range(1, 3):
            instance_num = f"{idx:02d}"
            rc = self.launch_instance(
                app_type="control",
                instance_num=instance_num,
                ssh=None,
                network=DEFAULT_NETWORK,
                nic=nic,
                cpuset_mems=self.config.demo.control_system.get("cpuset_mems"),
                cpuset_cpus=self._realtime_core_control(instance_num),
            )
            if rc != 0:
                return rc
        return 0

    def start_io(self) -> int:
        """Bring up all IO PLC instances on the remote IO system."""
        demo = self.config.demo
        io_host = demo.io_system.ip
        nic = demo.io_system.nic

        if io_host == "localhost":
            ssh = None
        else:
            ssh = self._ssh_connect(
                host=io_host,
                user=demo.io_system.get("ssh_user", "intel"),
                password=demo.io_system.get("ssh_password"),
                port=demo.io_system.get("ssh_port", 22),
            )

        try:
            # Create macvlan shim on the IO host so it can reach container IPs
            shim_ip = demo.io_system.get("shim_ip")
            if shim_ip is None:
                print("[INFO] 'shim_ip' not set for io_system in config")
                print("[INFO] IO PLCs may not be reachable from the IO host without it.")
                print("[INFO] Skipping macvlan shim setup for IO PLCs.")
                print("[INFO] To fix this, set 'demo.io_system.shim_ip' to an unused IP on the macvlan subnet (e.g.)")
            else:
                self._macvlan_shim_ensure(ssh=ssh, nic=nic, shim_ip=shim_ip)

            # Transfer image once, then launch all IO instances
            if ssh:
                image_tar = self.save_image()
                if self.transfer_and_load_image(ssh, image_tar) != 0:
                    return 1

            for idx in range(1, 3):
                instance_num = f"{idx:02d}"
                rc = self.launch_instance(
                    app_type="io",
                    instance_num=instance_num,
                    ssh=ssh,
                    network=DEFAULT_NETWORK,
                    nic=nic,
                    cpuset_cpus=self._realtime_core_io(int(instance_num)),
                )
                if rc != 0:
                    return rc
        finally:
            if ssh:
                ssh.close()
        return 0

    def start_all(self) -> int:
        """Bring up the complete HDE2E demo (Control + IO PLCs)."""
        print("=" * 60)
        print("  HDE2E — Starting all PLC instances")
        print("=" * 60)

        if self.build() != 0:
            return 1

        print("\n── Control PLCs (local) ──")
        if self.start_control() != 0:
            return 1

        print("\n── IO PLCs (remote) ──")
        if self.start_io() != 0:
            return 1

        print("\n[INFO] All PLC instances started successfully.")
        return 0

    #  Teardown
    def stop_all(self) -> int:
        """Stop and remove all PLC containers (local + remote)."""
        containers = [
            "Control_PLC_01", "Control_PLC_02",
            "IO_PLC_01", "IO_PLC_02",
        ]

        for name in containers:
            self._run_command(["docker", "rm", "-f", name])

        # Remove local socat forwards and macvlan shim
        self._socat_remove_forwards(ssh=None)
        self._macvlan_shim_remove(ssh=None)

        demo = self.config.demo
        io_host = demo.io_system.ip
        if io_host != "localhost":
            try:
                ssh = self._ssh_connect(
                    host=io_host,
                    user=demo.io_system.get("ssh_user", "intel"),
                    password=demo.io_system.get("ssh_password"),
                    port=demo.io_system.get("ssh_port", 22),
                )
                for name in containers:
                    self._run_ssh_command(ssh, f"docker rm -f {name}")
                self._socat_remove_forwards(ssh=ssh)
                self._macvlan_shim_remove(ssh=ssh)
                ssh.close()
            except Exception as exc:
                print(f"[WARN] Could not clean up remote containers: {exc}")
                return 1
        return 0
    def _cpu_cores_for_io_instance(self, instance_num: str) -> Optional[str]:
        """Return a CPU core list string for an IO PLC instance."""
        # Example mapping: IO_PLC_01 → cores 4-7, IO_PLC_02 → cores 8-11
        t_cpus = self.config.demo.get("t_cpus")
        if total_cpus < 2:
            print(f"[WARN] Not enough CPU cores for IO PLC instances (need at least 2, got {total_cpus})")
            return None
        return None