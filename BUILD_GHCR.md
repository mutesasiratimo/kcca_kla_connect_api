# Building and Pushing to GHCR (Linux AMD64)

## Problem

If you get this error when pulling the image:
```
no matching manifest for linux/amd64 in the manifest list entries
```

This means the image was built for the wrong platform (e.g., ARM64 on Mac instead of AMD64 for Linux VPS).

## Solutions

### Option 1: Build and Push Locally (Recommended for Quick Fix)

Build for `linux/amd64` platform using Docker Buildx:

```bash
# Log in to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Create buildx builder (if needed)
docker buildx create --use --name multiplatform 2>/dev/null || docker buildx use multiplatform

# Build and push for Linux AMD64
docker buildx build --platform linux/amd64 \
  -t ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest \
  --push .
```

**Or use the Makefile:**
```bash
make build-push REGISTRY=ghcr.io/mutesasiratimo/kcca_kla_connect_api PLATFORM=linux/amd64
```

### Option 2: Use GitHub Actions (Recommended for CI/CD)

The GitHub Actions workflow has been updated to automatically build for `linux/amd64`. 

**Trigger the workflow:**
1. Push to `main` branch (automatic build)
2. Or manually trigger from GitHub Actions tab:
   - Go to Actions → "Build and Deploy to Kubernetes (VPS)"
   - Click "Run workflow"
   - Set `dry_run` to `false` to push the image
   - Click "Run workflow"

The workflow will:
- Build for `linux/amd64` platform
- Push to `ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest`
- Also tag with commit SHA

### Option 3: Build on Linux Machine/VPS

If you have access to a Linux machine (same architecture as your VPS):

```bash
# On Linux machine
docker build -t ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest .
docker push ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest
```

---

## Verify Image Platform

After building, verify the image platform:

```bash
# Inspect image manifest
docker manifest inspect ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest

# Should show:
# "architecture": "amd64"
# "os": "linux"
```

---

## Using Docker Buildx (Cross-Platform)

Docker Buildx allows building for different platforms even on Mac/ARM:

```bash
# Install/use buildx
docker buildx create --use --name multiplatform

# Build for multiple platforms (optional)
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest \
  --push .

# Build for single platform (Linux AMD64 for VPS)
docker buildx build --platform linux/amd64 \
  -t ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest \
  --push .
```

---

## GitHub Actions Workflow

The updated workflow (`.github/workflows/deploy.yaml`) now:
- ✅ Builds for `linux/amd64` by default
- ✅ Uses GitHub token for GHCR authentication
- ✅ Pushes to `ghcr.io/mutesasiratimo/kcca_kla_connect_api`

**Workflow triggers:**
- Push to `main` branch
- Push tags starting with `v*.*.*`
- Manual workflow dispatch

---

## Quick Fix Commands

**If you're on Mac (Apple Silicon):**
```bash
# Build for Linux AMD64
docker buildx build --platform linux/amd64 \
  -t ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest \
  --push .
```

**If you're on Linux:**
```bash
# Standard build (will be for your architecture)
docker build -t ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest .
docker push ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest
```

**After pushing, verify on VPS:**
```bash
# On VPS
docker pull ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest
# Should work now! ✅
```

---

## Troubleshooting

### Buildx not available
```bash
# Install buildx plugin
mkdir -p ~/.docker/cli-plugins
curl -L https://github.com/docker/buildx/releases/latest/download/buildx-v0.11.2.linux-amd64 -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx
```

### Authentication issues
```bash
# Create GitHub Personal Access Token with `write:packages` permission
# Then login:
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### Still getting platform errors
- Verify you're building for `linux/amd64`
- Check your VPS architecture: `uname -m` (should be `x86_64`)
- Use `docker manifest inspect` to check image platforms

---

## Summary

**Best approach:**
1. Use GitHub Actions workflow (automatic, builds for correct platform)
2. Or build locally with `docker buildx build --platform linux/amd64`

**Key point:** Always specify `--platform linux/amd64` when building on Mac/ARM for Linux VPS deployment.







