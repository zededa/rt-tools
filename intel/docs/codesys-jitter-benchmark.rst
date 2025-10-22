CODESYS Jitter Benchmark Documentation
======================================

Overview
--------

The CODESYS Jitter Benchmark is an industrial automation runtime benchmark designed to test CODESYS Control performance and jitter characteristics in real-time industrial applications. It provides comprehensive testing of PLC (Programmable Logic Controller) runtime behavior, timing characteristics, and industrial communication protocols.

Purpose
-------

The CODESYS Jitter Benchmark evaluates:

* Industrial automation runtime performance
* PLC cycle time consistency and jitter
* Real-time task scheduling in industrial contexts
* OPC UA server performance under load
* Web-based HMI (Human Machine Interface) responsiveness
* System behavior under industrial workload patterns

Technical Specifications
------------------------

Container Details
~~~~~~~~~~~~~~~~~

:Base Image: ``eci-base:latest``
:Container Name: ``codesys-jitter-benchmark:latest``
:CODESYS Version: Control for Linux SL v3.5.18.20
:PlcLogic Version: v4.11.0.0 (benchmark application)
:Runtime: Complete CODESYS Control runtime environment

Key Components
~~~~~~~~~~~~~~

CODESYS Control Runtime
^^^^^^^^^^^^^^^^^^^^^^^

* Full industrial automation runtime
* Multi-core support (64 cores detected)
* Real-time task scheduler
* Integrated safety functions
* Communication protocol stack

PlcLogic Benchmark Application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Specialized benchmark logic for performance testing
* Configurable cycle times and workload patterns
* Performance metric collection
* Jitter measurement and analysis

Communication Interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^

* **OPC UA Server**: Port 4840 for industrial communication
* **Web Server**: Port 8080 for visualization and HMI
* **Visualization Server**: Real-time data visualization

Intel RDT Integration
^^^^^^^^^^^^^^^^^^^^^

* Cache allocation for deterministic performance
* CPU affinity for isolated execution
* Memory bandwidth allocation

Usage
-----

Basic Execution
~~~~~~~~~~~~~~~

.. code-block:: bash

   ./benchmarking.sh codesys-jitter-benchmark -l <cache_mask> -t <cores>

Parameters
~~~~~~~~~~

Required Parameters
^^^^^^^^^^^^^^^^^^^

* ``-l, --l3-cache-mask <mask>``: L3 cache allocation mask in hexadecimal format
* ``-t, --t-core <cores>``: Target CPU cores for execution

Optional Parameters
^^^^^^^^^^^^^^^^^^^

* ``-s, --stressor``: Enable background stress testing

Examples
~~~~~~~~

Single Core Execution
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Run CODESYS benchmark on core 15
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 15

Multi-Core Execution
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Allocate multiple cores for complex automation tasks
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 15,16,17

With Background Stress
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Test under system load conditions
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 15 --stressor

Technical Implementation
------------------------

Container Startup Process
~~~~~~~~~~~~~~~~~~~~~~~~~

The benchmark follows this initialization sequence:

1. **Environment Setup**: Configure RDT environment variables
2. **Resource Allocation**: Apply Intel RDT cache and CPU settings
3. **CODESYS Startup**: Initialize CODESYS Control runtime
4. **Application Loading**: Deploy PlcLogic benchmark application
5. **Service Activation**: Start OPC UA and web servers
6. **Performance Monitoring**: Begin metric collection

Docker Command Structure
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   docker run -p 8080:8080 \
     -e DEBUGOUTPUT=1 \
     -e DEBUGLOGFILE=/tmp/codesyscontrol_debug.log \
     -e L3_CACHE_MASK=${L3_CACHE_MASK} \
     -e T_CORE="${T_CORE}" \
     -d codesys-jitter-benchmark:latest /docker-entrypoint.sh

RDT Integration Process
~~~~~~~~~~~~~~~~~~~~~~~

The container integrates Intel RDT through the startup script:

.. code-block:: bash

   # Apply RDT resource allocation
   rdtset -r "${T_CORE}" -c "${T_CORE}" -p 1

   # Start CODESYS with preserved environment
   export L3_CACHE_MASK="${L3_CACHE_MASK}"
   export T_CORE="${T_CORE}"
   /etc/init.d/codesyscontrol start

Configuration Files
~~~~~~~~~~~~~~~~~~~

CODESYSControl.cfg (Main Configuration)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Runtime component configuration
* Task scheduler settings
* Communication protocol parameters
* Safety system configuration

CODESYSControl_User.cfg (User Settings)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Web server configuration (``Port.HTTP=8080``)
* Visualization server settings (``Port=8080``)
* User-specific runtime parameters
* Performance tuning options

Performance Metrics
--------------------

Measured Parameters
~~~~~~~~~~~~~~~~~~~

Timing Characteristics
^^^^^^^^^^^^^^^^^^^^^^

* **Cycle Time**: PLC program execution cycle duration
* **Jitter**: Variation in cycle time execution
* **Task Latency**: Response time for real-time tasks
* **Interrupt Handling**: Interrupt response characteristics

Industrial Communication
^^^^^^^^^^^^^^^^^^^^^^^^^

* **OPC UA Performance**: Server response times and throughput
* **Client Connection Handling**: Multiple client support
* **Data Exchange Rates**: Variable update frequencies
* **Network Latency**: Communication delay measurements

System Resources
^^^^^^^^^^^^^^^^

* **CPU Utilization**: Runtime CPU consumption patterns
* **Memory Usage**: Dynamic memory allocation behavior
* **Cache Performance**: L3 cache utilization with RDT
* **I/O Performance**: Input/output processing rates

Output and Monitoring
~~~~~~~~~~~~~~~~~~~~~

Web Interface Access
^^^^^^^^^^^^^^^^^^^^

:URL: ``http://<host_ip>:8080``
:Features:
  * Real-time variable monitoring
  * Performance dashboards
  * System status displays
  * Configuration interfaces

OPC UA Endpoint
^^^^^^^^^^^^^^^

:Endpoint: ``opc.tcp://<container_name>:4840``
:Features:
  * Industrial data access
  * Real-time subscriptions
  * Method invocation
  * Event notifications

Log Files
^^^^^^^^^

* **Runtime Logs**: ``/tmp/codesyscontrol.log``
* **Debug Logs**: ``/tmp/codesyscontrol_debug.log`` (when enabled)
* **Application Logs**: PlcLogic-specific performance data

System Requirements
-------------------

Hardware Requirements
~~~~~~~~~~~~~~~~~~~~~

* Intel processor with RDT support
* Multi-core CPU (minimum 4 cores recommended)
* 8GB RAM minimum (16GB recommended for complex applications)
* Network interface for communication testing

Software Requirements
~~~~~~~~~~~~~~~~~~~~~

* Linux kernel with RDT support
* Docker with privileged container support
* Intel CMT-CAT tools
* Network access for web interface testing

Network Configuration
~~~~~~~~~~~~~~~~~~~~~

* Port 8080: Web server and visualization
* Port 4840: OPC UA server communication
* Container networking or host network mode

Best Practices
--------------

System Preparation
~~~~~~~~~~~~~~~~~~

Industrial Real-time Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Kernel Tuning**: Use real-time kernel (PREEMPT_RT)
2. **CPU Isolation**: Dedicate cores for industrial tasks
3. **Interrupt Management**: Route interrupts away from PLC cores
4. **Memory Allocation**: Use locked memory for deterministic behavior

Network Optimization
^^^^^^^^^^^^^^^^^^^^

1. **Network Isolation**: Separate industrial and administrative networks
2. **QoS Configuration**: Prioritize industrial communication traffic
3. **Firewall Settings**: Configure for OPC UA and web access
4. **Bandwidth Management**: Ensure adequate bandwidth for visualization

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~

Cache Allocation Strategy
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Calculate cache allocation for industrial workloads
   # Example: 50% cache allocation for 16-way associative cache
   L3_CACHE_MASK=0xff  # 8 ways out of 16

Core Assignment
^^^^^^^^^^^^^^^

1. **NUMA Awareness**: Consider NUMA topology for core selection
2. **Thermal Considerations**: Avoid thermally coupled cores
3. **Interrupt Isolation**: Separate interrupt handling from PLC execution
4. **Communication Cores**: Dedicate cores for network processing

Testing Methodology
~~~~~~~~~~~~~~~~~~~~

Baseline Performance
^^^^^^^^^^^^^^^^^^^^

1. **Idle System**: Measure with minimal background activity
2. **Standard Configuration**: Test with default CODESYS settings
3. **Resource Monitoring**: Establish baseline resource consumption

Load Testing
^^^^^^^^^^^^

1. **Variable Load**: Test with different PLC program complexities
2. **Communication Load**: Vary OPC UA client connections
3. **Visualization Load**: Test with multiple web clients
4. **Background Stress**: Use stressor for realistic conditions

Industrial Scenarios
^^^^^^^^^^^^^^^^^^^^

1. **Rapid I/O**: Simulate high-frequency input/output operations
2. **Communication Bursts**: Test with burst communication patterns
3. **Safety Functions**: Validate safety-related timing requirements
4. **HMI Interaction**: Test human-machine interface responsiveness

Integration with Other Benchmarks
----------------------------------

Complementary Testing
~~~~~~~~~~~~~~~~~~~~~

* **Cyclictest**: Compare PLC timing with kernel timer latency
* **Caterpillar**: Validate computational performance correlation
* **OPC UA Pub/Sub**: Test communication protocol performance
* **Network Benchmarks**: Assess communication infrastructure impact

Industrial Validation
~~~~~~~~~~~~~~~~~~~~~~

* Compare results with actual PLC hardware performance
* Validate against industrial timing requirements (IEC 61131-3)
* Cross-reference with safety system specifications
* Assess scalability for multiple PLC instances

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

Visualization Server Not Starting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Symptoms**: Web interface not accessible, no visualization server in logs

**Cause**: Missing or incorrect visualization configuration

**Solution**:

.. code-block:: bash

   # Verify configuration in CODESYSControl_User.cfg
   [SysTarget]
   Port.HTTP=8080

   [CmpVisuServer]  
   Port=8080

OPC UA Connection Issues
^^^^^^^^^^^^^^^^^^^^^^^^

**Symptoms**: OPC UA clients cannot connect

**Cause**: Network configuration or certificate issues

**Solutions**:

1. Verify port 4840 accessibility
2. Check container networking configuration
3. Review OPC UA security settings

Poor Performance/High Jitter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Symptoms**: Inconsistent cycle times, high jitter values

**Causes**:

* Insufficient cache allocation
* CPU core contention
* Background system activity
* Thermal throttling

**Solutions**:

.. code-block:: bash

   # Check CPU isolation
   cat /sys/devices/system/cpu/isolated

   # Verify RDT allocation
   cat /sys/fs/resctrl/*/cpus
   cat /sys/fs/resctrl/*/schemata

   # Monitor thermal status
   sensors

Container Startup Failures
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Symptoms**: Container exits immediately or fails to start CODESYS

**Cause**: Missing privileges or resource access

**Solution**:

.. code-block:: bash

   # Verify container privileges
   docker run --privileged --rm codesys-jitter-benchmark:latest \
     cat /proc/1/status | grep Cap

   # Check RDT mount
   docker run --privileged --rm \
     -v /sys/fs/resctrl:/sys/fs/resctrl \
     codesys-jitter-benchmark:latest ls -la /sys/fs/resctrl

Debug Procedures
~~~~~~~~~~~~~~~~

Enable Debug Logging
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Set debug environment variables
   export DEBUGOUTPUT=1
   export DEBUGLOGFILE=/tmp/codesyscontrol_debug.log

Performance Analysis
^^^^^^^^^^^^^^^^^^^^

1. **Log Analysis**: Review CODESYS runtime logs for timing information
2. **Resource Monitoring**: Use container monitoring tools
3. **Network Analysis**: Monitor OPC UA communication patterns
4. **Cache Analysis**: Use Intel tools to analyze cache performance
-
Application Development
^^^^^^^^^^^^^^^^^^^^^^^

1. **CODESYS Development Environment**: Use CODESYS IDE for custom applications
2. **Performance Instrumentation**: Add timing measurement code
3. **Variable Mapping**: Configure OPC UA variable exposure
4. **Visualization Elements**: Create custom HMI screens



Container Orchestration
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Run multiple CODESYS instances
   for i in {1..4}; do
     docker run -d --name codesys-$i \
       -p $((8080+i)):8080 \
       -p $((4840+i)):4840 \
       -e L3_CACHE_MASK=${CACHE_MASK} \
       -e T_CORE="$((15+i))" \
       codesys-jitter-benchmark:latest
   done


Industrial IoT Pipeline
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # 1. Start OPC UA data collection
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 15

   # 2. Test communication performance
   ./benchmarking.sh codesys-opcua-pubsub -l 0xf0f -t 16

   # 3. Validate system under load
   ./benchmarking.sh cyclictest -l 0x0f0 -t 17 --stressor


References
----------

* CODESYS Documentation: `codesys.com <https://www.codesys.com>`_
* IEC 61131-3 Standard: Industrial Programming Languages
* OPC UA Specification: `opcfoundation.org <https://opcfoundation.org>`_
* Intel RDT Technology Guide
* Linux Real-time Programming Guide
* Intel ECI Documentation: `eci.intel.com <https://eci.intel.com>`_
