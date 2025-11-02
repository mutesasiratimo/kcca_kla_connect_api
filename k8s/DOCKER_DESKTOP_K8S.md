# Using Docker Desktop Kubernetes Instead of kind

If you prefer to use Docker Desktop's built-in Kubernetes (visible in Docker Desktop UI):

## Enable Docker Desktop Kubernetes

1. Open **Docker Desktop**
2. Go to **Settings** (gear icon)
3. Navigate to **Kubernetes**
4. Check **"Enable Kubernetes"**
5. Click **"Apply & Restart"**

## Deploy to Docker Desktop Kubernetes

Once enabled, Docker Desktop creates a context called `docker-desktop`:

```bash
# Switch to Docker Desktop context
kubectl config use-context docker-desktop

# Verify
kubectl cluster-info

# Deploy as normal
cd k8s
kubectl create namespace kcca-kla-connect
kubectl create secret generic kcca-kla-connect-secrets \
  --from-literal=DATABASE_URL='postgresql://postgres:password@postgres-service:5432/klaconnect' \
  --from-literal=SECRET='your-secret-key' \
  --from-literal=POSTGRES_PASSWORD='password' \
  --namespace=kcca-kla-connect

# Build and load image (Docker Desktop can use local images)
docker build -t kcca-kla-connect-api-web:latest .

# Deploy all resources
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f pvc-uploads.yaml
kubectl apply -f postgres.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml  # Can use LoadBalancer or NodePort
```

## Access Resources in Docker Desktop UI

- Open Docker Desktop
- Click **"Kubernetes"** tab
- You'll see:
  - Namespaces
  - Workloads (Deployments, Pods, etc.)
  - Services
  - Config & Secrets
  - Storage

## Switching Between Clusters

```bash
# List available contexts
kubectl config get-contexts

# Switch to Docker Desktop
kubectl config use-context docker-desktop

# Switch to kind
kubectl config use-context kind-kcca-kla-connect

# Use specific context for a command
kubectl get pods --context=docker-desktop
kubectl get pods --context=kind-kcca-kla-connect
```

## Comparison

| Feature | kind | Docker Desktop K8s |
|---------|------|---------------------|
| Visible in Docker Desktop UI | Containers only | Full Kubernetes UI |
| Lightweight | Yes | Yes |
| Multiple clusters | Easy | Requires switching |
| Production-like | Yes | Yes |
| Resource usage | Lower | Similar |

## Recommendation

- **For development and UI management**: Use Docker Desktop Kubernetes
- **For testing multi-cluster scenarios**: Use kind
- **Both work fine**: Choose based on preference

