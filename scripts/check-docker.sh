#!/bin/bash
# Quick Docker status check

echo "🔍 Checking Docker status..."
echo ""

# Check if Docker CLI is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker CLI is not installed"
    exit 1
fi
echo "✅ Docker CLI is installed"

# Check if Docker daemon is running
if docker info >/dev/null 2>&1; then
    echo "✅ Docker daemon is running"
    docker info | grep -E "Server Version|Operating System" | head -2
else
    echo "❌ Docker daemon is NOT running"
    echo ""
    echo "Please start Docker Desktop:"
    echo "  1. Open Docker Desktop application"
    echo "  2. Wait for it to fully start (whale icon should be steady)"
    echo "  3. Run this script again"
    exit 1
fi

# Check Docker context
echo ""
echo "📋 Docker context:"
docker context ls
CURRENT_CONTEXT=$(docker context ls --format '{{.Name}}' | grep '^*' | sed 's/^*//' | sed 's/^ //')
echo "Current: $CURRENT_CONTEXT"

# Check buildx
echo ""
if command -v docker buildx &> /dev/null; then
    echo "✅ Docker Buildx is available"
    echo "📋 Available builders:"
    docker buildx ls 2>/dev/null || echo "  (could not list builders)"
else
    echo "⚠️  Docker Buildx is not available"
fi

echo ""
echo "✅ Docker is ready!"







