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

ARG BASE_TAG=latest
FROM eci-base:${BASE_TAG}

# Install caterpillar benchmark
RUN apt-get update && apt-get install -y --no-install-recommends \
    caterpillar \
    && rm -rf /var/lib/apt/lists/*

ENV USER=root
RUN chmod +x /opt/benchmarking/caterpillar/caterpillar

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/
COPY conf/ ./conf/
COPY notebook/ ./notebook/
COPY main.py ./

# Install Python 3.12 and sync dependencies
RUN uv python install 3.12 && uv sync

# Output directory for results
RUN mkdir -p /tmp/output

ENTRYPOINT ["/entrypoint.sh", "uv", "run", "python", "main.py", "run.docker=false", "pqos.enable=false", "run.stressor=false", "run.interactive=false", "demo.demo_mode=false", "run.command=caterpillar"]
