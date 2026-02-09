#!/bin/bash
# Helper script to push image to GHCR with proper error handling

set -e

REGISTRY=${1:-"ghcr.io/mutesasiratimo/kcca_kla_connect_api"}
TAG=${2:-"latest"}
PLATFORM=${3:-"linux/amd64"}

FULL_IMAGE="${REGISTRY}:${TAG}"

echo "🚀 Pushing to GHCR"
echo "=================="
echo "Image: ${FULL_IMAGE}"
echo "Platform: ${PLATFORM}"
echo ""

# Check Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running!"
    echo ""
    echo "Please start Docker Desktop and try again."
    echo "On Mac: Open Docker Desktop application"
    exit 1
fi

# Check if logged in to GHCR
if ! docker pull "${REGISTRY}:nonexistent" 2>&1 | grep -q "authentication required\|unauthorized"; then
    echo "ℹ️  Checking GHCR authentication..."
    if ! echo "$GITHUB_TOKEN" | docker login ghcr.io -u mutesasiratimo --password-stdin 2>/dev/null; then
        echo "⚠️  Not logged in to GHCR"
        echo ""
        echo "Please login first:"
        echo "  echo \$GITHUB_TOKEN | docker login ghcr.io -u mutesasiratimo --password-stdin"
        echo ""
        echo "Or manually:"
        echo "  docker login ghcr.io"
        exit 1
    fi
fi

# Setup buildx
echo "📦 Setting up Docker Buildx..."
if command -v docker buildx &> /dev/null; then
    # Check if builder exists
    if ! docker buildx ls | grep -q "multiplatform"; then
        echo "Creating buildx builder 'multiplatform'..."
        docker buildx create --name multiplatform --use --bootstrap || \
        docker buildx create --name multiplatform --use || \
        docker buildx use default
    else
        echo "Using existing 'multiplatform' builder..."
        docker buildx use multiplatform || docker buildx use default
    fi
    
    echo "🏗️  Building and pushing with Buildx..."
    docker buildx build --platform "${PLATFORM}" -t "${FULL_IMAGE}" --push .
else
    echo "⚠️  Buildx not available, using standard Docker build..."
    echo "⚠️  Warning: Cross-platform builds may not work!"
    docker build -t "${FULL_IMAGE}" .
    docker push "${FULL_IMAGE}"
fi

echo ""
echo "✅ Successfully pushed: ${FULL_IMAGE}"
echo ""
echo "🔍 Verify with:"
echo "  docker pull ${FULL_IMAGE}"







