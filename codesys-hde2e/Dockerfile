###############################################################################
# Dockerfile - Instance-specific CODESYS HDE2E PLC image
#
# Requires base image built from Dockerfile.base:
#   docker build -f Dockerfile.base -t codesys-hde2e-base:latest .
#
# Build arguments:
#   PLC_NAME     - Instance name (e.g., Control_PLC_01, IO_PLC_01)
#   APP_TYPE     - Application type: "control" or "io"
#   INSTANCE_NUM - Instance number: "01" or "02"
#   BASE_IMAGE   - Base image tag (default: codesys-hde2e-base:latest)
#
# Usage examples:
#   docker build --build-arg PLC_NAME=Control_PLC_01 \
#                --build-arg APP_TYPE=control \
#                --build-arg INSTANCE_NUM=01 \
#                -t codesys-control-plc-01:latest .
#
#   docker build --build-arg PLC_NAME=IO_PLC_02 \
#                --build-arg APP_TYPE=io \
#                --build-arg INSTANCE_NUM=02 \
#                --build-arg BASE_IMAGE=myregistry.com/codesys-hde2e-base:4.18.0 \
#                -t codesys-io-plc-02:latest .
###############################################################################

ARG BASE_IMAGE=codesys-hde2e-base:latest
FROM ${BASE_IMAGE}

# Build arguments
ARG PLC_NAME
ARG APP_TYPE
ARG INSTANCE_NUM

# Validate required arguments
RUN test -n "$PLC_NAME" || (echo "ERROR: PLC_NAME build arg is required" && exit 1)
RUN test -n "$APP_TYPE" || (echo "ERROR: APP_TYPE build arg is required" && exit 1)
RUN test -n "$INSTANCE_NUM" || (echo "ERROR: INSTANCE_NUM build arg is required" && exit 1)

# Labels for container identification
LABEL plc.name="${PLC_NAME}"
LABEL plc.type="${APP_TYPE}"
LABEL plc.instance="${INSTANCE_NUM}"
LABEL org.opencontainers.image.title="CODESYS ${PLC_NAME}"
LABEL org.opencontainers.image.description="CODESYS Control PLC Runtime for ${PLC_NAME}"

# Copy pre-built PLC application and configuration for the specified instance
# This includes the compiled Control.app binary and all runtime state
COPY plc/${PLC_NAME}/conf/codesyscontrol/ /conf/codesyscontrol/
COPY plc/${PLC_NAME}/data/codesyscontrol/ /data/codesyscontrol/

# Overlay instance-specific configuration files
COPY configs/${APP_TYPE}/CODESYSControl_User.cfg /conf/codesyscontrol/

# Copy instance-specific hdE2E latency configuration
# Control PLCs use hdE2ELatencyConfig_Control_PLC_XX.json -> hdE2ELatencyConfig.json
# IO PLCs use hdE2ELatencyConfig_IO_PLC_XX.json -> hdE2ELatencyConfigio.json
COPY configs/${APP_TYPE}/hdE2ELatencyConfig_${PLC_NAME}.json /tmp/hdE2ELatencyConfig.json
RUN if [ "$APP_TYPE" = "io" ]; then \
    mv /tmp/hdE2ELatencyConfig.json /data/codesyscontrol/PlcLogic/Config/hdE2ELatencyConfigio.json; \
    else \
    mv /tmp/hdE2ELatencyConfig.json /data/codesyscontrol/PlcLogic/Config/hdE2ELatencyConfig.json; \
    fi

# Optional: Copy RDT configuration for reference
COPY configs/rdt_config_${APP_TYPE}.yaml /etc/rdt_config.yaml

# Copy startup scripts
COPY startup.sh /opt/codesys/scripts/startup.sh
COPY startup-strace.sh /opt/codesys/scripts/startup-strace.sh

# Set working directory
WORKDIR /var/opt/codesys/

# Start CODESYS runtime
# ENTRYPOINT ["/opt/codesys/scripts/startup-strace.sh"]
ENTRYPOINT ["/opt/codesys/scripts/startup.sh"]
CMD ["-d", "eth1"]
