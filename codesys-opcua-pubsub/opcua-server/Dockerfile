# INTEL CONFIDENTIAL
#
# Copyright (c) Intel Corporation, 2023
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
# Authors:
#  Jeremy Ouillette <jeremy.ouillette@intel.com>
#

FROM eci-base:latest
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /opt/ec-protocol-bridge

ARG APP="ec-bridge"
ARG CONFIG="smoke-test.yaml"

ENV APP_CMD="/opt/ec-protocol-bridge/${APP}"
ENV CONFIG_CMD="/opt/ec-protocol-bridge/config/${CONFIG}"

# Update APT sources
RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates wget iproute2 ec-bridge \
  && rm -rf /var/lib/apt/lists/*

# Install required dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
 eci-connectivity-ec-bridge \
 && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/opt/ec-protocol-bridge/opcsvr", "/opt/ec-protocol-bridge/config/opcsvr-pubsub.yaml"]
