Caterpillar Benchmark Documentation
====================================

Overview
--------

Caterpillar is a real-time computational benchmark designed to measure system responsiveness and deterministic behavior under computational load. It's part of the Intel ECI (Edge Computing Infrastructure) benchmarking suite and is specifically designed for testing real-time systems.

Purpose
-------

The Caterpillar benchmark evaluates:

* System real-time performance characteristics
* Deterministic execution behavior
* Cache allocation effectiveness
* CPU core isolation capabilities
* Real-time scheduling performance

Technical Specifications
------------------------

Container Details
~~~~~~~~~~~~~~~~~

:Base Image: ``eci-base:latest``
:Container Name: ``caterpillar:latest``
:Source: Intel ECI repository package
:Runtime: Native binary execution with real-time scheduling

Key Features
~~~~~~~~~~~~

* Real-time priority scheduling using ``chrt``
* Intel RDT (Resource Director Technology) integration
* Configurable CPU core affinity
* Performance logging and metrics collection
* Deterministic computational workload generation

Usage
-----

Basic Execution
~~~~~~~~~~~~~~~

.. code-block:: bash

   ./benchmarking.sh caterpillar -l <cache_mask> -t <core>

Parameters
~~~~~~~~~~

Required Parameters
^^^^^^^^^^^^^^^^^^^

* ``-l, --l3-cache-mask <mask>``: L3 cache allocation mask in hexadecimal format
* ``-t, --t-core <core>``: Target CPU core for execution

Optional Parameters
^^^^^^^^^^^^^^^^^^^

* ``-s, --stressor``: Enable background stress testing

Examples
~~~~~~~~

Single Core Execution
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Run on core 15 with specific cache allocation
   ./benchmarking.sh caterpillar -l 0xffe -t 15

With Background Stress
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Run with background stressor for load testing
   ./benchmarking.sh caterpillar -l 0xffe -t 15 --stressor

Multiple Core Allocation
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Allocate multiple cores for testing
   ./benchmarking.sh caterpillar -l 0xffe -t 15,16,17

Technical Implementation
------------------------

Docker Command Structure
~~~~~~~~~~~~~~~~~~~~~~~~~

The framework executes Caterpillar using the following command structure:

.. code-block:: bash

   rdtset -t "l3=${L3_CACHE_MASK};cpu=${T_CORE}" -c ${T_CORE} \
   -k /opt/benchmarking/caterpillar/caterpillar -c ${T_CORE} -s 12000

Component Breakdown
~~~~~~~~~~~~~~~~~~~

Intel RDT Integration
^^^^^^^^^^^^^^^^^^^^^

* **rdtset**: Intel RDT command-line tool for resource allocation
* **Cache Allocation**: L3 cache partitioning using specified mask
* **CPU Affinity**: Binds execution to specified CPU cores

Caterpillar Parameters
^^^^^^^^^^^^^^^^^^^^^^

* ``-c <core>``: Specifies target CPU core
* ``-s 12000``: Sets execution duration (12,000 iterations)

Container Configuration
^^^^^^^^^^^^^^^^^^^^^^^

* **Privileged Mode**: Required for RDT access and real-time scheduling
* **CPU Set**: Limits container to specified cores
* **Resource Mounts**:
  
  * ``/sys/fs/resctrl``: RDT control interface
  * ``/dev/cpu_dma_latency``: DMA latency control

* **Capabilities**:
  
  * ``CAP_SYS_NICE``: Real-time scheduling
  * ``CAP_IPC_LOCK``: Memory locking

Performance Metrics
--------------------

Measured Parameters
~~~~~~~~~~~~~~~~~~~

* **Execution Time**: Total benchmark completion time
* **Latency Characteristics**: Response time variations
* **Throughput**: Operations completed per unit time
* **Jitter**: Execution time variance
* **Cache Performance**: Cache hit/miss ratios with RDT

Output Format
~~~~~~~~~~~~~

Caterpillar generates performance logs containing:

* Timestamp information
* Execution statistics
* Latency measurements
* Cache allocation effectiveness
* Real-time constraint adherence

System Requirements
-------------------

Hardware Requirements
~~~~~~~~~~~~~~~~~~~~~

* Intel processor with RDT support
* Multi-core CPU architecture
* Sufficient L3 cache for allocation testing

Software Requirements
~~~~~~~~~~~~~~~~~~~~~

* Linux kernel with RDT support enabled
* Docker with privileged container support
* Intel CMT-CAT tools installed
* Real-time kernel configuration (recommended)

Kernel Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Required kernel boot parameters for optimal performance
   isolcpus=<core_list>        # Isolate CPU cores
   nohz_full=<core_list>       # Disable timer ticks
   rcu_nocbs=<core_list>       # Disable RCU callbacks

Best Practices
--------------

System Preparation
~~~~~~~~~~~~~~~~~~

1. **CPU Isolation**: Isolate target cores from general OS scheduling
2. **Governor Settings**: Set CPU frequency governor to 'performance'
3. **IRQ Affinity**: Configure interrupt handling away from test cores
4. **Background Services**: Minimize system background activity

Cache Allocation Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Mask Calculation**: Use appropriate cache allocation masks
2. **Conflict Avoidance**: Ensure no overlap with system critical processes
3. **Size Optimization**: Allocate sufficient cache for benchmark workload

Testing Methodology
~~~~~~~~~~~~~~~~~~~

1. **Baseline Measurement**: Establish system baseline without RDT
2. **Iterative Testing**: Run multiple iterations for statistical validity
3. **Load Variation**: Test under different system load conditions
4. **Result Validation**: Compare results across different configurations

Integration with Other Benchmarks
----------------------------------

Stressor Integration
~~~~~~~~~~~~~~~~~~~~

When using the ``--stressor`` flag:

* Background kernel compilation creates system load
* Tests system behavior under resource contention
* Validates cache allocation effectiveness under stress


Permission Errors
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Ensure proper Docker permissions
   sudo usermod -aG docker $USER
   # Restart Docker daemon if needed
   sudo systemctl restart docker

RDT Access Issues
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Verify RDT support
   cat /proc/cpuinfo | grep rdt
   # Check RDT mount
   mount | grep resctrl

Performance Anomalies
^^^^^^^^^^^^^^^^^^^^^

1. Check for competing processes on target cores
2. Verify cache allocation mask validity
3. Confirm real-time scheduler configuration
4. Monitor system thermal throttling


References
----------

* Intel RDT Technology Overview: `Intel Documentation <https://www.intel.com/content/www/us/en/architecture-and-technology/resource-director-technology.html>`_
* Linux Real-time Configuration Guide
* Intel ECI Benchmarking Documentation: `eci.intel.com <https://eci.intel.com>`_
* Container Security Best Practices
