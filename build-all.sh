#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${1:-}"
TAG="${TAG:?TAG env var is required (e.g. TAG=1.0.7 $0 [registry])}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/ztest_key.pub}"

if [ ! -f "$SSH_KEY" ]; then
    echo "ERROR: SSH public key not found at ${SSH_KEY}"
    echo "Set SSH_KEY to the path of your public key file"
    exit 1
fi

SSH_KEY_CONTENT="$(cat "$SSH_KEY")"
echo "Using SSH public key: ${SSH_KEY}"

IMAGES=(
    "eci-base:Dockerfile.base:."
    "caterpillar:caterpillar/Dockerfile:."
    "cyclictest:cyclictest/Dockerfile:."
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Resolve FQDN prefix: always include registry host, even for local builds
if [ -n "$REGISTRY" ]; then
    FQDN_PREFIX="${REGISTRY}"
else
    FQDN_PREFIX="docker.io/library"
fi

BUILT_TAGS=()

for entry in "${IMAGES[@]}"; do
    IFS=: read -r name dockerfile context <<< "$entry"
    local_tag="${name}:${TAG}"

    echo "===> Building ${local_tag} from ${dockerfile} (context: ${context})"
    docker build --network=host \
        --build-arg BASE_TAG="${TAG}" \
        --build-arg SSH_KEY="${SSH_KEY_CONTENT}" \
        -f "$dockerfile" \
        -t "$local_tag" \
        "$context"

    BUILT_TAGS+=("${FQDN_PREFIX}/${name}:${TAG}")

    if [ -n "$REGISTRY" ]; then
        remote_tag="${REGISTRY}/${name}:${TAG}"
        remote_latest="${REGISTRY}/${name}:latest"

        docker tag "$local_tag" "$remote_tag"
        docker tag "$local_tag" "$remote_latest"

        echo "===> Pushing ${remote_tag}"
        docker push "$remote_tag"

        echo "===> Pushing ${remote_latest}"
        docker push "$remote_latest"

        BUILT_TAGS+=("${REGISTRY}/${name}:latest")
    fi

    echo ""
done

echo ""
echo "BUILD SUMMARY"
echo ""

for entry in "${IMAGES[@]}"; do
    IFS=: read -r name dockerfile context <<< "$entry"
    local_tag="${name}:${TAG}"
    size=$(docker image inspect "$local_tag" --format='{{.Size}}' 2>/dev/null || echo "0")
    size_mb=$(( size / 1024 / 1024 ))
    printf "  %-50s %4s MB\n" "${FQDN_PREFIX}/${name}:${TAG}" "$size_mb"
    if [ -n "$REGISTRY" ]; then
        printf "  %-50s %4s MB\n" "${REGISTRY}/${name}:latest" "$size_mb"
    fi
done

echo ""
echo "QUICK START"
echo "  SSH:        ssh -i <key> root@<host>"
echo "  Jupyter:    ssh in, then run: jupyter-start"
echo "  Preflight:  ssh in, then run: rt-preflight"
echo ""

echo "ALL TAGS"
for t in "${BUILT_TAGS[@]}"; do
    echo "  $t"
done
echo ""

if [ -n "$REGISTRY" ]; then
    echo "Status: built and pushed to ${REGISTRY}"
else
    echo "Status: built locally (no registry, push skipped)"
fi
echo ""
