#!/bin/bash
# Copyright 2025 milbert.ai

# Build all tool Docker images

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TOOL_IMAGES_DIR="$PROJECT_ROOT/tool-images"

# Registry prefix (change for your Docker registry)
REGISTRY="${DOCKER_REGISTRY:-kwebbie}"

echo "Building tool Docker images..."

# Build base image first
echo "Building base image..."
docker build -t "$REGISTRY/base:latest" "$TOOL_IMAGES_DIR/base"

# Build individual tool images
TOOLS=(
    "nmap"
    "nuclei"
    "gobuster"
    "sqlmap"
    "hydra"
)

for tool in "${TOOLS[@]}"; do
    if [ -d "$TOOL_IMAGES_DIR/$tool" ]; then
        echo "Building $tool image..."
        docker build -t "$REGISTRY/$tool:latest" "$TOOL_IMAGES_DIR/$tool"
    fi
done

echo ""
echo "All tool images built successfully!"
echo ""
echo "Available images:"
docker images | grep "$REGISTRY"
