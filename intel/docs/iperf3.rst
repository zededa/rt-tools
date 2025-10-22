CODESYS OPC UA Pub/Sub Benchmark Documentation
==============================================

Overview
--------

The Iperf3 Benchmark measures maximum bandwidth over IP network by instantiating a client and server to send data between over the network.

Purpose
-------

The Iperf3 Benchmark evaluates:

* IP network performance

Technical Specifications
------------------------

Container Architecture
~~~~~~~~~~~~~~~~~~~~~~

:Server Container: ``iperf-server:latest``
:Client Container: ``iperf:latest``
:Base Image: ``eci-base:latest``
:Iperf3 for Linux

Key Components
~~~~~~~~~~~~~~

Iperf3 Server
^^^^^^^^^^^^^^^^^^^^^^^^^^

* Recieves data over network (by default)

Iperf 3 Client
^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Sends data over network (by default)

Usage
-----

Basic Execution
~~~~~~~~~~~~~~~

.. code-block:: bash

   ./benchmarking.sh iperf3 -l <cache_mask> -t <cores>

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

   # Test Iperf3 communication with specific resource allocation
   ./benchmarking.sh iperf3 -l 0xffe -t 15

Multi-Core Communication
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Allocate multiple cores for high-throughput testing
   ./benchmarking.sh iperf3 -l 0xffe -t 15,16

Under System Load
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Test communication performance under stress
   ./benchmarking.sh iperf3 -l 0xffe -t 15 --stressor

Technical Implementation
------------------------

Execution Flow
~~~~~~~~~~~~~~

The benchmark follows this coordinated execution sequence:

1. **Server Startup**: Launch Iperf3 server container
2. **Initialization Delay**: 5-second server startup wait
3. **Client Execution**: Start client with RDT resource allocation
4. **Data Exchange**: Perform basic network speed test
5. **Metric Collection**: Gather performance data
6. **Cleanup**: Stop server container

Container Orchestration
~~~~~~~~~~~~~~~~~~~~~~~

Server Container Startup
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash
   docker run -d --rm --privileged \
     --name iperf3-server \
     -p 5201:5201 \
     iperf3-server:latest \
     -s

Client Container Execution
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Get iperf3 Server IP ADDRESS:
   SERVER_IP_ADDRESS=$(docker inspect --format "{{ .NetworkSettings.IPAddress }}" iperf3-server)

   docker run --it --rm \
     -e L3_CACHE_MASK=${L3_CACHE_MASK} \
     -e T_CORE="${T_CORE}" \
     iperf3:latest \
     -c ${SERVER_IP_ADDRESS}

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

* **Default Server Port**: Port 5201 for data exchange

Communication Protocols
^^^^^^^^^^^^^^^^^^^^^^^^

* **TCP**: Primary communication channel
* **UDP/SCTP**: Additional communication channels

Performance Metrics
--------------------

Measured Parameters
~~~~~~~~~~~~~~~~~~~

Throughput Metrics
^^^^^^^^^^^^^^^^^^^

* **Data Rate**: Gbits per second transmission rate

Quality of Service
^^^^^^^^^^^^^^^^^^

* **Data Transmission**: Total data sent/received

Data Collection Methods
~~~~~~~~~~~~~~~~~~~~~~~

Real-time Monitoring
^^^^^^^^^^^^^^^^^^^^

* Continuous performance metric collection during test execution

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
* Port availability (5201)

Network Requirements
~~~~~~~~~~~~~~~~~~~~

* Container networking or host network mode
* Firewall configuration for Iperf3 ports
* Sufficient bandwidth for high-throughput testing
* Low-latency network infrastructure (for accurate measurements)

References
----------

* iperf3 man page: `software.es.net/iperf <https://software.es.net/iperf/invoking.html#iperf3-manual-page>`_
