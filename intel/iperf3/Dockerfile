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

# iperf3 not distributed by ECI repo but building from base to fit framework
RUN apt-get update && apt-get install -y --no-install-recommends \
 iperf3 \
 && rm -rf /var/lib/apt/lists/*

# Expose iperf3 server port
EXPOSE 5201

ENTRYPOINT ["iperf3"]