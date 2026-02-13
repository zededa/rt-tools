FROM eci-base:latest

# Add ECI repository key and sources
RUN wget -O- https://eci.intel.com/repos/gpg-keys/GPG-PUB-KEY-INTEL-ECI.gpg | tee /usr/share/keyrings/eci-archive-keyring.gpg > /dev/null

RUN . /etc/os-release && \
    echo "deb [signed-by=/usr/share/keyrings/eci-archive-keyring.gpg] https://eci.intel.com/repos/${VERSION_CODENAME} isar main" | tee /etc/apt/sources.list.d/eci.list && \
    echo "deb-src [signed-by=/usr/share/keyrings/eci-archive-keyring.gpg] https://eci.intel.com/repos/${VERSION_CODENAME} isar main" | tee -a /etc/apt/sources.list.d/eci.list

RUN bash -c 'echo -e "Package: *\nPin: origin eci.intel.com\nPin-Priority: 1000" > /etc/apt/preferences.d/isar' && \
    bash -c 'echo -e "\nPackage: libflann*\nPin: version 1.19.*\nPin-Priority: -1\n\nPackage: flann*\nPin: version 1.19.*\nPin-Priority: -1" >> /etc/apt/preferences.d/isar'

RUN apt-get update && apt-get install -y --no-install-recommends \
    eci-realtime-benchmarking \
    rt-tests \
    intel-cmt-cat \
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
COPY main.py ./

# Install Python 3.12 and sync dependencies
RUN uv python install 3.12 && uv sync

# Default: run main.py with docker=false so benchmarks execute natively
ENTRYPOINT ["uv", "run", "python", "main.py", "run.docker=false", "pqos.enable=false", "run.stressor=false"]
# Override command to select benchmark, e.g.:
#   docker run ... rt-tools-main:latest run.command=caterpillar
#   docker run ... rt-tools-main:latest run.command=cyclictest
