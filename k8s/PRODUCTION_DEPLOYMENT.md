# Production Cloud Deployment Guide

This guide walks you through deploying to a production cloud Kubernetes environment.

## 📋 Overview: Local vs Production

| Aspect | Local (kind) | Production Cloud |
|--------|--------------|------------------|
| **Kubernetes Cluster** | kind (local Docker) | Managed K8s (EKS, GKE, AKS, DOKS) |
| **Container Registry** | Load into kind directly | Push to registry (ECR, GCR, ACR, Docker Hub) |
| **Image Pull** | `imagePullPolicy: IfNotPresent` | `imagePullPolicy: Always` (use version tags) |
| **LoadBalancer** | Pending (use port-forward) | Real external IP automatically |
| **Database** | In-cluster PostgreSQL | Managed DB (RDS, Cloud SQL, DigitalOcean DB) |
| **Secrets** | Local kubectl secrets | Secret Manager (AWS Secrets Manager, etc.) |
| **Storage** | Local PVC | Cloud storage (EBS, Persistent Disk, etc.) |
| **Ingress** | Optional | Required (with TLS/HTTPS) |
| **Monitoring** | None | Required (CloudWatch, Stackdriver, etc.) |

---

## 🎯 Step-by-Step Production Setup

### Step 1: Choose Your Cloud Provider

**Options:**
- **AWS**: EKS (Elastic Kubernetes Service)
- **Google Cloud**: GKE (Google Kubernetes Engine)
- **Azure**: AKS (Azure Kubernetes Service)
- **DigitalOcean**: DOKS (DigitalOcean Kubernetes)
- **Others**: Linode, Vultr, etc.

**Recommended for your setup**: **DigitalOcean** (you already use DigitalOcean for database)

---

### Step 2: Container Registry Setup

You need to push your Docker image to a registry that Kubernetes can pull from.

#### Option A: Docker Hub (Easiest)

```bash
# Login
docker login

# Build and tag
docker build -t your-dockerhub-username/kcca-kla-connect-api:latest .
docker build -t your-dockerhub-username/kcca-kla-connect-api:v1.0.0 .

# Push
docker push your-dockerhub-username/kcca-kla-connect-api:latest
docker push your-dockerhub-username/kcca-kla-connect-api:v1.0.0
```

#### Option B: DigitalOcean Container Registry

```bash
# Install doctl
brew install doctl

# Login
doctl auth init
doctl registry login

# Create registry (if needed)
doctl registry create kcca-kla-connect-registry

# Build and tag
docker build -t registry.digitalocean.com/kcca-kla-connect-registry/kcca-kla-connect-api:latest .
docker tag kcca-kla-connect-api:latest registry.digitalocean.com/kcca-kla-connect-registry/kcca-kla-connect-api:v1.0.0

# Push
docker push registry.digitalocean.com/kcca-kla-connect-registry/kcca-kla-connect-api:latest
docker push registry.digitalocean.com/kcca-kla-connect-registry/kcca-kla-connect-api:v1.0.0
```

#### Option C: AWS ECR, Google GCR, Azure ACR

Similar process - use provider-specific commands.

---

### Step 3: Create Production Kubernetes Cluster

#### DigitalOcean (Recommended)

```bash
# Create cluster via CLI
doctl kubernetes cluster create kcca-kla-connect-prod \
  --region nyc1 \
  --node-pool "name=worker-pool;size=s-2vcpu-4gb;count=2" \
  --version 1.34.0

# Get kubeconfig
doctl kubernetes cluster kubeconfig save kcca-kla-connect-prod
```

#### Or use DigitalOcean Dashboard
1. Go to Kubernetes → Create Cluster
2. Choose region, node size, node count
3. Download kubeconfig or use `doctl` command above

---

### Step 4: Configure Image Pull Secrets (if using private registry)

For private registries (DigitalOcean, ECR, GCR, ACR):

```bash
# DigitalOcean
doctl registry kubernetes-manifest | kubectl apply -f -

# Or create secret manually
kubectl create secret docker-registry regcred \
  --docker-server=registry.digitalocean.com \
  --docker-username=<your-token> \
  --docker-password=<your-token> \
  --docker-email=<your-email> \
  --namespace=kcca-kla-connect
```

---

### Step 5: Update Production Configurations

Key files to update:
1. `deployment.yaml` - Update image, imagePullPolicy, add imagePullSecrets
2. `postgres.yaml` - Use managed database (or keep in-cluster)
3. `service.yaml` - LoadBalancer will work automatically
4. `ingress.yaml` - Configure TLS/HTTPS
5. Secrets - Use cloud secret manager or secure kubectl

---

### Step 6: Use Managed Database (Recommended)

You already have DigitalOcean database. Update your deployment:

**Current (from model.py):**
```
LIVE_DATABASE_URL = "postgresql://doadmin:...@db-postgresql-nyc3-89277-do-user-11136722-0.b.db.ondigitalocean.com:25060/klaconnect?sslmode=require"
```

**In Kubernetes Secrets:**
```bash
kubectl create secret generic kcca-kla-connect-secrets \
  --from-literal=DATABASE_URL='postgresql://doadmin:YOUR_PASSWORD@db-postgresql-nyc3-89277-do-user-11136722-0.b.db.ondigitalocean.com:25060/klaconnect?sslmode=require' \
  --from-literal=SECRET='your-production-secret-key' \
  --namespace=kcca-kla-connect
```

**Then skip PostgreSQL deployment:**
- Don't apply `postgres.yaml` in production
- Use only the managed database

---

### Step 7: Deploy with Production Configurations

Use the production-specific deployment files or update existing ones.

---

## 🔐 Production Security Checklist

- [ ] Use versioned image tags (not `:latest`)
- [ ] `imagePullPolicy: Always` in production
- [ ] Secrets stored in secret manager (not in code)
- [ ] TLS/HTTPS enabled via Ingress
- [ ] Database uses SSL/TLS connections
- [ ] Resource limits set appropriately
- [ ] Network policies configured
- [ ] Monitoring and logging set up
- [ ] Backup strategy implemented
- [ ] Disaster recovery plan

---

## 📊 Production Considerations

### Resource Sizing
- **Development**: 2 nodes, 2 vCPU, 4GB RAM each
- **Production**: 3+ nodes, 4+ vCPU, 8GB+ RAM each
- Auto-scaling enabled

### High Availability
- Multi-zone node distribution
- PodDisruptionBudget configured
- Minimum 2 replicas (recommend 3+)

### Monitoring
- Cloud provider monitoring (DigitalOcean Metrics, CloudWatch, etc.)
- Application logs aggregation
- Error tracking (Sentry, etc.)

### Backups
- Database backups (managed by provider or custom)
- Application data backups
- Disaster recovery testing

---

## 🚀 Next Steps

1. Review the production configuration files
2. Set up container registry
3. Create production cluster
4. Update configurations for your environment
5. Deploy and test

See `PRODUCTION_CONFIGURATION.md` for detailed production manifests.


