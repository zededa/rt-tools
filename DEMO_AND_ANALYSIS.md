# HDE2E Demo and Analysis Guide

This document describes how to run the High Density End-2-End (HDE2E) demo benchmark and analyze the results.

## Prerequisites

- `uv` package manager installed
- Network proxy configured (if behind corporate firewall)
- Docker installed and running
- `sudo` access for hardware-level operations

## Quick Start

### 1. Run the HDE2E Demo

```bash
# If NOT behind a proxy:
sudo $(which uv) run main.py

# If behind a proxy, set environment variables:
sudo http_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT https_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT $(which uv) run main.py
```

Replace `YOUR_PROXY_HOST` and `YOUR_PROXY_PORT` with your proxy settings (e.g., `proxy.company.com:8080`).

**What this does:**
- Collects system information
- Applies PQOS cache and memory bandwidth optimizations (if enabled)
- Launches CODESYS control and IO PLC instances
- Sets up Docker networking and port forwarding
- Runs the HDE2E latency and jitter benchmark

**Expected output:**
- System info saved to `outputs/YYYY-MM-DD/HH-MM-SS/sysinfo.json`
- Docker containers running:
  - `Control_PLC_01` on cores 3,5
  - `Control_PLC_02` on cores 7,9
  - `IO_PLC_01` and `IO_PLC_02` on remote system (10.34.106.119)
- Port forwarding configured:
  - Control web UI: ports 30080, 30081
  - IO web UI: ports 30090, 30091
  - CODESYS gateway: ports 11741, 11742

### 2. Retrieve Results from IO System

The benchmark generates result files on the remote IO system. Copy them to your local machine:

```bash
# Create results directory
mkdir -p ~/Results_testing

# Copy result files from IO system (10.34.106.119)
# Results are stored in: ~/dockerMount/IO_PLC_01/data/codesyscontrol/PlcLogic/Results/
scp intel@10.34.106.119:~/dockerMount/IO_PLC_01/data/codesyscontrol/PlcLogic/Results/*.csv ~/Results_testing/
```

**Note:** You may need to use the same SSH password from `conf/config.yaml` or set up key-based authentication.

### 3. Analyze Results

```bash
# If NOT behind a proxy:
sudo $(which uv) run hde2e-analyze /path/to/results [options]

# If behind a proxy:
sudo http_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT https_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT $(which uv) run hde2e-analyze /path/to/results [options]
```

**Options:**
- `-v, --verbose` - Print detailed statistics
- `-d, --debug` - Print debug information
- `--save` - Save plots as PNG files
- `--show` - Display plots interactively (use only with single instance for testing)
- `--rows N` - Read only first N rows of input data
- `--version` - Show version

**Example with output:**
```bash
sudo http_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT https_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT $(which uv) run hde2e-analyze /home/intel/Results_testing -v --save
```

**Output files generated:**
- `stat_Latency.csv` - Latency statistics
- `stat_Jitter.csv` - Jitter statistics
- `box_Latency.png` - Box plot for latency
- `box_Jitter.png` - Box plot for jitter
- `bar_Latency.png` - Bar chart for latency statistics
- `bar_Jitter.png` - Bar chart for jitter statistics
- `scatter_*.png` - Scatter plots for each latency component and jitter

## Configuration

### Demo Mode Settings

Edit `conf/config.yaml` to customize the demo:

```yaml
demo:
  demo_mode: true              # Enable demo mode
  t_core: [9,11]              # Target cores
  io_system:
    ip: 10.34.106.119         # Remote IO system IP
    nic: enp3s0               # Network interface
    ssh_user: intel           # SSH username
    ssh_password: "..."       # SSH password
    ssh_port: 22              # SSH port
    t_cpus: "1,3"             # IO system target CPUs
  control_system:
    ip: localhost             # Control system IP
    nic: eno12399np0          # Network interface
    t_cpus: "3,5,7,9"         # Control CPUs
```

### PQOS Optimizations

PQOS settings are automatically applied when running the demo. Configure them in `conf/config.yaml`:

```yaml
pqos:
  interface: "os"              # Use Linux resctrl interface
  reset_before_apply: true     # Reset before applying
  
  classes:
    - id: 1
      description: "real-time workload"
      l3_mask: "0x00ff"        # L3 cache mask (8 ways)
      l2_mask: "0x00ff"        # L2 cache mask (8 ways)
      mba: 100                 # Memory bandwidth 100%
      pids: []                 # PIDs (empty for demo)
      cores: []                # Cores (empty for demo)
      
    - id: 0
      description: "background worker"
      l3_mask: "0x7f00"        # L3 cache mask (7 ways)
      l2_mask: "0xff00"        # L2 cache mask (8 ways)
      mba: 10                  # Memory bandwidth 10%
      cores: [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
      pids: [115, 118]
```

## Complete Workflow Example

```bash
# Set proxy variables (if behind a proxy)
export http_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT
export https_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT

# 1. Run the demo (takes ~5-10 minutes)
sudo $(which uv) run main.py

# 2. The benchmark completes - result files are generated on IO system

# 3. Copy results from remote IO system to local machine
mkdir -p ~/Results_testing
scp intel@10.34.106.119:~/dockerMount/IO_PLC_01/data/codesyscontrol/PlcLogic/Results/*.csv ~/Results_testing/

# 4. Verify results were copied
ls -lh ~/Results_testing/Codesys-*.csv

# 5. Analyze results with statistics and plots
sudo $(which uv) run hde2e-analyze ~/Results_testing -v --save

# 6. View generated files
ls -lh ~/Results_testing/*.{csv,png}
```

## Cleaning Up

### Stop Running Containers

```bash
sudo docker stop Control_PLC_01 Control_PLC_02
sudo docker rm Control_PLC_01 Control_PLC_02
```

### Kill Port Forwarding

```bash
sudo pkill -f socat
```

### Full Cleanup (if containers are stuck)

```bash
sudo systemctl restart docker
```

## Troubleshooting

### SSH / SCP Issues

**Error: `Permission denied (publickey,password)`**
- Ensure you have the correct SSH password from `conf/config.yaml`
- Try with explicit password prompt:
  ```bash
  scp -P 22 intel@10.34.106.119:/home/intel/dockerMount/IO_PLC_01/data/codesyscontrol/PlcLogic/Results*.csv ~/Results_testing/
  ```
- If using key-based auth, ensure your public key is on the IO system

**Error: `No such file or directory`**
- Verify the results directory path on the IO system
- Connect to IO system to check: `ssh intel@10.34.106.119 ls -la /home/intel/dockerMount/IO_PLC_01/data/codesyscontrol/PlcLogic/Results`
- Results may be in a different location; check the benchmark output logs

**Slow SCP Transfer**
- Results files can be large (20MB+)
- Use compression: `scp -C intel@10.34.106.119:/path/to/results/*.csv ~/Results_testing/`

### Network Issues

**Error: `Failed to connect to github.com`**
- Ensure proxy is configured: `git config --global http.proxy http://YOUR_PROXY_HOST:YOUR_PROXY_PORT`
- Or set environment variables: `export http_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT`

**Error: `Failed to fetch from pypi.org`**
- Run with proxy environment variables:
  ```bash
  sudo http_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT https_proxy=http://YOUR_PROXY_HOST:YOUR_PROXY_PORT $(which uv) ...
  ```
- Or configure permanently in git: `git config --global http.proxy http://YOUR_PROXY_HOST:YOUR_PROXY_PORT`

### SSH Authentication

**Error: `Authentication failed` for IO system**
- Check SSH credentials in `conf/config.yaml`
- Verify network connectivity to 10.34.106.119 (IO system IP Address)
- Ensure SSH password is correct

### PQOS Issues

**Error: `pqos tool is not installed`**
- The demo will skip PQOS if not available
- Install with: `sudo apt-get install intel-cmt-cat`

**Error: `ROOT ACCESS REQUIRED`**
- All operations require `sudo` for hardware access

### Docker Issues

**Error: `Container stuck in exited state`**
- Restart Docker: `sudo systemctl restart docker`
- Force remove: `sudo docker rm -f <container_id>`

## Output Format

### Statistics Output

The analysis script produces statistics in multiple formats:

**Console Output (verbose mode):**
```
#### T2-T1 ############################
       mean   std   min   max
IO_01 355.4 144.5 195.0 754.0
```

**CSV Files:**
- Statistics at percentiles: 0.9, 0.99, 0.999, 0.9999, 0.99999
- One row per instance
- Columns: mean, std, min, max, and percentiles

### Latency Components

- **T2-T1**: IO to Control transmission time
- **T3-T2**: Control processing time
- **T4-T3**: Control to IO transmission time
- **T4-T1**: Total end-to-end latency
- **Jitter**: PubSub cycle time variation

## Performance Metrics

The HDE2E benchmark measures:
- **Latency**: Time for data to traverse from IO → Control → IO (in microseconds)
- **Jitter**: Variation in PubSub task cycle time (in microseconds)

With PQOS optimizations enabled:
- Real-time workload (Class 1) gets priority cache access
- Background workers (Class 0) are isolated with limited bandwidth
- Results in lower latency and reduced jitter variance

## References

- [CODESYS Documentation](https://help.codesys.com/)
- [Intel CAT/MBA Documentation](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-rdt-cat-mba-linux-rtos-support.html)
- [Docker Documentation](https://docs.docker.com/)
