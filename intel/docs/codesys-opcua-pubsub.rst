CODESYS OPC UA Pub/Sub Benchmark Documentation
==============================================

Overview
--------

The CODESYS OPC UA Pub/Sub Benchmark is a specialized communication performance benchmark designed to test OPC UA publisher/subscriber patterns for industrial IoT and automation scenarios. It evaluates real-time data communication performance between industrial devices and systems.

Purpose
-------

The OPC UA Pub/Sub Benchmark evaluates:

* OPC UA communication protocol performance
* Publisher/subscriber pattern efficiency
* Network latency and throughput in industrial contexts
* Real-time data exchange capabilities
* Communication system scalability
* Industrial protocol resilience under load

Technical Specifications
------------------------

Container Architecture
~~~~~~~~~~~~~~~~~~~~~~

:Publisher Container: ``codesys-opcua-server:latest``
:Subscriber Container: ``codesys-opcua-client:latest``
:Base Image: ``eci-base:latest``
:CODESYS Version: Control for Linux SL v4.5.0.0
:Communication Protocol: OPC UA with Pub/Sub extensions

Key Components
~~~~~~~~~~~~~~

OPC UA Server (Publisher)
^^^^^^^^^^^^^^^^^^^^^^^^^^

* Industrial data source simulation
* Real-time data publication
* Multiple client connection support
* Performance metric generation
* Network communication optimization

OPC UA Client (Subscriber)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Data subscription and consumption
* Latency measurement capabilities
* Throughput analysis
* Connection management
* Performance data collection

Communication Features
^^^^^^^^^^^^^^^^^^^^^^

* **Real-time Data Exchange**: High-frequency data updates
* **Subscription Management**: Dynamic subscription handling
* **Network Optimization**: Efficient data serialization
* **Quality of Service**: Configurable QoS parameters

Usage
-----

Basic Execution
~~~~~~~~~~~~~~~

.. code-block:: bash

   ./benchmarking.sh codesys-opcua-pubsub -l <cache_mask> -t <cores>

Parameters
~~~~~~~~~~

Required Parameters
^^^^^^^^^^^^^^^^^^^

* ``-l, --l3-cache-mask <mask>``: L3 cache allocation mask in hexadecimal format
* ``-t, --t-core <cores>``: Target CPU cores for client execution

Optional Parameters
^^^^^^^^^^^^^^^^^^^

* ``-s, --stressor``: Enable background stress testing

Examples
~~~~~~~~

Standard Communication Test
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Test OPC UA communication with specific resource allocation
   ./benchmarking.sh codesys-opcua-pubsub -l 0xffe -t 15

Multi-Core Communication
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Allocate multiple cores for high-throughput testing
   ./benchmarking.sh codesys-opcua-pubsub -l 0xffe -t 15,16

Under System Load
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Test communication performance under stress
   ./benchmarking.sh codesys-opcua-pubsub -l 0xffe -t 15 --stressor

Technical Implementation
------------------------

Execution Flow
~~~~~~~~~~~~~~

The benchmark follows this coordinated execution sequence:

1. **Server Startup**: Launch OPC UA server container
2. **Initialization Delay**: 10-second server startup wait
3. **Client Execution**: Start client with RDT resource allocation
4. **Data Exchange**: Perform publisher/subscriber communication test
5. **Metric Collection**: Gather performance data
6. **Cleanup**: Stop server container

Container Orchestration
~~~~~~~~~~~~~~~~~~~~~~~

Server Container Startup
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker run -d --rm --privileged \
     --name codesys-opcua-server \
     -p 4840:4840 \
     codesys-opcua-server:latest

Client Container Execution
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker run \
     -e L3_CACHE_MASK=${L3_CACHE_MASK} \
     -e T_CORE="${T_CORE}" \
     -p 8081:8080 \
     codesys-opcua-client:latest /docker-entrypoint.sh

RDT Integration
~~~~~~~~~~~~~~~

The client container uses Intel RDT for resource allocation:

* **Cache Allocation**: L3 cache partitioning for consistent performance
* **CPU Affinity**: Dedicated core assignment for communication tasks
* **Memory Bandwidth**: Optimal memory access patterns

Network Configuration
~~~~~~~~~~~~~~~~~~~~~

Port Allocation
^^^^^^^^^^^^^^^

* **Server OPC UA**: Port 4840 for OPC UA communication
* **Client Web Interface**: Port 8081 for monitoring and control
* **Internal Communication**: Docker network for container coordination

Communication Protocols
^^^^^^^^^^^^^^^^^^^^^^^^

* **OPC UA TCP**: Primary communication channel
* **HTTP/HTTPS**: Web-based monitoring and configuration
* **WebSocket**: Real-time data streaming (if configured)

Performance Metrics
--------------------

Measured Parameters
~~~~~~~~~~~~~~~~~~~

Communication Latency
^^^^^^^^^^^^^^^^^^^^^^

* **Round-trip Time**: Complete request/response cycle time
* **Publishing Latency**: Time from data generation to publication
* **Subscription Latency**: Time from publication to subscriber receipt
* **Network Propagation**: Pure network transmission delay

Throughput Metrics
^^^^^^^^^^^^^^^^^^^

* **Messages per Second**: Communication frequency capability
* **Data Rate**: Bytes per second transmission rate
* **Connection Throughput**: Simultaneous connection handling
* **Subscription Rate**: Variable update frequencies

Quality of Service
^^^^^^^^^^^^^^^^^^

* **Message Loss**: Percentage of lost communications
* **Out-of-Order Delivery**: Sequence integrity measurement
* **Duplicate Messages**: Communication protocol efficiency
* **Connection Reliability**: Connection stability metrics

Data Collection Methods
~~~~~~~~~~~~~~~~~~~~~~~

Real-time Monitoring
^^^^^^^^^^^^^^^^^^^^

* Continuous performance metric collection during test execution
* Live dashboard display through web interface
* Real-time alerting for performance threshold violations

Statistical Analysis
^^^^^^^^^^^^^^^^^^^^

* Latency distribution analysis
* Throughput trend analysis
* Performance correlation with system load
* Communication pattern optimization

System Requirements
-------------------

Hardware Requirements
~~~~~~~~~~~~~~~~~~~~~

* Intel processor with RDT support
* Multi-core CPU for concurrent server/client processing
* Network interface with sufficient bandwidth
* 8GB RAM minimum for realistic industrial simulation

Software Requirements
~~~~~~~~~~~~~~~~~~~~~

* Linux kernel with RDT support
* Docker with container networking
* Network connectivity between containers
* Port availability (4840, 8081)

Network Requirements
~~~~~~~~~~~~~~~~~~~~

* Container networking or host network mode
* Firewall configuration for OPC UA ports
* Sufficient bandwidth for high-throughput testing
* Low-latency network infrastructure (for accurate measurements)

Best Practices
--------------

System Preparation
~~~~~~~~~~~~~~~~~~

Network Optimization
^^^^^^^^^^^^^^^^^^^^

1. **Network Interface Tuning**: Optimize network stack parameters
2. **Interrupt Management**: Configure network interrupt affinity
3. **Buffer Configuration**: Optimize network buffer sizes
4. **QoS Setup**: Configure traffic prioritization

.. code-block:: bash

   # Network optimization examples
   echo 1 > /proc/sys/net/core/netdev_max_backlog
   echo 4096 > /proc/sys/net/core/netdev_budget

Container Networking
^^^^^^^^^^^^^^^^^^^^

1. **Network Mode Selection**: Choose appropriate Docker network mode
2. **DNS Configuration**: Ensure proper name resolution
3. **Port Management**: Avoid port conflicts
4. **Security Settings**: Configure appropriate network security

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~

Resource Allocation
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Separate cache allocation for server and client
   SERVER_CACHE_MASK=0xf0f    # Server cache allocation
   CLIENT_CACHE_MASK=0x0f0    # Client cache allocation

Core Assignment Strategy
^^^^^^^^^^^^^^^^^^^^^^^^

1. **NUMA Awareness**: Consider NUMA topology for network processing
2. **Interrupt Isolation**: Separate network interrupts from application cores
3. **Cache Topology**: Optimize for L3 cache sharing patterns
4. **Thermal Management**: Avoid thermal coupling between cores

Testing Methodology
~~~~~~~~~~~~~~~~~~~~

Baseline Establishment
^^^^^^^^^^^^^^^^^^^^^^

1. **Network Baseline**: Measure raw network performance
2. **Container Overhead**: Assess containerization impact
3. **Protocol Overhead**: Evaluate OPC UA protocol efficiency
4. **System Idle**: Establish idle system performance

Load Testing Scenarios
^^^^^^^^^^^^^^^^^^^^^^^

1. **Variable Message Rates**: Test different publication frequencies
2. **Multiple Subscribers**: Scale client connections
3. **Large Messages**: Test with various message sizes
4. **Burst Traffic**: Evaluate performance under traffic bursts

Industrial Scenarios
^^^^^^^^^^^^^^^^^^^^

1. **Sensor Data Simulation**: Simulate industrial sensor data patterns
2. **Control Commands**: Test command/response patterns
3. **Alarm Conditions**: Evaluate high-priority message handling
4. **Network Interruptions**: Test resilience to network issues

Integration with Other Benchmarks
----------------------------------

Complementary Testing
~~~~~~~~~~~~~~~~~~~~~

* **Cyclictest**: Correlate communication latency with kernel timing
* **CODESYS Jitter**: Compare with PLC runtime performance
* **Caterpillar**: Assess computational impact on communication
* **Network Benchmarks**: Validate network infrastructure performance

Industrial Validation
~~~~~~~~~~~~~~~~~~~~~~

1. **Real Device Testing**: Compare with actual industrial devices
2. **Protocol Compliance**: Validate OPC UA specification adherence
3. **Interoperability**: Test with different OPC UA implementations
4. **Scalability Assessment**: Evaluate performance with multiple devices

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

Connection Failures
^^^^^^^^^^^^^^^^^^^

**Symptoms**: Client cannot connect to OPC UA server

**Causes**:

* Network connectivity issues
* Port accessibility problems
* Container startup timing
* Firewall restrictions

**Solutions**:

.. code-block:: bash

   # Verify server startup
   docker logs codesys-opcua-server

   # Check port accessibility
   netstat -tlnp | grep 4840

   # Test network connectivity
   docker exec codesys-opcua-client ping codesys-opcua-server

Performance Degradation
^^^^^^^^^^^^^^^^^^^^^^^

**Symptoms**: High latency or low throughput

**Causes**:

* Insufficient cache allocation
* Network congestion
* CPU resource contention
* Memory pressure

**Solutions**:

.. code-block:: bash

   # Monitor network traffic
   iftop -i docker0

   # Check resource utilization
   docker stats

   # Verify RDT allocation
   cat /sys/fs/resctrl/*/schemata


Performance Profiling
^^^^^^^^^^^^^^^^^^^^^^

1. **Container Monitoring**: Use Docker stats and monitoring tools
2. **Resource Analysis**: Monitor CPU, memory, and network utilization
3. **Cache Performance**: Use Intel tools for cache analysis
4. **System Tracing**: Use kernel tracing for detailed analysis

Load Distribution
^^^^^^^^^^^^^^^^^

1. **Client Isolation**: Separate resource allocation per client
2. **Network Load Balancing**: Distribute network load
3. **Subscription Management**: Optimize subscription patterns
4. **Resource Monitoring**: Monitor aggregate resource usage


Cross-Platform Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test with different container configurations
   docker run --privileged --network host \
     codesys-opcua-server:latest &

   ./benchmarking.sh codesys-opcua-pubsub -l 0xffe -t 15

References
----------

* OPC Foundation Specifications: `opcfoundation.org <https://opcfoundation.org>`_
* CODESYS OPC UA Documentation: `codesys.com <https://www.codesys.com>`_
* Industrial Communication Standards: IEC 62541 (OPC UA)
* Real-time Communication Guide: IEEE 802.1 Time-Sensitive Networking
* Intel RDT Programming Guide
* Docker Networking Best Practices
* Intel ECI Documentation: `eci.intel.com <https://eci.intel.com>`_
