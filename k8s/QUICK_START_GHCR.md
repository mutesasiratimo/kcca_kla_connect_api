# Quick Start: Deploy to VPS from GHCR

This is a condensed guide for deploying to a VPS using GitHub Container Registry **without cloning the repository**.

## 🎯 Prerequisites

1. **VPS with Kubernetes** (k3s recommended)
2. **GitHub Personal Access Token** (PAT) with `read:packages` permission
3. **kubectl** installed and configured on VPS

## ⚡ Quick Deployment (5 minutes)

### 1. Set Up Kubernetes on VPS

```bash
# SSH into VPS
ssh user@your-vps-ip

# Install k3s
curl -sfL https://get.k3s.io | sh -
sudo systemctl enable k3s

# Configure kubectl
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config

# Verify
kubectl get nodes
```

### 2. Create GHCR Pull Secret

```bash
# Replace YOUR_GITHUB_USERNAME and YOUR_GITHUB_PAT
kubectl create namespace kcca-kla-connect
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_PAT \
  --namespace=kcca-kla-connect
```

### 3. Deploy Application

**Option A: Using the Deployment Script (Recommended)**

```bash
# Download and run the deployment script
curl -sSL https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/deploy-ghcr-remote.sh -o deploy-ghcr-remote.sh
chmod +x deploy-ghcr-remote.sh
./deploy-ghcr-remote.sh --no-confirm
```

**Option B: Using kubectl Directly**

```bash
# Download manifests
mkdir -p ~/k8s-manifests && cd ~/k8s-manifests
curl -o namespace.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/namespace.yaml
curl -o configmap.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/configmap.yaml
curl -o pvc-uploads.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/pvc-uploads.yaml
curl -o deployment.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/deployment.yaml
curl -o service.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/service.yaml

# Create secrets (CHANGE VALUES!)
kubectl create secret generic kcca-kla-connect-secrets \
  --from-literal=DATABASE_URL='postgresql://user:pass@host:5432/klaconnect' \
  --from-literal=SECRET='your-secret-key' \
  --namespace=kcca-kla-connect

# Deploy
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f pvc-uploads.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Check status
kubectl get all -n kcca-kla-connect
```

### 4. Access Your Application

```bash
# Get service info
kubectl get svc -n kcca-kla-connect

# For testing (port-forward)
kubectl port-forward -n kcca-kla-connect service/kcca-kla-connect-internal 8000:8000
# Visit: http://localhost:8000/docs

# For production (expose via NodePort or Ingress)
kubectl patch svc kcca-kla-connect-service -n kcca-kla-connect -p '{"spec":{"type":"NodePort"}}'
kubectl get svc kcca-kla-connect-service -n kcca-kla-connect
# Access: http://YOUR_VPS_IP:NODEPORT/docs
```

## 🔄 Updating the Application

When you push a new image to GHCR:

```bash
# Restart deployment to pull latest image
kubectl rollout restart deployment/kcca-kla-connect-web -n kcca-kla-connect

# Or update to specific tag
kubectl set image deployment/kcca-kla-connect-web \
  web=ghcr.io/mutesasiratimo/kcca_kla_connect_api:v1.0.0 \
  -n kcca-kla-connect
```

## 📚 Next Steps

- See [GHCR_VPS_DEPLOYMENT.md](./GHCR_VPS_DEPLOYMENT.md) for detailed guide
- See [VPS_DEPLOYMENT.md](./VPS_DEPLOYMENT.md) for alternative deployment methods

## 🐛 Troubleshooting

```bash
# Check pods
kubectl get pods -n kcca-kla-connect

# View logs
kubectl logs -f deployment/kcca-kla-connect-web -n kcca-kla-connect

# Check events
kubectl describe pod -l app=kcca-kla-connect -n kcca-kla-connect

# Verify image pull secret
kubectl get secret ghcr-pull-secret -n kcca-kla-connect
```


