# Use a base image with necessary build tools (e.g., Ubuntu with build-essential)
FROM ubuntu:latest

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libncurses-dev \
    flex \
    bison \
    libssl-dev \
    elfutils \
    pahole \
    git
RUN git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git

# Set the working directory inside the container
WORKDIR /linux

# Copy the cloned kernel source code into the container

# Configure the kernel (e.g., using a default config or an existing one)
# This example uses the default config for your architecture
RUN make defconfig
RUN apt-get install libncurses-dev libssl-dev libelf-dev bc
COPY build-kernel.sh .
# Build the kernel (jN for parallel compilation, where N is number of cores
#CMD ["/bin/bash","-c", "make -j $(bash -c nproc)"]
CMD ["/bin/sh", "build-kernel.sh"]

