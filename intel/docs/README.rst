==================================================================
Intel Edge Controls Zedada Enablement Benchmarking Suite
==================================================================

Overview
========

The Intel Edge Controls Zedada Enablement Benchmarking Suite is a comprehensive framework designed for real-time performance testing on Intel Edge Computing Infrastructure (ECI). This suite provides containerized benchmarks that evaluate system performance under various workloads while leveraging Intel Resource Director Technology (RDT) for precise cache allocation and CPU affinity controls.

Architecture
============

The benchmarking suite follows a modular containerized architecture:

**Base Layer (eci-base)**
  - Debian bookworm-slim foundation
  - Intel ECI repositories and GPG keys
  - Intel Cache Monitoring Technology (CMT-CAT)
  - OneAPI runtime components
  - OpenVINO toolkit integration
  - ROS2 support infrastructure

**Benchmark Containers**
  - Specialized containers for each benchmark type
  - Optimized runtime environments
  - Pre-configured tools and dependencies

**Orchestration Layer**
  - Unified ``benchmarking.sh`` script
  - Intel RDT integration for cache allocation
  - CPU affinity and isolation controls
  - Background stress testing capabilities

Framework Components
====================

Main Orchestration Script (benchmarking.sh)
--------------------------------------------

The central orchestration script provides unified access to all benchmarks with consistent command-line interface and Intel RDT integration.

**Core Features:**

- Automatic discovery of available benchmarks
- Intel RDT cache allocation and CPU affinity controls
- Background stress testing integration
- Privileged container execution with necessary capabilities
- Resource isolation and performance monitoring

**Usage Syntax:**

.. code-block:: bash

   ./benchmarking.sh <command> [options]

**Commands:**

- ``build`` - Build all benchmark containers
- ``<benchmark_name>`` - Execute specific benchmark with RDT controls

**Required Options for Benchmarks:**

- ``-l, --l3-cache-mask <mask>`` - L3 cache allocation mask (hex format)
- ``-t, --t-core <cores>`` - Target CPU cores (single or comma-separated list)

**Optional Parameters:**

- ``-s, --stressor`` - Enable background stress testing

**Examples:**

.. code-block:: bash

   # Build all benchmarks
   ./benchmarking.sh build
   
   # Run caterpillar on core 15 with specific cache allocation
   ./benchmarking.sh caterpillar -l 0xffe -t 15
   
   # Run with multiple cores and background stress
   ./benchmarking.sh cyclictest --l3-cache-mask 0xffe --t-core 15,16,17 --stressor

Available Benchmarks
====================

1. Caterpillar Benchmark
------------------------

**Purpose:** Real-time computational benchmark designed to measure system responsiveness and deterministic behavior under computational load.

**Source:** Intel ECI repository (eci.intel.com)

**Container:** ``caterpillar:latest``

**Key Features:**

- Deterministic computational workload generation
- Real-time priority scheduling with ``chrt``
- Configurable core affinity and execution duration
- Performance logging and metrics collection
- Integration with Intel RDT for cache allocation

**Technical Implementation:**

- Uses Intel RDT's ``rdtset`` for resource allocation
- Executes with real-time scheduling priority
- Configurable execution duration (default: 12000 iterations)
- Isolated execution on specified CPU cores

**Docker Command Structure:**

.. code-block:: bash

   rdtset -t "l3=<cache_mask>;cpu=<cores>" -c <cores> 
   -k /opt/benchmarking/caterpillar/caterpillar -c <cores> -s 12000

**Use Cases:**

- Real-time system validation
- Cache performance optimization
- Deterministic behavior verification
- Industrial control system testing

2. Cyclictest Benchmark  
-----------------------

**Purpose:** Standard Linux real-time testing tool for measuring timer latency and kernel real-time capabilities.

**Source:** rt-tests package from standard repositories

**Container:** ``cyclictest:latest``

**Key Features:**

- High-resolution timer latency measurement
- Multi-threaded testing capabilities
- Real-time scheduling class execution (SCHED_FIFO, priority 99)
- Statistical analysis of latency variations
- Long-duration testing support (100,000 loops default)

**Technical Implementation:**

- 4 parallel test threads
- 100μs interval testing
- Real-time priority (99) execution
- Statistical collection over 100,000 iterations
- CPU affinity binding to specified cores

**Docker Command Structure:**

.. code-block:: bash

   rdtset -t "l3=<cache_mask>;cpu=<cores>" -c <cores>
   -k /usr/bin/cyclictest --threads -t 4 -p 99 -l 100000 -d 1 -D 0 -i 100000 -a <cores>

**Metrics Collected:**

- Minimum latency
- Maximum latency  
- Average latency
- Standard deviation
- Latency distribution histograms

**Use Cases:**

- Real-time kernel validation
- System latency characterization
- Interrupt handling performance
- Real-time application suitability assessment

3. CODESYS Jitter Benchmark
---------------------------

**Purpose:** Industrial automation runtime benchmark for testing CODESYS Control performance and jitter characteristics in real-time industrial applications.

**Source:** CODESYS Control for Linux SL v4.11.0.0

**Container:** ``codesys-jitter-benchmark:latest``

**Key Features:**

- Complete CODESYS Control runtime environment
- PlcLogic application execution
- Web-based visualization server (port 8080)
- OPC UA server integration (port 4840)
- Real-time task scheduling and jitter measurement
- Intel RDT cache allocation integration

**Technical Implementation:**

- CODESYS Control runtime v3.5.18.20
- PlcLogic benchmark application v4.11.0.0
- Multi-core support (64 cores detected)
- Integrated web server for visualization
- OPC UA server for industrial communication
- Background execution with container persistence

**Configuration Components:**

- ``CODESYSControl.cfg`` - Main runtime configuration
- ``CODESYSControl_User.cfg`` - User-specific settings
- PlcLogic application with performance monitoring
- Web server configuration for remote access

**Docker Command Structure:**

.. code-block:: bash

   docker run -p 8080:8080 -e L3_CACHE_MASK=<mask> -e T_CORE="<cores>"
   -d codesys-jitter-benchmark:latest /docker-entrypoint.sh

**Access Methods:**

- Web visualization: ``http://<host_ip>:8080``
- OPC UA endpoint: ``opc.tcp://<container_name>:4840``

**Use Cases:**

- Industrial automation performance testing
- PLC runtime validation
- Real-time control system benchmarking
- HMI response time measurement

4. CODESYS OPC UA Pub/Sub Benchmark
-----------------------------------

**Purpose:** Communication performance benchmark testing OPC UA publisher/subscriber patterns for industrial IoT and automation scenarios.

**Source:** CODESYS OPC UA components with custom configuration

**Containers:** 
- ``codesys-opcua-server:latest`` (Publisher)
- ``codesys-opcua-client:latest`` (Subscriber)

**Key Features:**

- OPC UA publisher/subscriber pattern implementation
- Real-time data communication testing
- Network latency and throughput measurement
- Industrial protocol performance validation
- Coordinated client-server execution

**Technical Implementation:**

- Dedicated OPC UA server container (port 4840)
- Client container with benchmark application
- Automated coordination between publisher and subscriber
- Performance metrics collection
- Network isolation and measurement

**Execution Flow:**

1. Start OPC UA server container
2. Wait for server initialization (10-second delay)
3. Execute client benchmark with RDT controls
4. Collect communication performance metrics
5. Cleanup server container

**Docker Command Structure:**

.. code-block:: bash

   # Server startup
   docker run -d --rm --privileged --name codesys-opcua-server 
   -p 4840:4840 codesys-opcua-server:latest
   
   # Client execution with RDT
   docker run -e L3_CACHE_MASK=<mask> -e T_CORE="<cores>" 
   -p 8081:8080 codesys-opcua-client:latest /docker-entrypoint.sh

**Use Cases:**

- Industrial IoT communication testing
- OPC UA performance validation
- Network latency characterization
- Real-time data exchange benchmarking

5. Mega Benchmark
-----------------

**Purpose:** Long-duration (48-hour) stability and performance testing for extended system validation under continuous load.

**Source:** Intel ECI realtime benchmarking package

**Container:** ``mega-benchmark:latest``

**Key Features:**

- 48-hour continuous execution
- Multiple benchmark integration
- System stability validation
- Extended performance monitoring
- Automated result collection

**Technical Implementation:**

- Integrated multiple benchmark tools
- Continuous monitoring and logging
- Resource usage tracking
- Automated failure detection
- Result aggregation and analysis

**Use Cases:**

- System stability validation
- Long-term performance characterization
- Production readiness testing
- Reliability assessment

6. Stressor
-----------

**Purpose:** Background stress generation for testing system behavior under load conditions.

**Source:** Custom Linux kernel compilation stress

**Container:** ``stressor:latest``

**Key Features:**

- Continuous background load generation
- Kernel compilation stress testing
- Resource contention simulation
- Configurable stress patterns

**Technical Implementation:**

- Linux kernel source compilation
- Continuous build process execution
- CPU, memory, and I/O stress generation
- Background daemon execution

**Integration:**

- Automatically started with ``--stressor`` flag
- Runs in background during other benchmarks
- Provides realistic system load conditions

Intel RDT Integration
====================

Resource Director Technology (RDT) Features
--------------------------------------------

The benchmarking suite leverages Intel RDT for precise resource allocation and isolation:

**Cache Allocation Technology (CAT):**

- L3 cache partition allocation
- Cache isolation between workloads
- Performance interference reduction

**CPU Affinity Control:**

- Dedicated CPU core assignment
- Process isolation and binding
- NUMA-aware scheduling

**Memory Bandwidth Allocation (MBA):**

- Memory bandwidth throttling
- QoS enforcement
- Resource contention management

**Implementation:**

All benchmarks use ``rdtset`` for resource allocation:

.. code-block:: bash

   rdtset -t "l3=<cache_mask>;cpu=<cores>" -c <cores> -k <benchmark_command>

Configuration Examples
======================

Single Core Execution
---------------------

.. code-block:: bash

   # Dedicate core 15 with specific L3 cache allocation
   ./benchmarking.sh caterpillar -l 0xffe -t 15

Multi-Core Execution
--------------------

.. code-block:: bash

   # Use cores 15,16,17 with shared cache allocation
   ./benchmarking.sh cyclictest -l 0xffe -t 15,16,17

Stress Testing
--------------

.. code-block:: bash

   # Run benchmark with background stress
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 15 --stressor

Container Capabilities
======================

Required Container Privileges
-----------------------------

The benchmarks require specific container capabilities:

**Privileged Mode:**
- Full system access for RDT operations
- Hardware performance counter access
- Real-time scheduling capabilities

**Resource Mounts:**
- ``/sys/fs/resctrl`` - RDT control interface
- ``/dev/cpu_dma_latency`` - DMA latency control

**Capabilities:**
- ``CAP_SYS_NICE`` - Real-time scheduling
- ``CAP_IPC_LOCK`` - Memory locking

**Network Configuration:**
- Host networking for some benchmarks
- Port mapping for web interfaces

Performance Monitoring
======================

Metrics Collection
------------------

Each benchmark provides specific performance metrics:

**Latency Measurements:**
- Minimum, maximum, average latency
- Latency distribution histograms
- Jitter and variance analysis

**Throughput Metrics:**
- Operations per second
- Data transfer rates
- Communication performance

**Resource Utilization:**
- CPU usage patterns
- Memory consumption
- Cache hit/miss ratios

**System Behavior:**
- Real-time constraint violations
- Scheduling delays
- Interrupt handling performance

Troubleshooting
===============

Common Issues
-------------

**Permission Errors:**
- Ensure Docker has privileged access
- Verify RDT support in kernel
- Check container capability configuration

**Resource Conflicts:**
- Verify CPU core availability
- Check cache allocation masks
- Ensure no conflicting processes

**Network Issues:**
- Verify port availability
- Check firewall configurations
- Ensure container networking setup

**Performance Anomalies:**
- Validate system isolation
- Check for background processes
- Verify RDT configuration

Best Practices
==============

System Preparation
------------------

1. **Kernel Configuration:**
   - Enable real-time kernel features
   - Configure RDT support
   - Disable unnecessary services

2. **CPU Isolation:**
   - Use kernel boot parameters for CPU isolation
   - Configure NUMA topology
   - Set appropriate scheduling policies

3. **System Tuning:**
   - Disable power management features
   - Configure interrupt affinity
   - Optimize memory allocation

Benchmark Execution
-------------------

1. **Environment Preparation:**
   - Ensure system idle state
   - Stop non-essential services
   - Configure CPU governor settings

2. **Resource Allocation:**
   - Plan cache allocation strategy
   - Select appropriate CPU cores
   - Consider NUMA topology

3. **Result Validation:**
   - Run multiple iterations
   - Compare baseline measurements
   - Validate result consistency

Development and Extension
========================

Adding New Benchmarks
----------------------

To add a new benchmark to the suite:

1. **Create Benchmark Directory:**
   - Add new directory under project root
   - Include Dockerfile for container build
   - Add benchmark-specific documentation

2. **Update Orchestration Script:**
   - Benchmark auto-discovery will include new directory
   - Add specific execution logic in switch statement
   - Configure required Docker parameters

3. **Integration Testing:**
   - Verify RDT integration
   - Test resource allocation
   - Validate metrics collection

Container Development
---------------------

**Base Image Extension:**
- Extend from ``eci-base:latest``
- Install benchmark-specific dependencies
- Configure runtime environment

**RDT Integration:**
- Use ``rdtset`` for resource allocation
- Configure cache and CPU affinity
- Implement performance monitoring

**Documentation Requirements:**
- Update this documentation
- Add benchmark-specific guides
- Include usage examples

References
==========

- Intel ECI Documentation: https://eci.intel.com
- Intel RDT Technology Guide
- CODESYS Control Documentation
- Linux Real-time Testing Guide
- Docker Container Best Practices