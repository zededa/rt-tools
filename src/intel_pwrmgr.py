# Helper functions to manage Intel Power management
# Note that it's not used in benchmark, since we disabled
# _everything_ in BIOS settings. Left here as a pointer
# if one needs to set it up for their hardware


import pwr  # Import the module
from omegaconf import DictConfig


TURBO_PATH = "/sys/devices/system/cpu/intel_pstate/no_turbo"


def configure_cores(cfg: DictConfig):
    """
    if
    disable turbo
    disable C - states
    fix clock to specified Freq
    """
    set_turbo(cfg.cpus.enable_turbo)
    core_list = [int(x) for x in cfg.cpus.t_core.split(",")]
    configure_selected_cores(core_list)


def set_turbo(enable: bool):
    """This function enable or disable the turbo."""
    val = str(int(not enable))
    try:
        with open(TURBO_PATH, "w") as state_file:
            state_file.write(val)
    except (IOError, OSError, ValueError) as err:
        print(f"{err}: failed to enable or disable the turbo")


def configure_selected_cores(core_ids):
    """
    Set selected cores to a fixed frequency of 3 MHz and disable all C-states.

    Args:
        core_ids (list[int]): List of core IDs (integers) to configure.
    """
    target_freq = 3  # MHz
    all_cores = pwr.get_cores()  # Fetch all available cores

    # Filter cores by the provided core IDs
    selected_cores = [c for c in all_cores if c.core_id in core_ids]

    if not selected_cores:
        print(f"No matching cores found for IDs: {core_ids}")
        return

    for core in selected_cores:
        core.refresh_stats()  # Ensure current stats are up-to-date

        # Set min and max frequency to 3 MHz
        core.min_freq = target_freq
        core.max_freq = target_freq

        # Disable all C-states if available
        if core.cstates:
            for state in core.cstates:
                core.cstates[state] = False

        # Commit changes to hardware
        core.commit()

    print(
        f"Configured cores {core_ids}: min/max = {target_freq}MHz, all C-states disabled."
    )
