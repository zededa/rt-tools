import argparse
import os
import sys
import hydra
import subprocess
import threading

from omegaconf import DictConfig, OmegaConf

from src.bios_settings import process_bios_settings

from src.metrics import (
    CPUmonitor,
    InterruptMonitor,
    MemInfoMonitor,
    SoftIrqMonitor,
    CpuStatMonitor,
    PQOSMonitor,
)
from src.sysinfo_collector import SystemInfoCollector
from src.pqos_manager import PQOSManager
from src.irq_affinity import set_irq_affinity
from src.test_runner import DockerTestRunner
from src.hde2e import DockerHDE2E


def setup_pqos(cfg: DictConfig) -> None:
    try:
        manager = PQOSManager()
    except Exception as e:
        print(f"Init Error: {e}")
        return

    if cfg.pqos.get("reset_before_apply", False):
        manager.reset_configuration()

    if "classes" in cfg.pqos:
        for item in cfg.pqos.classes:
            class_id = item.id

            # Extract config values (default to None if missing)
            l3 = item.get("l3_mask")
            l2 = item.get("l2_mask")
            mba = item.get("mba")
            cores = (
                OmegaConf.to_container(item.cores, resolve=True) if item.cores else []
            )
            pids = OmegaConf.to_container(item.pids, resolve=True) if item.cores else []

            print(f"Configuring Class {class_id}...")

            # Apply Hardware Allocations
            try:
                manager.apply_allocations(class_id, l3_mask=l3, l2_mask=l2, mba=mba)
            except subprocess.CalledProcessError:
                print(
                    f"Warning: Failed to apply allocations for Class {class_id}. Check if HW supports L2/MBA."
                )

            if pids:
                manager.assign_pids_to_class(class_id, pids)

            # Apply Core Associations
            if cores:
                manager.assign_cores_to_class(class_id, cores)

    print(manager.get_current_status_text())


def setup_metrics(cfg: DictConfig) -> None:
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
    pqos_monitor = PQOSMonitor(cfg.pqos_monitor.path, cfg.pqos_monitor.interval)

    cpu_monitor.start()
    interrupt_monitor.start()
    meminfo_monitor.start()
    softirq_monitor.start()
    cpustat_monitor.start()
    pqos_monitor.start()


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig):
    collector = SystemInfoCollector()
    collector.gather_all(cfg)
    collector.dump_to_file(cfg.sysinfo_collector_file)

    # Collect BIOS settings via redfish
    if cfg.bios.enable:
        process_bios_settings(cfg.bios)

    if cfg.demo.demo_mode:
        print("Running in demo mode. Skipping test execution.")
        setup_pqos(cfg)
        runner = DockerHDE2E(cfg)
        print("Starting demo HDE2E test...")
        print("Starting IO...")
        io_thread = threading.Thread(target=runner.start_io)
        control_thread = threading.Thread(target=runner.start_control)

        print("Starting IO...")
        io_thread.start()
        print("Starting Control...")
        control_thread.start()

        io_thread.join()
        control_thread.join()
        return 0
    else:
        runner = DockerTestRunner(cfg)

        if cfg.run.command == "build":
            return runner.build()

        setup_pqos(cfg)

        # Handle test commands
        if cfg.run.command not in runner.tests:
            print(f"Error: '{cfg.run.command}' is not a valid command")
            return 1

        if cfg.run.metrics:
            setup_metrics(cfg)
        if cfg.irq_affinity.enabled:
            set_irq_affinity(cfg.irq_affinity.housekeeping_cores)

        return runner.run_test(cfg.run.command, cfg.run.t_core, cfg.run.stressor)


if __name__ == "__main__":
    main()
