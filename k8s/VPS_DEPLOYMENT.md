# VPS/Server Deployment Guide

This guide is for deploying to a provisioned Linux server with a public IP address. This is similar to local deployment but on a remote server.

## 🚀 Quick Start: Deploy from GHCR (No Repository Needed)

**If you're using GitHub Container Registry (GHCR)**, see **[GHCR_VPS_DEPLOYMENT.md](./GHCR_VPS_DEPLOYMENT.md)** for deploying without cloning the repository on your VPS. This is the recommended approach for production deployments.

Quick command:
```bash
# On VPS, download and run the deployment script
curl -sSL https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/deploy-ghcr-remote.sh -o deploy-ghcr-remote.sh
chmod +x deploy-ghcr-remote.sh
./deploy-ghcr-remote.sh --no-confirm
```

---

## 🎯 Overview

You have:
- ✅ Linux server with public IP
- ✅ SSH access
- ✅ Root/sudo access

Options for Kubernetes:
1. **k3s** (Recommended) - Lightweight, single-command install
2. **MicroK8s** - Ubuntu-friendly, snap-based
3. **kubeadm** - Full Kubernetes, more complex
4. **Docker Compose** - Simpler alternative (no Kubernetes)

---

## 🚀 Option 1: k3s (Recommended)

k3s is perfect for single-server deployments - lightweight and easy to manage.

### Step 1: Install k3s on Server

```bash
# SSH into your server
ssh user@your-server-ip

# Install k3s (as root or with sudo)
curl -sfL https://get.k3s.io | sh -

# Check status
sudo systemctl status k3s

# Get kubeconfig
sudo cat /etc/rancher/k3s/k3s.yaml
```

### Step 2: Configure kubectl Locally

On your **local machine**, copy the kubeconfig:

```bash
# Save server kubeconfig locally
mkdir -p ~/.kube/configs
# Copy the output from server's k3s.yaml to a file
# Then merge or use with KUBECONFIG env var
```

Or use kubectl remotely:

```bash
# Install kubectl on server
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

### Step 3: Make k3s Accessible Remotely (Optional)

By default, k3s binds to localhost. To access from your local machine:

```bash
# On server, edit k3s service
sudo nano /etc/systemd/system/k3s.service

# Add these flags to the ExecStart line:
# --bind-address 0.0.0.0 --node-external-ip YOUR_SERVER_IP

# Or create /etc/rancher/k3s/config.yaml:
write-default-kubeconfig: true
bind-address: "0.0.0.0"
node-external-ip: "YOUR_SERVER_PUBLIC_IP"

# Restart
sudo systemctl restart k3s
```

### Step 4: Deploy Using Local Deployment Scripts

Since it's similar to local deployment, you can use the existing scripts:

```bash
# Option A: Build on server and deploy
ssh user@your-server-ip
cd /path/to/project
make deploy  # Uses deploy-full.sh

# Option B: Use kubectl from local machine
# Configure kubectl to point to server, then:
make deploy-no-cluster  # Skip cluster creation
```

---

## 🔧 Option 2: MicroK8s (Ubuntu/Debian)

Good for Ubuntu servers, managed via snap.

### Step 1: Install MicroK8s

```bash
# SSH into server
ssh user@your-server-ip

# Install
sudo snap install microk8s --classic

# Add user to microk8s group
sudo usermod -a -G microk8s $USER
sudo chown -R $USER ~/.kube
newgrp microk8s

# Enable addons
microk8s enable dns storage ingress
```

### Step 2: Configure kubectl

```bash
# MicroK8s includes kubectl as 'microk8s kubectl'
# Create alias
echo "alias kubectl='microk8s kubectl'" >> ~/.bashrc
source ~/.bashrc

# Or use microk8s kubectl directly
microk8s kubectl get nodes
```

---

## 📦 Deployment Options

### Option A: Build on Server

```bash
# SSH to server
ssh user@your-server-ip

# Clone/copy your project
git clone <your-repo>
cd kcca_kla_connect_api

# Install Docker if not installed
# Then deploy
make deploy  # This will create kind cluster OR use existing k3s/microk8s
```

**Note**: If using k3s/microk8s, modify `deploy-full.sh` to skip cluster creation.

### Option B: Build Locally, Deploy Remotely

```bash
# On local machine
# Build image
docker build -t kcca-kla-connect-api-web:latest .

# Save image
docker save kcca-kla-connect-api-web:latest | gzip > kcca-api.tar.gz

# Copy to server
scp kcca-api.tar.gz user@your-server-ip:/tmp/

# On server
ssh user@your-server-ip
docker load < /tmp/kcca-api.tar.gz
# Or for k3s: use k3s's containerd
k3s ctr images import /tmp/kcca-api.tar.gz

# Deploy
cd kcca_kla_connect_api
make deploy-no-cluster
```

### Option C: Use Container Registry (Recommended for Production)

Even on VPS, using a registry is cleaner:

```bash
# On local machine
make build-push REGISTRY=your-registry.io TAG=v1.0.0

# On server
# Configure kubectl to use registry credentials if private
make deploy-prod REGISTRY=your-registry.io TAG=v1.0.0
```

---

## 🔄 Modified Deployment Script for VPS

Since you have a server (not managed K8s), you can use a hybrid approach:

1. **k3s/MicroK8s on server** (one-time setup)
2. **Use local deployment scripts** but point kubectl to server
3. **Or modify deploy scripts** to work with existing cluster

---

## 🌐 Access from Internet

Once deployed, your API will be accessible via server's public IP:

### Using LoadBalancer Service

For k3s, you may need to install a LoadBalancer provider:

```bash
# Install MetalLB for k3s
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.12/config/manifests/metallb-native.yaml

# Configure IP pool (use your server's IP range)
```

Or use **NodePort** and access directly:

```bash
# Modify service to NodePort
kubectl patch svc kcca-kla-connect-service -n kcca-kla-connect -p '{"spec":{"type":"NodePort"}}'

# Get NodePort
kubectl get svc kcca-kla-connect-service -n kcca-kla-connect

# Access: http://YOUR_SERVER_IP:NODEPORT/docs
```

### Using Ingress

For k3s, Traefik is installed by default:

```bash
# k3s includes Traefik ingress controller
# Just deploy your ingress.yaml and point DNS to server IP
```

---

## 🔐 Security Considerations for VPS

1. **Firewall Rules**
   ```bash
   # Allow only necessary ports
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 80/tcp   # HTTP
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw allow 6443/tcp # Kubernetes API (if accessing remotely)
   sudo ufw enable
   ```

2. **Secure Kubernetes API**
   - Don't expose k3s API port (6443) to internet
   - Use SSH tunnel or VPN for kubectl access
   - Or use kubectl port-forward through SSH

3. **TLS/HTTPS**
   - Use cert-manager with Let's Encrypt
   - Or use Cloudflare in front of your server

---

## 📝 Recommended Setup for Your Scenario

**Best approach for VPS with public IP:**

1. **Install k3s on server** (one command)
2. **Use Docker Hub or DigitalOcean Registry** (easy image management)
3. **Build locally, push to registry, deploy on server**
4. **Use NodePort or Ingress** for external access

### Quick Setup Commands

```bash
# On Server
curl -sfL https://get.k3s.io | sh -
sudo systemctl enable k3s
sudo systemctl start k3s

# Install kubectl on server (or use k3s kubectl)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Configure
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config

# Test
kubectl get nodes
```

Then deploy using the existing scripts!

---

## 🔗 Remote kubectl Access

If you want to manage from your local machine:

### Method 1: SSH Tunnel

```bash
# Create SSH tunnel
ssh -L 6443:localhost:6443 user@your-server-ip

# In another terminal, configure kubectl
# Edit ~/.kube/config to use localhost:6443
```

### Method 2: Copy kubeconfig

```bash
# On server
cat ~/.kube/config

# On local machine, merge into ~/.kube/config
# Or set KUBECONFIG environment variable
export KUBECONFIG=/path/to/server-kubeconfig
```

---

## 💡 Simplest Workflow

```bash
# 1. Install k3s on server (one command)
ssh user@server "curl -sfL https://get.k3s.io | sh -"

# 2. Build and push image (from local machine)
make build-push REGISTRY=your-dockerhub-username TAG=v1.0.0

# 3. Deploy on server (via SSH or direct on server)
ssh user@server "cd kcca_kla_connect_api && make deploy-prod REGISTRY=your-dockerhub-username TAG=v1.0.0"

# 4. Access API
# http://YOUR_SERVER_IP:NODEPORT/docs
# or via Ingress if configured
```

This gives you production-like setup but with full control on your VPS!

---

## 🧪 Testing `make deploy-vps` Locally

You can test `make deploy-vps` on your local machine if you have a Kubernetes cluster running (kind, minikube, k3s, etc.):

### Non-Interactive Testing with Environment Variables

```bash
# Test with NO_CONFIRM to skip prompts
NO_CONFIRM=true make deploy-vps

# Test with skip build (if image already exists)
NO_CONFIRM=true SKIP_BUILD=true make deploy-vps

# Test with registry image (simulates production)
NO_CONFIRM=true REGISTRY=your-dockerhub-username IMAGE_TAG=v1.0.0 make deploy-vps

# Test without database deployment (use external/managed DB)
NO_CONFIRM=true SKIP_DB=true make deploy-vps

# Combined: Production-like testing
NO_CONFIRM=true SKIP_BUILD=true REGISTRY=your-dockerhub-username IMAGE_TAG=v1.0.0 SKIP_DB=true make deploy-vps
```

### Available Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `NO_CONFIRM` | Skip confirmation prompts | `false` | `NO_CONFIRM=true` |
| `SKIP_BUILD` | Skip Docker build step | `false` | `SKIP_BUILD=true` |
| `REGISTRY` | Container registry URL | (empty) | `REGISTRY=your-registry.io` |
| `IMAGE_TAG` | Image tag/version | `latest` | `IMAGE_TAG=v1.0.0` |
| `SKIP_DB` | Skip PostgreSQL deployment | `false` | `SKIP_DB=true` |

### Testing Workflow

```bash
# 1. Ensure you have a Kubernetes cluster (kind, minikube, k3s, etc.)
kubectl cluster-info

# 2. Test non-interactive deployment
NO_CONFIRM=true make deploy-vps

# 3. Test with registry (if you have one set up)
NO_CONFIRM=true REGISTRY=your-username make deploy-vps

# 4. Verify deployment
kubectl get all -n kcca-kla-connect

# 5. Test access
make port-forward
# Then visit: http://localhost:8000/docs
```

---

## 🏭 Production Server Usage

Yes, `make deploy-vps` is designed to run on production servers! Here's how:

### Prerequisites on Production Server

1. **Install k3s or microk8s**
   ```bash
   # k3s (recommended)
   curl -sfL https://get.k3s.io | sh -
   sudo systemctl enable k3s
   
   # OR microk8s (Ubuntu)
   sudo snap install microk8s --classic
   microk8s enable dns storage ingress
   ```

2. **Configure kubectl**
   ```bash
   # For k3s
   mkdir -p ~/.kube
   sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
   sudo chown $USER ~/.kube/config
   
   # For microk8s
   microk8s kubectl config view --raw > ~/.kube/config
   ```

3. **Install Docker** (if building locally)
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install docker.io
   sudo usermod -aG docker $USER
   ```

### Production Deployment Options

#### Option A: Build on Server, Deploy Locally
```bash
# On server
cd /path/to/kcca_kla_connect_api
NO_CONFIRM=true make deploy-vps
```

#### Option B: Use Container Registry (Recommended)
```bash
# From local machine: Build and push
make build-push REGISTRY=your-registry.io TAG=v1.0.0

# On server: Deploy from registry
NO_CONFIRM=true REGISTRY=your-registry.io IMAGE_TAG=v1.0.0 SKIP_BUILD=true make deploy-vps
```

#### Option C: Use External Database
```bash
# Create secret with external database connection
kubectl create secret generic kcca-kla-connect-secrets \
  --from-literal=DATABASE_URL='postgresql://user:pass@external-db:5432/db' \
  --from-literal=SECRET='your-production-secret' \
  --namespace=kcca-kla-connect

# Deploy without database
NO_CONFIRM=true SKIP_DB=true SKIP_BUILD=true REGISTRY=your-registry.io make deploy-vps
```

### Production Checklist

- [ ] Use versioned image tags (not `:latest`)
- [ ] Set `REGISTRY` to a production registry
- [ ] Use `SKIP_DB=true` with external/managed database
- [ ] Set proper secrets before deployment
- [ ] Configure firewall rules
- [ ] Set up TLS/HTTPS via Ingress
- [ ] Configure monitoring and logging
- [ ] Set up automated backups

### Example Production Deployment

```bash
# On production server
export NO_CONFIRM=true
export REGISTRY=registry.digitalocean.com/your-registry
export IMAGE_TAG=v1.2.3
export SKIP_BUILD=true
export SKIP_DB=true

make deploy-vps
```

This will:
- Deploy to your existing k3s/microk8s cluster
- Pull image from registry
- Skip database deployment (use external DB)
- Skip all prompts
- Work in CI/CD pipelines

