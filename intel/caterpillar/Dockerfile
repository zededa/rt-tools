# INTEL CONFIDENTIAL
#
# Copyright (c) Intel Corporation, 2025
#
# This software and the related documents are Intel copyrighted materials, and
# your use of them is governed by the express license under which they were
# provided to you (License). Unless the License provides otherwise, you may
# not use, modify, copy, publish, distribute, disclose or transmit this
# software or the related documents without Intel's prior written permission.
#
# This software and the related documents are provided as is, with no express
# or implied warranties, other than those that are expressly stated in the
# License.
#

FROM eci-base:latest
# Install required dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
 caterpillar \
 && rm -rf /var/lib/apt/lists/*

ENV USER=root
RUN chmod +x /opt/benchmarking/caterpillar/caterpillar

WORKDIR /opt/benchmarking/caterpillar

# example directory to share file (-v output:/tmp/output)
RUN mkdir -p /tmp/output

