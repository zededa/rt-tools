# Intel Edge Controls Zedada Enablement Benchmarking Suite

A comprehensive benchmarking framework for real-time performance testing on Intel Edge Computing Infrastructure (ECI). This suite provides containerized benchmarks for evaluating system performance under various workloads with Intel Resource Director Technology (RDT) cache allocation and CPU affinity controls.

## Overview

This benchmarking suite enables performance testing of real-time applications and systems using Intel's Edge Computing Infrastructure. It includes multiple specialized benchmarks designed to test different aspects of real-time performance:

- **Real-time latency testing** with cyclictest
- **Computational workload analysis** with Caterpillar
- **Industrial automation benchmarks** with CODESYS Control runtime
- **OPC UA communication performance** testing
- **System stress testing** capabilities
- **Long-duration stability testing** with mega-benchmark
- **Network performance and bandwidth testing** with iperf3

## Quick Start

### Prerequisites

- Debian 12 (Bookwork)
- Docker installed and configured
- Privileged container execution capabilities
- Intel RDT-enabled system (for cache allocation features)

### Setup ECI Repository

1. Open a terminal
2. Download the ECI APT key to the system keyring:

```bash
sudo -E wget -O- https://eci.intel.com/repos/gpg-keys/GPG-PUB-KEY-INTEL-ECI.gpg | sudo tee /usr/share/keyrings/eci-archive-keyring.gpg > /dev/null
```
3. Add the signed APT sources and configure the APT client to use the ECI APT repository:

```bash
echo "deb [signed-by=/usr/share/keyrings/eci-archive-keyring.gpg] https://eci.intel.com/repos/$(source /etc/os-release && echo $VERSION_CODENAME) isar main" | sudo tee /etc/apt/sources.list.d/eci.list
echo "deb-src [signed-by=/usr/share/keyrings/eci-archive-keyring.gpg] https://eci.intel.com/repos/$(source /etc/os-release && echo $VERSION_CODENAME) isar main" | sudo tee -a /etc/apt/sources.list.d/eci.list
```
4. Configure the ECI APT reposity to have higher priority over other repositories and ping the version of the libflann packages:

```bash
sudo bash -c 'echo -e "Package: *\nPin: origin eci.intel.com\nPin-Priority: 1000" > /etc/apt/preferences.d/isar'
sudo bash -c 'echo -e "\nPackage: libflann*\nPin: version 1.19.*\nPin-Priority: -1\n\nPackage: flann*\nPin: version 1.19.*\nPin-Priority: -1" >> /etc/apt/preferences.d/isar'
```
5. Update your apt sources lists

```bash
sudo apt update
```
6. Install ECI Grub menu.


### Setup Real Time Kernel

```bash
sudo apt install eci-experimental
```
1. Update the firmware packages
```bash
sudo apt-get reinstall '(firmware-linux-nonfree|linux-firmware$)'
```
2. Install 6.12.8 Kernel
```bash
sudo apt install linux-intel-rt-experimental
```
3. Reboot the target system
```bash
sudo reboot
```

4. Update Kernel (Change Isolated cpus)
```bash
sudo vim /etc/grub.d/09_eci
```
update `isolcpus` to the core you want isolated

5. Update grub and reboot
```bash
sudo update-grub
sudo reboot
```


### Build All Benchmarks

```bash
./benchmarking.sh build
```

### Mount Resource Control 
1. Mount Resource Control

```bash
sudo mount -t resctrl resctrl /sys/fs/resctrl
```
### Run a Benchmark

```bash
# Example: Run caterpillar benchmark with specific cache and core settings
./benchmarking.sh caterpillar -l 0xffe -t 15

# Example: Run with background stressor
./benchmarking.sh caterpillar --l3-cache-mask 0xffe --t-core 15,16,17 --stressor
```

## Available Benchmarks

### 1. Caterpillar
Real-time computational benchmark for measuring system responsiveness under load.
- **Purpose**: Deterministic computational workload testing
- **Source**: Intel ECI repository
- **Documentation**: [https://eci.intel.com/docs/3.3/development/performance/benchmarks.html?highlight=caterpillar#caterpillar](Caterpillar)

### 2. Cyclictest
Standard Linux real-time testing tool for measuring timer latency.
- **Purpose**: High-resolution timer latency measurement
- **Source**: rt-tests package
- **Documentation**: [https://eci.intel.com/docs/3.3/development/performance/benchmarks.html?highlight=caterpillar#caterpillar](cyclictest)

### 3. CODESYS Jitter Benchmark
Industrial automation runtime benchmark testing PLC performance and jitter.
- **Purpose**: Industrial automation runtime validation
- **Source**: CODESYS Control for Linux SL
- **Documentation**: [https://eci.intel.com/docs/3.3/components/codesys.html#codesys-ui-benchmark](Codesys-Jitter-Benchmark)

### 4. CODESYS OPC UA Pub/Sub
Communication benchmark testing OPC UA publisher/subscriber performance.
- **Purpose**: Industrial communication protocol testing
- **Source**: CODESYS OPC UA components
- **Documentation**: [https://eci.intel.com/docs/3.3/components/codesys.html#codesys-opcua-client-benchmark](Codesys-opcua-Benchmark)

### 5. Mega Benchmark
Long-duration (48-hour) stability and performance testing.
- **Purpose**: Extended system stability validation
- **Source**: Intel ECI realtime benchmarking package
- **Documentation**: [https://eci.intel.com/docs/3.3/development/performance/benchmarks.html#mega-benchmark](mega-benchmark)

### 6. Iperf3
Network performance and bandwidth testing.
- **Purpose**: Networking measurements
- **Source**: Open source iperf3

### 7. Stressor
Background stress generation for testing system behavior under load.
- **Purpose**: Realistic background load simulation
- **Source**: Linux kernel compilation stress

## Documentation

### Complete Documentation
- [**Comprehensive Guide**](docs/README.rst) - Complete technical documentation
- [**Usage Guide**](docs/usage-guide.rst) - Quick start and common usage patterns

### Individual Benchmark Documentation
- [Caterpillar](docs/caterpillar.rst) - Real-time computational benchmark
- [Cyclictest](docs/cyclictest.rst) - Timer latency testing
- [CODESYS Jitter](docs/codesys-jitter-benchmark.rst) - Industrial automation testing
- [CODESYS OPC UA](docs/codesys-opcua-pubsub.rst) - Industrial communication testing
- [Mega Benchmark](docs/mega-benchmark.rst) - Long-duration stability testing
- [Iperf3](docs/iperf3.rst) - Network and bandwidth testing

## Architecture

The framework is built on a layered architecture:

### Base Infrastructure
- **ECI Base Image**: Common foundation with Intel tools and repositories
- **Intel RDT Integration**: Cache allocation and CPU affinity controls
- **Container Orchestration**: Unified execution through benchmarking.sh script

### Intel RDT Integration
All benchmarks leverage Intel Resource Director Technology:
- **Cache Allocation Technology (CAT)**: L3 cache partitioning
- **CPU Affinity Control**: Dedicated core assignment
- **Memory Bandwidth Allocation**: QoS enforcement

### Execution Framework
```bash
# Unified command structure
./benchmarking.sh <benchmark> -l <cache_mask> -t <cores> [--stressor]

# Example with RDT controls
rdtset -t "l3=${L3_CACHE_MASK};cpu=${T_CORE}" -c ${T_CORE} -k <benchmark_command>
```

## Key Features

### Resource Control
- **Intel RDT Integration**: Precise cache and CPU resource allocation
- **Container Isolation**: Privileged containers with necessary capabilities
- **NUMA Awareness**: Topology-aware resource assignment

### Performance Monitoring
- **Real-time Metrics**: Latency, throughput, and jitter measurement
- **System Monitoring**: CPU, memory, and cache performance tracking
- **Comprehensive Logging**: Detailed performance data collection

### Industrial Focus
- **CODESYS Integration**: Complete industrial automation runtime testing
- **OPC UA Testing**: Industrial communication protocol validation
- **Real-time Validation**: Deterministic behavior verification

### Stress Testing
- **Background Load**: Realistic system stress simulation
- **Resource Contention**: Cache and CPU competition testing
- **Long-duration Testing**: 48-hour stability validation

## System Requirements

### Hardware
- Intel processor with RDT support
- Multi-core CPU architecture
- Sufficient memory (8GB minimum, 16GB recommended)
- Network connectivity for web interfaces

### Software
- Linux kernel with RDT support enabled
- Docker with privileged container support
- Intel CMT-CAT tools
- Real-time kernel configuration (recommended)

### Configuration
```bash
# Kernel boot parameters for optimal performance
isolcpus=<core_list>        # Isolate CPU cores
nohz_full=<core_list>       # Disable timer ticks
rcu_nocbs=<core_list>       # Disable RCU callbacks
```

## Usage Examples

### Basic Performance Testing
```bash
# Build all containers
./benchmarking.sh build

# Test timer latency
./benchmarking.sh cyclictest -l 0xffe -t 15

# Test computational performance
./benchmarking.sh caterpillar -l 0xffe -t 16

# Test Network performance
./benchmarking.sh iperf3 -l 0xffe -t 15
```

### Industrial Automation Testing
```bash
# Test PLC runtime performance
./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 15

# Test industrial communication
./benchmarking.sh codesys-opcua-pubsub -l 0xffe -t 16
```

### Stress Testing
```bash
# Test under system load
./benchmarking.sh cyclictest -l 0xffe -t 15 --stressor
./benchmarking.sh caterpillar -l 0xffe -t 16 --stressor
```

### Multi-Core Testing
```bash
# Allocate multiple cores
./benchmarking.sh cyclictest -l 0xffe -t 15,16,17,18
```

## Development and Extension

### Adding New Benchmarks
1. Create benchmark directory with Dockerfile
2. Update auto-discovery in benchmarking.sh
3. Add execution logic to main script
4. Create documentation following existing patterns

### Integration Testing
- RDT resource allocation validation
- Container privilege verification
- Performance metric collection testing

## References

- **Intel ECI Documentation**: https://eci.intel.com
- **Intel RDT Technology Guide**: Resource Director Technology overview
- **CODESYS Documentation**: Industrial automation platform
- **Linux Real-time Documentation**: PREEMPT_RT and real-time best practices

## License

Intel Confidential - See individual source files for specific license terms.

## Support

For support and questions:
- Review documentation in `docs/` directory
- Check troubleshooting sections in individual benchmark docs
- Consult Intel ECI resources at eci.intel.com
