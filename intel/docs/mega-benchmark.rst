Mega Benchmark Documentation
============================

Overview
--------

The Mega Benchmark is a comprehensive long-duration (48-hour) stability and performance testing suite designed for extended system validation under continuous load. It integrates multiple benchmarking tools and provides automated testing for production readiness assessment.

Purpose
-------

The Mega Benchmark evaluates:

* Long-term system stability and reliability
* Performance consistency over extended periods
* Thermal behavior under sustained load
* Memory leak detection and resource management
* System degradation patterns
* Production environment readiness

Technical Specifications
------------------------

Container Details
~~~~~~~~~~~~~~~~~

:Base Image: ``eci-base:latest``
:Container Name: ``mega-benchmark:latest``
:Source: Intel ECI realtime benchmarking package (``eci-realtime-benchmarking``)
:Duration: 48 hours continuous execution
:Runtime: Automated test orchestration with multiple benchmark integration

Key Components
~~~~~~~~~~~~~~

Integrated Benchmarks
^^^^^^^^^^^^^^^^^^^^^^

* Multiple real-time testing tools
* System stress generators
* Performance monitoring utilities
* Resource utilization trackers
* Automated result collection and analysis

Test Orchestration
^^^^^^^^^^^^^^^^^^

* **48-hour Test Script**: ``/opt/benchmarking/mega-benchmark/48_hour_benchmark.sh``
* **Automated Scheduling**: Coordinated test execution
* **Continuous Monitoring**: Real-time performance tracking
* **Result Aggregation**: Comprehensive data collection
* **Failure Detection**: Automated anomaly detection

Monitoring Capabilities
^^^^^^^^^^^^^^^^^^^^^^^

* System resource utilization tracking
* Performance metric collection
* Thermal monitoring integration
* Error detection and logging
* Trend analysis and reporting

Usage
-----

Build Configuration
~~~~~~~~~~~~~~~~~~~

The Mega Benchmark is automatically built during the standard build process:

.. code-block:: bash

   ./benchmarking.sh build

Direct Container Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   docker run -it --privileged --rm \
     --name mega-benchmark \
     --cpuset-cpus=<cores> \
     -v /sys/fs/resctrl:/sys/fs/resctrl \
     -v /dev/cpu_dma_latency:/dev/cpu_dma_latency \
     --cap-add=SYS_NICE --cap-add=IPC_LOCK \
     mega-benchmark:latest

Manual Script Execution
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Execute the 48-hour benchmark script directly
   docker exec -it mega-benchmark /opt/benchmarking/mega-benchmark/48_hour_benchmark.sh

Technical Implementation
------------------------

Container Configuration
~~~~~~~~~~~~~~~~~~~~~~~

Dockerfile Structure
^^^^^^^^^^^^^^^^^^^^

.. code-block:: dockerfile

   FROM eci-base:latest

   # Install comprehensive benchmarking suite
   RUN apt-get update && apt-get install -y --allow-downgrades eci-realtime-benchmarking

   # Set execution permissions
   RUN chmod +x /opt/benchmarking/mega-benchmark/48_hour_benchmark.sh

   # Default command for 48-hour execution
   CMD [ "/opt/benchmarking/mega-benchmark/48_hour_benchmark.sh" ]

Required Privileges
^^^^^^^^^^^^^^^^^^^

* **Privileged Mode**: Full system access for comprehensive testing
* **Resource Access**: Direct hardware performance counter access
* **Scheduling Control**: Real-time process scheduling capabilities
* **Resource Director Technology**: Intel RDT for cache and memory control

Container Capabilities
^^^^^^^^^^^^^^^^^^^^^^

* **CAP_SYS_NICE**: Real-time scheduling permissions
* **CAP_IPC_LOCK**: Memory locking capabilities
* **CAP_SYS_ADMIN**: System administration for comprehensive testing
* **CAP_NET_ADMIN**: Network configuration for communication tests

Test Execution Framework
~~~~~~~~~~~~~~~~~~~~~~~~~

48-Hour Test Phases
^^^^^^^^^^^^^^^^^^^

**Phase 1: System Baseline (Hours 0-4)**

* Initial system characterization
* Baseline performance measurement
* Resource utilization mapping
* Thermal profile establishment

**Phase 2: Standard Load Testing (Hours 4-20)**

* Continuous real-time workload execution
* Multiple benchmark parallel execution
* Resource contention testing
* Performance stability validation

**Phase 3: Stress Testing (Hours 20-36)**

* Maximum system load application
* Thermal stress validation
* Resource exhaustion testing
* Failure mode analysis

**Phase 4: Recovery and Stability (Hours 36-48)**

* System recovery validation
* Long-term stability confirmation
* Resource leak detection
* Performance consistency verification

Integrated Test Components
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Real-time Performance Tests**

* Cyclictest for timer latency measurement
* Task scheduling consistency verification
* Interrupt handling performance assessment
* Priority inversion detection

**Computational Load Tests**

* CPU-intensive workload generation
* Memory allocation and deallocation patterns
* Cache performance under sustained load
* Multi-core coordination testing

**I/O Performance Tests**

* Disk I/O performance measurement
* Network throughput and latency testing
* Memory bandwidth utilization
* Resource contention analysis

**System Stability Tests**

* Memory leak detection
* Resource exhaustion recovery
* Thermal throttling behavior
* Error condition handling

Performance Metrics
--------------------

Measured Parameters
~~~~~~~~~~~~~~~~~~~

System Performance
^^^^^^^^^^^^^^^^^^

* **CPU Utilization**: Per-core utilization patterns over 48 hours
* **Memory Usage**: RAM consumption trends and leak detection
* **I/O Performance**: Disk and network throughput consistency
* **Cache Performance**: L1, L2, L3 cache efficiency over time

Real-time Characteristics
^^^^^^^^^^^^^^^^^^^^^^^^^

* **Latency Trends**: Timer and scheduling latency evolution
* **Jitter Analysis**: Performance consistency measurement
* **Deadline Adherence**: Real-time constraint compliance
* **Priority Handling**: Real-time priority effectiveness

Thermal Behavior
^^^^^^^^^^^^^^^^

* **Temperature Monitoring**: CPU and system temperature tracking
* **Throttling Events**: Thermal throttling frequency and impact
* **Cooling Efficiency**: System thermal management effectiveness
* **Performance Impact**: Temperature effect on performance

Reliability Metrics
^^^^^^^^^^^^^^^^^^^

* **Error Rates**: System error frequency and types
* **Recovery Time**: System recovery from stress conditions
* **Stability Index**: Overall system stability measurement
* **Degradation Patterns**: Performance degradation over time

Data Collection and Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Continuous Monitoring
^^^^^^^^^^^^^^^^^^^^^

* Real-time metric collection every second
* Automated anomaly detection and alerting
* Performance trend analysis
* Resource utilization tracking

Statistical Analysis
^^^^^^^^^^^^^^^^^^^^

* Long-term performance trend calculation
* Statistical stability measurement
* Confidence interval determination
* Outlier detection and analysis

Report Generation
^^^^^^^^^^^^^^^^^

* Comprehensive 48-hour performance report
* Graphical trend visualization
* Summary statistics and recommendations
* Comparative analysis with baseline systems

System Requirements
-------------------

Hardware Requirements
~~~~~~~~~~~~~~~~~~~~~

* **Multi-core Processor**: Minimum 8 cores recommended for comprehensive testing
* **Memory**: 16GB RAM minimum (32GB recommended for realistic industrial loads)
* **Storage**: 100GB available space for log files and test data
* **Cooling**: Adequate thermal management for 48-hour sustained load
* **Intel RDT Support**: For cache allocation and resource management testing

Software Requirements
~~~~~~~~~~~~~~~~~~~~~

* **Linux Kernel**: Real-time kernel (PREEMPT_RT) recommended
* **Docker**: Latest stable version with privileged container support
* **System Monitoring**: Integration with system monitoring tools
* **Storage**: Sufficient disk space for 48 hours of detailed logging


Best Practices
--------------

Pre-Test Preparation
~~~~~~~~~~~~~~~~~~~~

System Configuration
^^^^^^^^^^^^^^^^^^^^

1. **Thermal Management**: Ensure adequate cooling for sustained load
2. **Resource Allocation**: Plan CPU and memory allocation strategy
3. **Storage Space**: Verify sufficient disk space for logs
4. **Monitoring Setup**: Configure external monitoring systems

Baseline Measurement
^^^^^^^^^^^^^^^^^^^^

1. **System Idle**: Measure idle system performance
2. **Short Duration**: Run shorter tests for baseline establishment
3. **Component Testing**: Validate individual components
4. **Environment Validation**: Confirm test environment stability


Post-Test Analysis
~~~~~~~~~~~~~~~~~~

Data Collection
^^^^^^^^^^^^^^^

1. **Log Aggregation**: Collect all test logs and metrics
2. **System State**: Capture final system state information
3. **Performance Summary**: Generate comprehensive performance summary
4. **Comparison Analysis**: Compare with previous test runs

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

Premature Test Termination
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Symptoms**: Test stops before 48-hour completion

**Causes**:

* System resource exhaustion
* Thermal protection activation
* Container resource limits
* Host system instability

**Solutions**:

.. code-block:: bash

   # Check system resources
   free -h
   df -h
   cat /proc/loadavg

   # Monitor thermal status
   sensors
   cat /sys/class/thermal/thermal_zone*/temp

   # Verify container limits
   docker inspect mega-benchmark | grep -i memory

Performance Degradation
^^^^^^^^^^^^^^^^^^^^^^^

**Symptoms**: Significant performance decline during test

**Causes**:

* Memory leaks in test components
* Thermal throttling
* Resource fragmentation
* Storage I/O bottlenecks

**Diagnostics**:

.. code-block:: bash

   # Memory analysis
   cat /proc/meminfo
   vmstat 1

   # I/O analysis
   iostat -x 1

   # Process analysis
   top -p $(pgrep mega-benchmark)


References
----------

* Intel ECI Real-time Benchmarking Guide: `eci.intel.com <https://eci.intel.com>`_
* Long-duration Testing Best Practices
* System Reliability Engineering Guidelines
* Linux Performance Monitoring and Analysis
* Docker Container Resource Management
* Thermal Management for Sustained Computing Loads
