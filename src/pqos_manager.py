import sys
import os
import shutil
import subprocess
import json
import hydra
from omegaconf import DictConfig, OmegaConf


class PQOSManager:
    def __init__(self):
        self.executable = "pqos"
        self._check_requirements()

    def _check_requirements(self):
        if os.geteuid() != 0:
            raise PermissionError("ROOT ACCESS REQUIRED: Run with 'sudo'")
        if shutil.which(self.executable) is None:
            raise FileNotFoundError(
                f"'{self.executable}' not found. Install intel-cmt-cat."
            )

    def _run_command(self, args):
        full_cmd = [self.executable] + args
        try:
            result = subprocess.run(
                full_cmd, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"ERROR: {e.stderr}", file=sys.stderr)
            raise

    def reset_configuration(self):
        self._run_command(["-R"])

    def configure_l3_cat(self, class_id, ways_mask):
        self._run_command(["-e", f"llc:{class_id}={ways_mask}"])

    def assign_cores_to_class(self, class_id, core_list):
        if not core_list:
            return
        cores_str = ",".join(map(str, core_list))
        self._run_command(["-a", f"llc:{class_id}={cores_str}"])

    def get_current_status_text(self):
        """Returns the raw text output of pqos -s"""
        return self._run_command(["-s"])
