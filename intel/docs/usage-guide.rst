Intel ECI Benchmarking Suite Usage Guide
=========================================

Quick Start
-----------

1. Build All Benchmarks
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   ./benchmarking.sh build

2. Run Basic Tests
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test timer latency
   ./benchmarking.sh cyclictest -l 0xffe -t 15

   # Test computational performance  
   ./benchmarking.sh caterpillar -l 0xffe -t 16

   # Test industrial automation
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 17

3. Run with Background Stress
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   ./benchmarking.sh cyclictest -l 0xffe -t 15 --stressor

Command Reference
-----------------

Build Command
~~~~~~~~~~~~~

.. code-block:: bash

   ./benchmarking.sh build

Builds all benchmark containers including base images and dependencies.

Benchmark Execution
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   ./benchmarking.sh <benchmark> -l <cache_mask> -t <cores> [--stressor]

Required Parameters
^^^^^^^^^^^^^^^^^^^

* ``<benchmark>``: One of ``caterpillar``, ``cyclictest``, ``codesys-jitter-benchmark``, ``codesys-opcua-pubsub``
* ``-l, --l3-cache-mask <mask>``: L3 cache allocation mask (hex format)
* ``-t, --t-core <cores>``: Target CPU cores (single or comma-separated)

Optional Parameters
^^^^^^^^^^^^^^^^^^^

* ``-s, --stressor``: Enable background stress testing

Cache Allocation Guide
----------------------

Understanding Cache Masks
~~~~~~~~~~~~~~~~~~~~~~~~~~

Intel RDT uses bitmasks to allocate L3 cache portions:

.. code-block:: bash

   # Example for 16-way associative cache:
   0xffff  # All 16 ways (100% allocation)
   0xfff0  # Ways 4-15 (75% allocation) 
   0x0fff  # Ways 0-11 (75% allocation)
   0xff00  # Ways 8-15 (50% allocation)
   0x00ff  # Ways 0-7 (50% allocation)

Recommended Allocations
~~~~~~~~~~~~~~~~~~~~~~~

Single Application Testing
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Dedicate 75% cache to benchmark
   ./benchmarking.sh caterpillar -l 0xfff0 -t 15

Multi-Application Testing
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Split cache between applications
   ./benchmarking.sh caterpillar -l 0xff00 -t 15 &
   ./benchmarking.sh cyclictest -l 0x00ff -t 16 &

Core Selection Strategy
-----------------------

NUMA Topology Awareness
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check NUMA topology
   numactl --hardware

   # Select cores from same NUMA node
   ./benchmarking.sh caterpillar -l 0xffe -t 0,2,4,6  # Even cores, node 0
   ./benchmarking.sh cyclictest -l 0xffe -t 1,3,5,7   # Odd cores, node 0

Thermal Considerations
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Avoid thermally coupled cores
   # Check thermal zones
   ls /sys/devices/system/cpu/cpu*/topology/core_siblings_list

   # Use physically separated cores
   ./benchmarking.sh caterpillar -l 0xffe -t 0,8,16,24

Performance Testing Scenarios
-----------------------------

Baseline Performance
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Establish system baseline
   ./benchmarking.sh cyclictest -l 0xffff -t 15    # Full cache
   ./benchmarking.sh caterpillar -l 0xffff -t 16    # Full cache

Resource Contention Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test with limited cache
   ./benchmarking.sh cyclictest -l 0x00ff -t 15    # 50% cache
   ./benchmarking.sh caterpillar -l 0xff00 -t 16    # 50% cache

Stress Testing
~~~~~~~~~~~~~~

.. code-block:: bash

   # Test under system load
   ./benchmarking.sh cyclictest -l 0xffe -t 15 --stressor
   ./benchmarking.sh caterpillar -l 0xffe -t 16 --stressor

Industrial Application Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # CODESYS automation testing
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 15

   # OPC UA communication testing
   ./benchmarking.sh codesys-opcua-pubsub -l 0xffe -t 16

System Preparation
------------------

Setup Host APT repository
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash
    sudo -E wget -O- https://eci.intel.com/repos/gpg-keys/GPG-PUB-KEY-INTEL-ECI.gpg | sudo tee /usr/share/keyrings/eci-archive-keyring.gpg > /dev/null
    echo "deb [signed-by=/usr/share/keyrings/eci-archive-keyring.gpg] https://eci.intel.com/repos/$(source /etc/os-release && echo $VERSION_CODENAME) isar main" | sudo tee /etc/apt/sources.list.d/eci.list
    echo "deb-src [signed-by=/usr/share/keyrings/eci-archive-keyring.gpg] https://eci.intel.com/repos/$(source /etc/os-release && echo $VERSION_CODENAME) isar main" | sudo tee -a /etc/apt/sources.list.d/eci.list
    sudo bash -c 'echo -e "Package: *\nPin: origin eci.intel.com\nPin-Priority: 1000" > /etc/apt/preferences.d/isar'
    sudo bash -c 'echo -e "\nPackage: libflann*\nPin: version 1.19.*\nPin-Priority: -1\n\nPackage: flann*\nPin: version 1.19.*\nPin-Priority: -1" >> /etc/apt/preferences.d/isar'
Install ECI GRUB on Debian
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sudo apt-get update
   sudo apt-get install -y  eci-experimental

ECI Firmware Backports
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sudo apt-get reinstall '(firmware-linux-nonfree|linux-firmware$)'

Install ECI Kernel on Debian
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash
    sudo apt install -y linux-intel-rt
    sudo reboot

Update Kernel Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

Add to ``/etc/grub.d/09_eci``:

.. code-block:: bash

   isolcpus="10-16"

Update GRUB:

.. code-block:: bash

   sudo update-grub
   sudo reboot


Result Interpretation
---------------------

Cyclictest Output
~~~~~~~~~~~~~~~~~

.. code-block:: text

   T: 0 ( 1234) P:99 I:100000 C: 100000 Min: 2 Act: 4 Avg: 3 Max: 45

* ``Min``: Best case latency (microseconds)
* ``Max``: Worst case latency (microseconds) - Key metric
* ``Avg``: Average latency

**Good Values:**

* Max < 20μs: Excellent real-time performance
* Max < 50μs: Good real-time performance  
* Max > 100μs: Poor real-time performance

Caterpillar Results
~~~~~~~~~~~~~~~~~~~

Look for:

* Consistent execution times
* Low jitter/variance
* Stable performance under load

CODESYS Performance
~~~~~~~~~~~~~~~~~~~

Monitor:

* PLC cycle time consistency
* Web interface responsiveness
* OPC UA communication latency

Troubleshooting
---------------

Permission Issues
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Add user to docker group
   sudo usermod -aG docker $USER
   newgrp docker

   # Verify Docker access
   docker run hello-world

RDT Access Issues
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check RDT support
   cat /proc/cpuinfo | grep rdt

   # Verify RDT mount
   mount | grep resctrl

   # Check permissions
   ls -la /sys/fs/resctrl/

Performance Issues
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check CPU isolation
   cat /sys/devices/system/cpu/isolated

   # Verify CPU governor
   cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

   # Monitor thermal throttling
   journalctl | grep -i thermal

Container Issues
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check container status
   docker ps -a

   # View container logs
   docker logs <container_name>

   # Debug container
   docker run -it --rm <image_name> /bin/bash

Best Practices
--------------

Testing Environment
~~~~~~~~~~~~~~~~~~~

1. **Consistent Configuration**: Use same system configuration for all tests
2. **Thermal Management**: Ensure adequate cooling
3. **Background Activity**: Minimize unnecessary system activity
4. **Multiple Runs**: Perform multiple test iterations for statistical validity

Resource Allocation
~~~~~~~~~~~~~~~~~~~

1. **NUMA Awareness**: Consider NUMA topology in core selection
2. **Cache Planning**: Plan cache allocation strategy
3. **Thermal Coupling**: Avoid thermally coupled cores for sustained testing
4. **Interrupt Isolation**: Route interrupts away from test cores

Data Collection
~~~~~~~~~~~~~~~

1. **Baseline Measurement**: Always establish baseline before optimization
2. **Statistical Analysis**: Use multiple runs for confidence intervals
3. **Environmental Factors**: Document test environment conditions
4. **Result Validation**: Cross-validate results with different benchmarks

Advanced Usage
--------------

Custom Cache Allocation
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Create custom RDT groups
   sudo mkdir /sys/fs/resctrl/benchmark
   echo 15 > /sys/fs/resctrl/benchmark/cpus
   echo "L3:0=0xff" > /sys/fs/resctrl/benchmark/schemata

Multi-Instance Testing
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run multiple benchmark instances
   ./benchmarking.sh caterpillar -l 0xff00 -t 15 &
   ./benchmarking.sh cyclictest -l 0x00ff -t 16 &
   wait

Automated Testing
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   #!/bin/bash
   # Automated test suite
   for cores in "15" "15,16" "15,16,17"; do
       for cache in "0xff" "0xfff" "0xffff"; do
           echo "Testing cores $cores with cache $cache"
           ./benchmarking.sh cyclictest -l $cache -t $cores
           sleep 60  # Cool-down period
       done
   done

Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Monitor during test execution
   watch -n 1 'cat /proc/loadavg; free -h; sensors'

Examples Repository
-------------------

Real-time System Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Complete real-time validation suite
   ./benchmarking.sh build
   ./benchmarking.sh cyclictest -l 0xfff0 -t 15
   ./benchmarking.sh caterpillar -l 0xfff0 -t 16  
   ./benchmarking.sh codesys-jitter-benchmark -l 0xfff0 -t 17

Industrial Automation Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Industrial application performance
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 15
   ./benchmarking.sh codesys-opcua-pubsub -l 0xffe -t 16

Stress Testing Suite
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Performance under load
   ./benchmarking.sh cyclictest -l 0xffe -t 15 --stressor
   ./benchmarking.sh caterpillar -l 0xffe -t 16 --stressor
   ./benchmarking.sh codesys-jitter-benchmark -l 0xffe -t 17 --stressor

Long-Duration Testing
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Extended stability testing
   docker run -d --privileged --name mega-test \
       --cpuset-cpus=15,16,17,18 \
       -v /sys/fs/resctrl:/sys/fs/resctrl \
       mega-benchmark:latest
