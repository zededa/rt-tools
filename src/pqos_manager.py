import sys
import os
import shutil
import subprocess
import json
import hydra
from omegaconf import DictConfig, OmegaConf


import sys
import os
import shutil
import subprocess
import json
import hydra
from omegaconf import DictConfig, OmegaConf


class PQOSManager:
    def __init__(self):
        # Use -I if you want to force OS interface, otherwise defaults to MSR
        self.executable = "pqos"
        self._check_requirements()

    def _check_requirements(self):
        if os.geteuid() != 0:
            raise PermissionError("ROOT ACCESS REQUIRED: Run with 'sudo'")
        if shutil.which("pqos") is None:
            raise FileNotFoundError("'pqos' not found. Install intel-cmt-cat.")

    def _run_command(self, args):
        full_cmd = [self.executable] + args
        try:
            result = subprocess.run(
                full_cmd, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            # Return error in JSON friendly format or raise
            print(f"PQOS CMD FAILED: {e.stderr}", file=sys.stderr)
            raise

    def reset_configuration(self):
        self._run_command(["-R"])

    def apply_allocations(self, class_id, l3_mask=None, l2_mask=None, mba=None):
        """
        Builds a combined allocation string and applies it.
        Example result: pqos -e "llc:1=0xff;l2:1=0xf;mba:1=50"
        """
        allocations = []

        # 1. L3 Cache (LLC)
        if l3_mask:
            allocations.append(f"llc:{class_id}={l3_mask}")

        # 2. L2 Cache
        if l2_mask:
            allocations.append(f"l2:{class_id}={l2_mask}")

        # 3. Memory Bandwidth Allocation (MBA)
        if mba is not None:
            # MBA is typically defined in percentages (10, 20... 100)
            allocations.append(f"mba:{class_id}={mba}")

        if not allocations:
            return  # Nothing to do

        # Join them with semicolons for a single pqos execution
        allocation_str = ";".join(allocations)
        self._run_command(["-e", allocation_str])

    def assign_cores_to_class(self, class_id, core_list):
        if not core_list:
            return
        cores_str = ",".join(map(str, core_list))
        # Note: We use 'llc' type for association, but it applies to the whole COS
        self._run_command(["-a", f"llc:{class_id}={cores_str}"])

    def get_current_status_text(self):
        return self._run_command(["-s"])
