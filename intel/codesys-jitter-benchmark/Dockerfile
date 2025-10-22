# Copyright 2017-2023 Intel Corporation.
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

FROM eci-base:latest

USER root
ARG CDS_VERSION=4.11.0.0
ARG VISU_PORT=8080
ARG UASERVER_PORT=4840
ARG APP_DEB
ARG ECI_DEB
ENV SCRIPT=docker-entrypoint.sh
# ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/codesys/lib

WORKDIR /workdir

# Required packages to install the CodeSys Debian package
RUN apt-get update && apt-get install -y --no-install-recommends \
    lsb-base \
    procps \
    libfontconfig1 \
    libfreetype6 \
    libice6 \
    libsm6 \
    libx11-6 \
    libxcb1 \
    libusb-1.0-0 \
    wget \
    unzip \
    iproute2 \
    ca-certificates \
&& rm -rf /var/lib/apt/lists/*

COPY install.sh install.sh

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN chmod +x install.sh && ./install.sh codesyscontrol ${CDS_VERSION}
RUN if [ -n "${APP_DEB}" ] ; then \
   apt-get update && apt-get install -y --no-install-recommends -f ${APP_DEB}; \
fi

COPY $SCRIPT /

### Begin Override Codesys Application Boot Project: opcua-codesys-benchmark ###
### This overrides the ECI_DEB feature from above                            ###

# Extract and store version information
# Remove initial execution of /etc/init.d/codesyscontrol
RUN update-rc.d codesyscontrol remove && chmod -x /etc/init.d/codesyscontrol
EXPOSE 1217/tcp 11740/tcp ${UASERVER_PORT}/udp ${UASERVER_PORT}/tcp ${VISU_PORT}/tcp ${VISU_PORT}/udp
COPY codesyscontrol /etc/init.d/codesyscontrol
RUN chmod +x /docker-entrypoint.sh
# COPY codesyscontrol /etc/init.d/codesyscontrol
RUN chmod +x /etc/init.d/codesyscontrol