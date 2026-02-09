# Deploying from GHCR to VPS (Without Repository)

This guide explains how to deploy your application to a remote Linux VPS using GitHub Container Registry (GHCR) **without cloning the repository** on the VPS.

## 🎯 Overview

The deployment process:
1. **Build and push images to GHCR** (from your local machine or CI/CD)
2. **On VPS**: Only need kubectl and Kubernetes manifests
3. **Create GHCR pull secret** on VPS
4. **Deploy using kubectl** directly

---

## 📋 Prerequisites

### On Your Local Machine
- Docker installed
- GitHub account with access to the repository
- GitHub Personal Access Token (PAT) with `write:packages` permission

### On Your VPS
- Kubernetes cluster (k3s, microk8s, or full K8s)
- `kubectl` installed and configured
- SSH access to VPS

---

## 🚀 Step-by-Step Deployment

### Step 1: Build and Push Image to GHCR (Local Machine)

#### Option A: Manual Build and Push

```bash
# On your local machine
cd /path/to/kcca_kla_connect_api

# Log in to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Build and tag the image
docker build -t ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest .

# Push to GHCR
docker push ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest

# Optional: Tag a specific version
docker tag ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest ghcr.io/mutesasiratimo/kcca_kla_connect_api:v1.0.0
docker push ghcr.io/mutesasiratimo/kcca_kla_connect_api:v1.0.0
```

#### Option B: Use GitHub Actions (Recommended)

If you have GitHub Actions set up, images are automatically built and pushed on push to `main` branch.

Check your repository's Packages section to see published images:
- https://github.com/mutesasiratimo/kcca_kla_connect_api/pkgs/container/kcca_kla_connect_api

---

### Step 2: Set Up VPS - Install Kubernetes

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Install k3s (lightweight, recommended)
curl -sfL https://get.k3s.io | sh -
sudo systemctl enable k3s
sudo systemctl start k3s

# Configure kubectl
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config
chmod 600 ~/.kube/config

# Verify cluster
kubectl get nodes
```

---

### Step 3: Create GHCR Pull Secret on VPS

You need a GitHub Personal Access Token (PAT) with `read:packages` permission.

```bash
# On VPS, create the pull secret
kubectl create namespace kcca-kla-connect

# Create GHCR pull secret
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_PAT \
  --namespace=kcca-kla-connect
```

**Or if your image is public**, you can skip this step and remove `imagePullSecrets` from deployment.yaml.

---

### Step 4: Download Kubernetes Manifests (VPS)

You have two options:

#### Option A: Download Manifests from GitHub (Recommended)

```bash
# On VPS, create a directory for manifests
mkdir -p ~/k8s-manifests
cd ~/k8s-manifests

# Download manifests directly from GitHub
curl -o namespace.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/namespace.yaml
curl -o configmap.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/configmap.yaml
curl -o deployment.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/deployment.yaml
curl -o service.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/service.yaml
curl -o pvc-uploads.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/pvc-uploads.yaml
curl -o postgres.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/postgres.yaml  # Optional if using external DB
```

#### Option B: Copy Manifests via SCP

```bash
# From your local machine
scp -r k8s/*.yaml user@your-vps-ip:~/k8s-manifests/
```

---

### Step 5: Configure Secrets on VPS

```bash
# On VPS, create application secrets
kubectl create secret generic kcca-kla-connect-secrets \
  --from-literal=DATABASE_URL='postgresql://user:password@host:5432/klaconnect' \
  --from-literal=SECRET='your-production-secret-key' \
  --from-literal=POSTGRES_PASSWORD='postgres-password' \
  --namespace=kcca-kla-connect \
  --dry-run=client -o yaml | kubectl apply -f -
```

**For production**, use strong, unique values for all secrets.

---

### Step 6: Deploy Application

```bash
# On VPS, apply all manifests
cd ~/k8s-manifests

# Create namespace (if not exists)
kubectl apply -f namespace.yaml

# Deploy ConfigMap
kubectl apply -f configmap.yaml

# Create PVCs
kubectl apply -f pvc-uploads.yaml

# Deploy PostgreSQL (optional, skip if using external DB)
kubectl apply -f postgres.yaml

# Wait for PostgreSQL to be ready (if deploying)
kubectl wait --for=condition=ready pod -l app=postgres -n kcca-kla-connect --timeout=180s

# Deploy application
kubectl apply -f deployment.yaml

# Deploy services
kubectl apply -f service.yaml

# Check status
kubectl get all -n kcca-kla-connect
```

---

### Step 7: Verify Deployment

```bash
# Check pods
kubectl get pods -n kcca-kla-connect

# View logs
kubectl logs -f deployment/kcca-kla-connect-web -n kcca-kla-connect

# Check service
kubectl get svc -n kcca-kla-connect

# Access the API (via port-forward for testing)
kubectl port-forward -n kcca-kla-connect service/kcca-kla-connect-internal 8000:8000
# Then visit: http://localhost:8000/docs
```

---

## 🔄 Updating the Application

When you push a new image to GHCR:

### From Local Machine
```bash
# Build and push new image
docker build -t ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest .
docker push ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest
```

### On VPS
```bash
# Trigger rolling update (pulls new image automatically with imagePullPolicy: Always)
kubectl rollout restart deployment/kcca-kla-connect-web -n kcca-kla-connect

# Or update to a specific tag
kubectl set image deployment/kcca-kla-connect-web \
  web=ghcr.io/mutesasiratimo/kcca_kla_connect_api:v1.0.1 \
  -n kcca-kla-connect

# Monitor rollout
kubectl rollout status deployment/kcca-kla-connect-web -n kcca-kla-connect
```

---

## 📝 Minimal Deployment Script for VPS

Create a simple script on your VPS:

```bash
#!/bin/bash
# ~/deploy.sh - Minimal deployment script for VPS

set -e

NAMESPACE="kcca-kla-connect"
MANIFESTS_DIR="$HOME/k8s-manifests"

echo "🚀 Deploying KCCA Kla Connect API..."

# Ensure namespace exists
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply all manifests
kubectl apply -f $MANIFESTS_DIR/configmap.yaml
kubectl apply -f $MANIFESTS_DIR/pvc-uploads.yaml
kubectl apply -f $MANIFESTS_DIR/deployment.yaml
kubectl apply -f $MANIFESTS_DIR/service.yaml

# Restart deployment to pull latest image
kubectl rollout restart deployment/kcca-kla-connect-web -n $NAMESPACE

echo "✅ Deployment complete!"
kubectl get all -n $NAMESPACE
```

Make it executable:
```bash
chmod +x ~/deploy.sh
```

---

## 🌐 Exposing the Application

### Option 1: NodePort (Simple)

```bash
# Modify service to use NodePort
kubectl patch svc kcca-kla-connect-service -n kcca-kla-connect \
  -p '{"spec":{"type":"NodePort"}}'

# Get NodePort
kubectl get svc kcca-kla-connect-service -n kcca-kla-connect

# Access: http://YOUR_VPS_IP:NODEPORT/docs
```

### Option 2: Ingress (Recommended for Production)

For k3s, Traefik is installed by default. Create an ingress:

```bash
# Download ingress manifest
curl -o ingress.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/ingress.yaml

# Edit and apply
kubectl apply -f ingress.yaml
```

---

## 🔐 Security Best Practices

1. **Use Private Images**: Keep your GHCR images private and use pull secrets
2. **Rotate Secrets**: Regularly rotate your GitHub PAT
3. **Use Versioned Tags**: Don't rely on `:latest`, use specific version tags
4. **Limit Access**: Restrict who can access your VPS and Kubernetes cluster
5. **Firewall Rules**: Only expose necessary ports (80, 443, 22)

```bash
# Example firewall setup
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

---

## 🐛 Troubleshooting

### Image Pull Errors

```bash
# Check if secret exists
kubectl get secret ghcr-pull-secret -n kcca-kla-connect

# Verify secret is correct
kubectl describe secret ghcr-pull-secret -n kcca-kla-connect

# Test image pull manually
docker pull ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest
```

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod -l app=kcca-kla-connect -n kcca-kla-connect

# Check logs
kubectl logs -l app=kcca-kla-connect -n kcca-kla-connect --tail=100
```

### Update Image Tag

```bash
# Update to specific version
kubectl set image deployment/kcca-kla-connect-web \
  web=ghcr.io/mutesasiratimo/kcca_kla_connect_api:v1.0.0 \
  -n kcca-kla-connect
```

---

## 📚 Quick Reference Commands

```bash
# View all resources
kubectl get all -n kcca-kla-connect

# View pods
kubectl get pods -n kcca-kla-connect

# View logs
kubectl logs -f deployment/kcca-kla-connect-web -n kcca-kla-connect

# Restart deployment
kubectl rollout restart deployment/kcca-kla-connect-web -n kcca-kla-connect

# Scale deployment
kubectl scale deployment kcca-kla-connect-web --replicas=3 -n kcca-kla-connect

# Delete everything
kubectl delete namespace kcca-kla-connect
```

---

## 🎉 Summary

This workflow allows you to:
- ✅ Deploy without cloning the repository on VPS
- ✅ Use GitHub Container Registry for image management
- ✅ Update applications by pushing new images
- ✅ Keep your VPS minimal (only kubectl and manifests)

The key is that **all application code is in the container image**, so the VPS only needs Kubernetes manifests to deploy it.


