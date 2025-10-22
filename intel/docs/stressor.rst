Stressor Documentation
======================

Overview
--------

The Stressor is a background stress generation tool designed for testing system behavior under realistic load conditions. It provides sustained computational, memory, and I/O stress through continuous Linux kernel compilation, simulating real-world background activity during benchmark testing.

Purpose
-------

The Stressor evaluates:

* System performance under realistic background load
* Resource contention impact on benchmarks
* Cache allocation effectiveness under stress
* System stability during sustained computational load
* Multi-core performance scaling under stress
* Real-time constraint adherence with background activity

Technical Specifications
------------------------

Container Details
~~~~~~~~~~~~~~~~~

:Base Image: ``ubuntu:latest``
:Container Name: ``stressor:latest``
:Source: Custom Linux kernel compilation stress
:Runtime: Continuous background kernel build process
:Resource Impact: CPU, memory, and I/O intensive workload

Key Components
~~~~~~~~~~~~~~

Linux Kernel Source
^^^^^^^^^^^^^^^^^^^

* Complete Linux kernel source tree
* Git clone from official Linus Torvalds repository
* Continuous compilation cycle
* Multi-core parallel build execution

Build Tools
^^^^^^^^^^^

* **build-essential**: Complete compilation toolchain
* **libncurses-dev**: Development libraries
* **flex/bison**: Parser generators
* **libssl-dev**: SSL development libraries
* **elfutils**: ELF file utilities
* **pahole**: BTF type information tool

Stress Generation
^^^^^^^^^^^^^^^^^

* **CPU Stress**: Parallel compilation across all available cores
* **Memory Stress**: Large compilation memory requirements
* **I/O Stress**: Continuous file system operations
* **Cache Pressure**: High cache allocation requirements

Usage
-----

Automatic Integration
~~~~~~~~~~~~~~~~~~~~~

The stressor is automatically integrated when using the ``--stressor`` flag with any benchmark:

.. code-block:: bash

   ./benchmarking.sh <benchmark> -l <cache_mask> -t <cores> --stressor

Manual Execution
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Start stressor container directly
   docker run -d --rm --name stressor stressor:latest

   # Stop stressor when done
   docker stop stressor

Integration Examples
~~~~~~~~~~~~~~~~~~~~

With Cyclictest
^^^^^^^^^^^^^^^

.. code-block:: bash

   # Test timer latency under kernel compilation stress
   ./benchmarking.sh cyclictest -l 0xffe -t 15 --stressor

With Caterpillar
^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Test computational performance under background load
   ./benchmarking.sh caterpillar -l 0xffe -t 16 --stressor

With CODESYS
^^^^^^^^^^^^

.. code-block:: bash

   # Test industrial automation under system stress
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 17 --stressor

Technical Implementation
------------------------

Container Architecture
~~~~~~~~~~~~~~~~~~~~~~

Dockerfile Structure
^^^^^^^^^^^^^^^^^^^^

.. code-block:: dockerfile

   FROM ubuntu:latest

   # Install build dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       libncurses-dev \
       flex \
       bison \
       libssl-dev \
       elfutils \
       pahole \
       git

   # Clone Linux kernel source
   RUN git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git

   # Set working directory
   WORKDIR /linux

   # Configure kernel build
   RUN make defconfig

   # Copy build script
   COPY build-kernel.sh .

   # Default command
   CMD ["/bin/sh", "build-kernel.sh"]

Build Script Implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``build-kernel.sh`` script provides continuous stress generation:

.. code-block:: bash

   #!/bin/sh
   
   # Continuous kernel compilation loop
   while true; do
       echo "Starting kernel compilation cycle..."
       
       # Clean previous build
       make clean
       
       # Parallel compilation using all available cores
       make -j $(nproc)
       
       echo "Kernel compilation cycle completed"
       
       # Brief pause before next cycle
       sleep 5
   done

Stress Characteristics
~~~~~~~~~~~~~~~~~~~~~~

CPU Utilization
^^^^^^^^^^^^^^^

* **Multi-core Load**: Utilizes all available CPU cores
* **Sustained Activity**: Continuous compilation cycles
* **Variable Load**: Compilation phases create varying CPU demands
* **Context Switching**: High process and thread activity

Memory Pressure
^^^^^^^^^^^^^^^

* **Compilation Memory**: Large memory requirements for linking
* **Buffer Cache**: Extensive file system caching
* **Dynamic Allocation**: Frequent memory allocation/deallocation
* **Memory Fragmentation**: Creates realistic memory pressure

I/O Activity
^^^^^^^^^^^^

* **File System Operations**: Continuous read/write operations
* **Disk Throughput**: High sequential and random I/O
* **Metadata Operations**: Frequent file creation/deletion
* **Cache Invalidation**: Impacts system cache behavior

Cache Behavior
^^^^^^^^^^^^^^

* **L1/L2/L3 Pressure**: High cache allocation demands
* **Cache Misses**: Creates realistic cache contention
* **Memory Bandwidth**: Sustained memory subsystem utilization
* **TLB Pressure**: Translation lookaside buffer stress

System Requirements
-------------------

Hardware Requirements
~~~~~~~~~~~~~~~~~~~~~

* **Multi-core CPU**: More cores provide increased stress
* **Memory**: 4GB minimum (8GB recommended for effective stress)
* **Storage**: 20GB available space for kernel source and builds
* **I/O Subsystem**: SSD recommended for realistic I/O patterns

Software Requirements
~~~~~~~~~~~~~~~~~~~~~

* **Docker**: Container runtime support
* **Linux Kernel**: Host kernel compatibility
* **File System**: Sufficient space and performance
* **Resource Availability**: Cores available for background stress

Container Resources
~~~~~~~~~~~~~~~~~~~

* **CPU Access**: No CPU limitations for maximum stress
* **Memory Access**: Unrestricted memory allocation
* **Storage Access**: Bind mount or volume for build artifacts
* **Network Access**: Internet connectivity for kernel source updates

Best Practices
--------------

Integration Strategy
~~~~~~~~~~~~~~~~~~~~

Resource Isolation
^^^^^^^^^^^^^^^^^^

1. **Core Separation**: Run stressor on different cores than benchmarks
2. **NUMA Awareness**: Consider NUMA topology for resource placement
3. **Cache Partitioning**: Use Intel RDT for cache isolation
4. **Memory Allocation**: Separate memory regions when possible


Container Management
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Check stressor status
   docker ps --filter name=stressor

   # Monitor stressor resource usage
   docker stats stressor

   # View stressor logs
   docker logs stressor

   # Stop stressor
   docker stop stressor

System Impact Monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Monitor CPU utilization
   top -p $(docker inspect --format '{{.State.Pid}}' stressor)

   # Monitor I/O activity
   iostat -x 1

   # Monitor memory usage
   free -h && cat /proc/meminfo


References
----------

* Linux Kernel Development Guide
* Docker Resource Management Documentation
* System Load Testing Best Practices
* Intel RDT Resource Isolation Guide
* Performance Testing Methodologies
* Intel ECI Documentation: `eci.intel.com <https://eci.intel.com>`_
