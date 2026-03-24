#!/bin/bash
###############################################################################
# build-all.sh - Build and push all CODESYS HDE2E PLC containers
#
# Usage: ./build-all.sh [options] [registry]
#
# Options:
#   --base          Build the base image first
#   --base-only     Build only the base image, skip instance images
#   --no-cache      Pass --no-cache to docker build
#
# Environment variables:
#   DEB             CODESYS .deb filename (default: codesyscontrol_virtuallinux_4.18.0.0_amd64.deb)
#   TAG             Image tag for instance images (default: latest)
#   BASE_TAG        Image tag for base image (default: 1.0.1)
#
# Examples:
#   ./build-all.sh                          # Build instance images only (base must exist)
#   ./build-all.sh --base                   # Build base + all instance images
#   ./build-all.sh --base-only              # Build base image only
#   ./build-all.sh --base myregistry.com    # Build all and push to registry
#   DEB=codesyscontrol_virtuallinux_4.20.0.0_amd64.deb ./build-all.sh --base
###############################################################################

set -e

# Defaults
BUILD_BASE=false
BASE_ONLY=false
NO_CACHE=""
REGISTRY=""

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base)
            BUILD_BASE=true
            shift
            ;;
        --base-only)
            BUILD_BASE=true
            BASE_ONLY=true
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        -h|--help)
            sed -n '2,/^###$/p' "$0" | grep '^#' | sed 's/^# \?//'
            exit 0
            ;;
        *)
            REGISTRY="$1"
            shift
            ;;
    esac
done

REGISTRY="${REGISTRY:-localhost}"
TAG="${TAG:-latest}"
BASE_TAG="${BASE_TAG:-1.0.1}"
DEB="${DEB:-codesyscontrol_virtuallinux_4.18.0.0_amd64.deb}"

BASE_IMAGE_NAME="codesys-hde2e-base"
if [ "$REGISTRY" != "localhost" ]; then
    BASE_IMAGE="${REGISTRY}/${BASE_IMAGE_NAME}:${BASE_TAG}"
else
    BASE_IMAGE="${BASE_IMAGE_NAME}:${BASE_TAG}"
fi

# Check prerequisites
if [ ! -f "$DEB" ]; then
    echo "ERROR: $DEB not found"
    exit 1
fi

if [ ! -f "Dockerfile.base" ] || [ ! -f "Dockerfile" ]; then
    echo "ERROR: Dockerfile.base and/or Dockerfile not found"
    exit 1
fi

# Build base image
if [ "$BUILD_BASE" = true ]; then
    echo "==> Building base image: ${BASE_IMAGE}"
    docker build \
        ${NO_CACHE} \
        --build-arg CODESYSCONTROL_DEB="${DEB}" \
        -f Dockerfile.base \
        -t "${BASE_IMAGE}" \
        .
    echo ""
    echo "Base image built: ${BASE_IMAGE}"
    echo ""

    if [ "$REGISTRY" != "localhost" ]; then
        echo "Pushing base image to ${REGISTRY}..."
        docker push "${BASE_IMAGE}"
        echo ""
    fi

    if [ "$BASE_ONLY" = true ]; then
        echo "Done (base only)."
        exit 0
    fi
else
    # Verify base image exists
    if ! docker image inspect "${BASE_IMAGE}" >/dev/null 2>&1; then
        echo "ERROR: Base image ${BASE_IMAGE} not found."
        echo "       Build it first with: $0 --base-only"
        exit 1
    fi
    echo "Using existing base image: ${BASE_IMAGE}"
    echo ""
fi

# Build all 4 PLC instance images
echo "Building all CODESYS PLC instance images..."
echo "Base image: ${BASE_IMAGE}"
echo "Registry:   ${REGISTRY}"
echo "Tag:        ${TAG}"
echo ""

# Control_PLC_01
echo "==> Building Control_PLC_01..."
docker build \
    ${NO_CACHE} \
    --build-arg BASE_IMAGE="${BASE_IMAGE}" \
    --build-arg PLC_NAME=Control_PLC_01 \
    --build-arg APP_TYPE=control \
    --build-arg INSTANCE_NUM=01 \
    -t ${REGISTRY}/codesys-control-plc-01:${TAG} .

# Control_PLC_02
echo "==> Building Control_PLC_02..."
docker build \
    ${NO_CACHE} \
    --build-arg BASE_IMAGE="${BASE_IMAGE}" \
    --build-arg PLC_NAME=Control_PLC_02 \
    --build-arg APP_TYPE=control \
    --build-arg INSTANCE_NUM=02 \
    -t ${REGISTRY}/codesys-control-plc-02:${TAG} .

# IO_PLC_01
echo "==> Building IO_PLC_01..."
docker build \
    ${NO_CACHE} \
    --build-arg BASE_IMAGE="${BASE_IMAGE}" \
    --build-arg PLC_NAME=IO_PLC_01 \
    --build-arg APP_TYPE=io \
    --build-arg INSTANCE_NUM=01 \
    -t ${REGISTRY}/codesys-io-plc-01:${TAG} .

# IO_PLC_02
echo "==> Building IO_PLC_02..."
docker build \
    ${NO_CACHE} \
    --build-arg BASE_IMAGE="${BASE_IMAGE}" \
    --build-arg PLC_NAME=IO_PLC_02 \
    --build-arg APP_TYPE=io \
    --build-arg INSTANCE_NUM=02 \
    -t ${REGISTRY}/codesys-io-plc-02:${TAG} .

echo ""
echo "Build complete!"
docker images | grep -E "codesys-(control|io)-plc|codesys-hde2e-base" | grep -E "${TAG}|${BASE_TAG}"

# Push if registry is not localhost
if [ "$REGISTRY" != "localhost" ]; then
    echo ""
    echo "Pushing instance images to $REGISTRY..."
    docker push ${REGISTRY}/codesys-control-plc-01:${TAG}
    docker push ${REGISTRY}/codesys-control-plc-02:${TAG}
    docker push ${REGISTRY}/codesys-io-plc-01:${TAG}
    docker push ${REGISTRY}/codesys-io-plc-02:${TAG}
    echo "Push complete!"
fi
