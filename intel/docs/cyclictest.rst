Cyclictest Benchmark Documentation
===================================

Overview
--------

Cyclictest is the standard Linux real-time testing tool for measuring timer latency and evaluating kernel real-time capabilities. It's part of the rt-tests package and is widely used for validating real-time system performance characteristics.

Purpose
-------

Cyclictest evaluates:

* High-resolution timer latency
* Kernel real-time scheduling performance
* System jitter and timing variations
* Real-time constraint adherence
* Multi-threaded timing consistency

Technical Specifications
------------------------

Container Details
~~~~~~~~~~~~~~~~~

:Base Image: ``eci-base:latest``
:Container Name: ``cyclictest:latest``
:Source: rt-tests package from standard repositories
:Runtime: Native cyclictest binary with real-time scheduling

Key Features
~~~~~~~~~~~~

* High-resolution timer latency measurement
* Multi-threaded testing capabilities (4 threads default)
* Real-time scheduling class execution (SCHED_FIFO, priority 99)
* Statistical analysis of latency variations
* Long-duration testing support (100,000 loops default)
* Intel RDT integration for cache allocation

Usage
-----

Basic Execution
~~~~~~~~~~~~~~~

.. code-block:: bash

   ./benchmarking.sh cyclictest -l <cache_mask> -t <cores>

Parameters
~~~~~~~~~~

Required Parameters
^^^^^^^^^^^^^^^^^^^

* ``-l, --l3-cache-mask <mask>``: L3 cache allocation mask in hexadecimal format
* ``-t, --t-core <cores>``: Target CPU cores for execution (single or comma-separated)

Optional Parameters
^^^^^^^^^^^^^^^^^^^

* ``-s, --stressor``: Enable background stress testing

Examples
~~~~~~~~

Single Core Testing
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Test timer latency on core 15
   ./benchmarking.sh cyclictest -l 0xffe -t 15

Multi-Core Testing
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Test across multiple cores
   ./benchmarking.sh cyclictest -l 0xffe -t 15,16,17,18

With Background Stress
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Test under system load
   ./benchmarking.sh cyclictest -l 0xffe -t 15 --stressor

Technical Implementation
------------------------

Docker Command Structure
~~~~~~~~~~~~~~~~~~~~~~~~~

The framework executes cyclictest using:

.. code-block:: bash

   rdtset -t "l3=${L3_CACHE_MASK};cpu=${T_CORE}" -c ${T_CORE} \
   -k /usr/bin/cyclictest --threads -t 4 -p 99 -l 100000 -d 1 -D 0 -i 100000 -a ${T_CORE}

Parameter Breakdown
~~~~~~~~~~~~~~~~~~~

Intel RDT Configuration
^^^^^^^^^^^^^^^^^^^^^^^

* **rdtset**: Resource allocation command
* **l3=${L3_CACHE_MASK}**: L3 cache partition allocation
* **cpu=${T_CORE}**: CPU core affinity binding
* **-c ${T_CORE}**: Core specification for rdtset
* **-k**: Keep allocation during execution

Cyclictest Parameters
^^^^^^^^^^^^^^^^^^^^^

* **--threads**: Enable multi-threaded testing
* **-t 4**: Number of test threads (4 threads)
* **-p 99**: Real-time priority (SCHED_FIFO, priority 99)
* **-l 100000**: Number of test loops (100,000 iterations)
* **-d 1**: Test interval distance (1 microsecond)
* **-D 0**: Duration of test run (0 = run until completion)
* **-i 100000**: Test interval (100,000 nanoseconds = 100μs)
* **-a ${T_CORE}**: CPU affinity for threads

Container Configuration
^^^^^^^^^^^^^^^^^^^^^^^

* **Privileged Mode**: Required for real-time scheduling and RDT access
* **CPU Set**: Limits container to specified cores
* **Resource Mounts**:
  
  * ``/sys/fs/resctrl``: RDT control interface
  * ``/dev/cpu_dma_latency``: DMA latency control device

* **Capabilities**:
  
  * ``CAP_SYS_NICE``: Real-time scheduling permissions
  * ``CAP_IPC_LOCK``: Memory locking capabilities

Performance Metrics
--------------------

Measured Parameters
~~~~~~~~~~~~~~~~~~~

Latency Statistics
^^^^^^^^^^^^^^^^^^

* **Minimum Latency**: Best-case timer response time
* **Maximum Latency**: Worst-case timer response time  
* **Average Latency**: Mean timer response time
* **Standard Deviation**: Latency variation measurement

Distribution Analysis
^^^^^^^^^^^^^^^^^^^^^

* **Latency Histograms**: Distribution of response times
* **Percentile Analysis**: 95th, 99th, 99.9th percentile latencies
* **Outlier Detection**: Identification of anomalous measurements

Real-time Metrics
^^^^^^^^^^^^^^^^^

* **Deadline Misses**: Count of timing constraint violations
* **Jitter Analysis**: Timer interval consistency
* **Thread Consistency**: Per-thread performance comparison

Output Format
~~~~~~~~~~~~~

Cyclictest generates detailed output including:

.. code-block:: text

   # /dev/cpu_dma_latency set to 0us
   T: 0 ( 1234) P:99 I:100000 C: 100000 Min:    2 Act:    4 Avg:    3 Max:   45
   T: 1 ( 1235) P:99 I:100000 C: 100000 Min:    2 Act:    3 Avg:    3 Max:   42
   T: 2 ( 1236) P:99 I:100000 C: 100000 Min:    2 Act:    4 Avg:    3 Max:   38
   T: 3 ( 1237) P:99 I:100000 C: 100000 Min:    2 Act:    3 Avg:    3 Max:   41

Where:

* **T**: Thread number
* **P**: Priority level
* **I**: Interval (nanoseconds)
* **C**: Completed cycles
* **Min**: Minimum latency (microseconds)
* **Act**: Actual current latency
* **Avg**: Average latency
* **Max**: Maximum latency observed

System Requirements
-------------------

Hardware Requirements
~~~~~~~~~~~~~~~~~~~~~

* Intel processor with high-resolution timer support
* Multi-core CPU architecture for thread testing
* Intel RDT support for cache allocation
* NUMA-aware system (recommended)

Software Requirements
~~~~~~~~~~~~~~~~~~~~~

* Linux kernel with real-time patches (PREEMPT_RT recommended)
* High-resolution timer support (``CONFIG_HIGH_RES_TIMERS``)
* RDT support enabled in kernel
* Docker with privileged container support

Kernel Configuration
~~~~~~~~~~~~~~~~~~~~

Required Kernel Options
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   CONFIG_HIGH_RES_TIMERS=y
   CONFIG_PREEMPT_RT=y
   CONFIG_INTEL_RDT=y
   CONFIG_X86_CPU_RESCTRL=y

Boot Parameters
^^^^^^^^^^^^^^^

.. code-block:: bash

   # Optimal real-time configuration
   isolcpus=<core_list>           # Isolate CPU cores
   nohz_full=<core_list>          # Disable timer ticks on isolated cores
   rcu_nocbs=<core_list>          # Disable RCU callbacks
   intel_iommu=on                 # Enable IOMMU
   processor.max_cstate=1         # Limit C-states for consistent timing
   intel_idle.max_cstate=0        # Disable deep idle states

Best Practices
--------------

System Preparation
~~~~~~~~~~~~~~~~~~

CPU Configuration
^^^^^^^^^^^^^^^^^

1. **CPU Isolation**: Reserve cores exclusively for testing
2. **Frequency Scaling**: Set CPU governor to 'performance'
3. **Thermal Management**: Ensure adequate cooling to prevent throttling
4. **IRQ Affinity**: Route interrupts away from test cores

.. code-block:: bash

   # Set CPU governor
   echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

   # Configure IRQ affinity (example for core isolation)
   echo 0x01 > /proc/irq/default_smp_affinity

Memory Configuration
^^^^^^^^^^^^^^^^^^^^

1. **NUMA Topology**: Consider NUMA node placement
2. **Memory Locking**: Prevent memory swapping
3. **Huge Pages**: Use huge pages for memory allocation consistency

System Services
^^^^^^^^^^^^^^^

1. **Service Minimization**: Stop non-essential services
2. **Cgroup Configuration**: Use cgroups for resource isolation
3. **Scheduler Tuning**: Optimize kernel scheduler parameters

Cache Allocation Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~

Mask Calculation
^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Example: Allocate 75% of L3 cache (assuming 16-way associative)
   # 12 ways out of 16 = 0xfff
   L3_CACHE_MASK=0xfff

Allocation Guidelines
^^^^^^^^^^^^^^^^^^^^^

1. **Size Adequacy**: Ensure sufficient cache for workload
2. **Conflict Avoidance**: Avoid overlap with critical system processes
3. **Performance Validation**: Measure cache effectiveness

Testing Methodology
~~~~~~~~~~~~~~~~~~~

Baseline Establishment
^^^^^^^^^^^^^^^^^^^^^^

1. **System Idle**: Measure baseline with minimal system activity
2. **No RDT**: Test without cache allocation for comparison
3. **Default Scheduling**: Compare with non-real-time scheduling

Load Testing
^^^^^^^^^^^^

1. **Background Stress**: Use stressor for realistic load conditions
2. **Interrupt Load**: Test with varying interrupt rates
3. **Memory Pressure**: Test under memory allocation stress

Result Validation
^^^^^^^^^^^^^^^^^

1. **Multiple Runs**: Execute multiple test iterations
2. **Statistical Analysis**: Ensure result consistency
3. **Environment Consistency**: Maintain consistent test conditions

Integration with Other Benchmarks
----------------------------------

Complementary Testing
~~~~~~~~~~~~~~~~~~~~~

* **Caterpillar**: Compare computational vs. timer latency
* **CODESYS**: Validate industrial real-time requirements
* **OPC UA**: Assess communication impact on timing

Stress Testing Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

When using ``--stressor``:

* Background kernel compilation provides realistic system load
* Tests real-time behavior under resource contention
* Validates cache allocation effectiveness

Performance Correlation
~~~~~~~~~~~~~~~~~~~~~~~

* Cross-reference results with hardware performance counters
* Compare with application-specific latency requirements
* Validate against real-time system specifications

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

High Maximum Latency
^^^^^^^^^^^^^^^^^^^^

**Symptoms**: Unexpectedly high maximum latency values

**Causes**:

* Interrupt handling on test cores
* Memory allocation/deallocation
* Thermal throttling
* Background system activity

**Solutions**:

.. code-block:: bash

   # Check interrupt affinity
   cat /proc/interrupts
   # Verify CPU isolation
   cat /sys/devices/system/cpu/isolated
   # Monitor thermal status
   cat /sys/class/thermal/thermal_zone*/temp

Inconsistent Results
^^^^^^^^^^^^^^^^^^^^

**Symptoms**: Large variation between test runs

**Causes**:

* System background activity
* Inconsistent CPU frequency
* Memory pressure
* Network activity

**Solutions**:

1. Stop non-essential services
2. Set consistent CPU frequency
3. Monitor system resource usage
4. Use network isolation

Permission Errors
^^^^^^^^^^^^^^^^^

**Symptoms**: Cannot set real-time priority or access RDT

**Solutions**:

.. code-block:: bash

   # Verify container privileges
   docker run --privileged --rm cyclictest:latest cat /proc/1/status | grep Cap

   # Check RDT availability
   ls -la /sys/fs/resctrl/

Debug Analysis
~~~~~~~~~~~~~~

Latency Spike Investigation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Trace Analysis**: Use kernel tracing tools
2. **Performance Counters**: Monitor hardware events
3. **System Monitoring**: Check for competing processes

Performance Tuning
^^^^^^^^^^^^^^^^^^^

1. **Cache Optimization**: Adjust cache allocation masks
2. **Core Selection**: Test different core combinations
3. **Scheduler Tuning**: Optimize real-time scheduler parameters

Advanced Configuration
----------------------

Custom Test Parameters
~~~~~~~~~~~~~~~~~~~~~~

Extended Testing
^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Long-duration test (1 million loops)
   cyclictest -t 4 -p 99 -l 1000000 -i 100000 -a <cores>

   # High-frequency testing (10μs interval)
   cyclictest -t 4 -p 99 -l 100000 -i 10000 -a <cores>

Histogram Generation
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Generate latency histograms
   cyclictest -t 4 -p 99 -l 100000 -i 100000 -h 200 -a <cores>

References
----------

* Linux RT-tests Documentation: `kernel.org <https://kernel.org>`_
* Intel RDT Programming Guide
* PREEMPT_RT Patch Documentation
* Real-time Linux Best Practices Guide
* Intel ECI Documentation: `eci.intel.com <https://eci.intel.com>`_
