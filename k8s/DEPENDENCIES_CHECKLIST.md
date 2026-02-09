# Dependencies Checklist for GHCR Deployment

This checklist covers all dependencies and prerequisites needed when deploying from GitHub Container Registry (GHCR) to your VPS.

---

## 🔧 Infrastructure Dependencies

### 1. Kubernetes Cluster
- [ ] **k3s** (recommended) or **microk8s** or full **Kubernetes** installed
- [ ] Cluster is running and accessible
- [ ] Verify with: `kubectl get nodes`

### 2. kubectl CLI
- [ ] **kubectl** installed on VPS
- [ ] `kubectl` configured to connect to your cluster
- [ ] Verify with: `kubectl cluster-info`

### 3. Storage Class
- [ ] Storage class available for PersistentVolumeClaims
  - k3s: Uses `local-path` by default
  - microk8s: Enable with `microk8s enable storage`
  - Cloud providers: Usually `standard`, `gp2`, `gp3`, etc.
- [ ] Verify: `kubectl get storageclass`
- [ ] Update `storageClassName` in `pvc-uploads.yaml` and `postgres.yaml` if needed

---

## 🔐 Authentication & Secrets

### 4. GHCR Pull Secret (Required for Private Images)
- [ ] GitHub Personal Access Token (PAT) created
  - Permissions needed: `read:packages`
  - Create at: https://github.com/settings/tokens
- [ ] GHCR pull secret created in Kubernetes:
  ```bash
  kubectl create secret docker-registry ghcr-pull-secret \
    --docker-server=ghcr.io \
    --docker-username=YOUR_GITHUB_USERNAME \
    --docker-password=YOUR_GITHUB_PAT \
    --namespace=kcca-kla-connect
  ```
- [ ] **Note**: If your image is public, you can skip this step and remove `imagePullSecrets` from deployment.yaml

### 5. Application Secrets
- [ ] **DATABASE_URL** - PostgreSQL connection string
  - Format: `postgresql://user:password@host:port/database`
  - Example: `postgresql://postgres:mypass@postgres-service:5432/klaconnect`
- [ ] **SECRET** - JWT secret key (use a strong random string)
- [ ] **POSTGRES_PASSWORD** - Only needed if deploying in-cluster PostgreSQL

Create the secret:
```bash
kubectl create secret generic kcca-kla-connect-secrets \
  --from-literal=DATABASE_URL='postgresql://user:pass@host:5432/klaconnect' \
  --from-literal=SECRET='your-strong-secret-key-here' \
  --from-literal=POSTGRES_PASSWORD='postgres-password' \
  --namespace=kcca-kla-connect
```

---

## 🗄️ Database Dependencies

### Option A: In-Cluster PostgreSQL (Included in Deployment)

If using the provided `postgres.yaml`:
- [ ] PostgreSQL StatefulSet deployed
- [ ] PostgreSQL PVC created (20Gi minimum)
- [ ] PostgreSQL service accessible at `postgres-service:5432`
- [ ] Database initialized with name: `klaconnect`
- [ ] Database user: `postgres`
- [ ] Database password set in secrets

### Option B: External/Managed Database (Recommended for Production)

If using external database (AWS RDS, DigitalOcean, etc.):
- [ ] External PostgreSQL database provisioned
- [ ] Database name: `klaconnect` (or your custom name)
- [ ] Database user and password configured
- [ ] Database accessible from Kubernetes cluster
  - Network/firewall rules allow connections
  - For managed services, may need VPC peering or allowed IPs
- [ ] Connection string configured in `DATABASE_URL` secret
- [ ] SSL mode configured if required (add `?sslmode=require` to DATABASE_URL)
- [ ] Deploy with `--skip-db` flag to skip in-cluster PostgreSQL

**Example External Database Connection:**
```bash
# DigitalOcean Managed Database
DATABASE_URL="postgresql://doadmin:password@db-postgresql-nyc3-12345-do-user-12345-0.b.db.ondigitalocean.com:25060/klaconnect?sslmode=require"

# AWS RDS
DATABASE_URL="postgresql://user:pass@your-rds-endpoint.region.rds.amazonaws.com:5432/klaconnect"
```

---

## 📦 Application Dependencies (Inside Container)

These are **already included** in the container image - you don't need to install them separately:

- ✅ Python 3.9+
- ✅ All Python packages from `requirements.txt`
- ✅ FastAPI, SQLAlchemy, Alembic, etc.
- ✅ Application code

---

## 🔑 Optional: Additional Service Dependencies

### 6. Firebase Service Account (If using Firebase features)

If your application uses Firebase:
- [ ] Firebase service account JSON file: `ug-kla-konnect-firebase-adminsdk-fbsvc-f2479ab9d6.json`
- [ ] File must be **included in the container image** (already in your Dockerfile)
- [ ] Or mount as a secret if not in image:
  ```bash
  kubectl create secret generic firebase-credentials \
    --from-file=service-account.json=./ug-kla-konnect-firebase-adminsdk-fbsvc-f2479ab9d6.json \
    --namespace=kcca-kla-connect
  ```
- [ ] Update deployment.yaml to mount the secret if using external file

**Note**: Currently, your Dockerfile copies this file into the image, so it should already be available.

### 7. Email Configuration (If using email features)

Email settings are **hardcoded in the application code** (`app/send_mail.py`):
- ⚠️ **Gmail SMTP credentials** are in code (consider moving to secrets)
- Current config uses: `mutestimo72@gmail.com`
- For production, consider:
  - Moving email credentials to Kubernetes secrets
  - Using environment variables for email configuration
  - Using a dedicated email service (SendGrid, AWS SES, etc.)

---

## 🌐 Network & Access Dependencies

### 8. Service Configuration
- [ ] Service type configured (LoadBalancer, NodePort, or ClusterIP)
- [ ] Port 8000 exposed
- [ ] LoadBalancer IP allocated (if using LoadBalancer)
- [ ] Or NodePort assigned (if using NodePort)

### 9. Ingress (Optional, for Domain/DNS)
- [ ] Ingress controller installed (Traefik for k3s, NGINX for others)
- [ ] Ingress resource configured
- [ ] DNS record pointing to cluster IP/LoadBalancer
- [ ] TLS certificate configured (cert-manager, Let's Encrypt, etc.)

---

## 📋 Kubernetes Resources Checklist

Deploy these resources in order:

- [ ] **Namespace** - `kcca-kla-connect`
- [ ] **GHCR Pull Secret** - `ghcr-pull-secret` (if using private image)
- [ ] **Application Secrets** - `kcca-kla-connect-secrets`
- [ ] **ConfigMap** - `kcca-kla-connect-config`
- [ ] **PVC for Uploads** - `kcca-kla-connect-uploads-pvc` (10Gi)
- [ ] **PostgreSQL PVC** - `postgres-pvc` (20Gi) - Only if using in-cluster DB
- [ ] **PostgreSQL Service** - `postgres-service` - Only if using in-cluster DB
- [ ] **PostgreSQL StatefulSet** - `postgres` - Only if using in-cluster DB
- [ ] **Application Deployment** - `kcca-kla-connect-web`
- [ ] **Application Service** - `kcca-kla-connect-service`
- [ ] **Internal Service** - `kcca-kla-connect-internal` (optional)
- [ ] **Ingress** - `kcca-kla-connect-ingress` (optional)

---

## ✅ Pre-Deployment Verification

Before deploying, verify:

```bash
# 1. Cluster connectivity
kubectl cluster-info
kubectl get nodes

# 2. Storage class available
kubectl get storageclass

# 3. Namespace exists
kubectl get namespace kcca-kla-connect

# 4. Secrets exist
kubectl get secrets -n kcca-kla-connect

# 5. GHCR image is accessible (if private)
# Test on VPS:
docker pull ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest
# Or configure docker login first:
echo $GITHUB_PAT | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# 6. Database connectivity (if external)
# From a pod or test container:
psql "postgresql://user:pass@host:port/database"
```

---

## 🚀 Quick Deployment Command

Once all dependencies are ready:

```bash
# Option 1: Using the remote deployment script
curl -sSL https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/deploy-ghcr-remote.sh -o deploy-ghcr-remote.sh
chmod +x deploy-ghcr-remote.sh
./deploy-ghcr-remote.sh --no-confirm

# Option 2: Using kubectl directly
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f pvc-uploads.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

---

## 🔍 Post-Deployment Verification

After deployment, verify:

```bash
# Check all resources
kubectl get all -n kcca-kla-connect

# Check pod status
kubectl get pods -n kcca-kla-connect

# Check pod logs
kubectl logs -f deployment/kcca-kla-connect-web -n kcca-kla-connect

# Check database connection (if using in-cluster PostgreSQL)
kubectl exec -it deployment/kcca-kla-connect-web -n kcca-kla-connect -- pg_isready -h postgres-service -p 5432

# Test API endpoint
kubectl port-forward -n kcca-kla-connect service/kcca-kla-connect-internal 8000:8000
# Visit: http://localhost:8000/docs
```

---

## 📝 Summary

**Minimum Required Dependencies:**
1. ✅ Kubernetes cluster (k3s/microk8s/K8s)
2. ✅ kubectl installed and configured
3. ✅ GHCR pull secret (if image is private)
4. ✅ Application secrets (DATABASE_URL, SECRET)
5. ✅ PostgreSQL database (in-cluster or external)
6. ✅ Storage class for PVCs
7. ✅ ConfigMap for application config

**Optional Dependencies:**
- Firebase service account (if using Firebase features)
- Email SMTP configuration (currently in code)
- Ingress controller (for domain/DNS access)
- TLS certificates (for HTTPS)

---

## 🆘 Troubleshooting

If deployment fails, check:

1. **Image Pull Errors:**
   - Verify GHCR pull secret exists and is correct
   - Check if image is public or private
   - Test image pull manually: `docker pull ghcr.io/...`

2. **Database Connection Errors:**
   - Verify DATABASE_URL is correct
   - Check database is accessible from cluster
   - For external DB: Check firewall/network rules
   - For in-cluster DB: Check PostgreSQL pod is running

3. **Storage Errors:**
   - Verify storage class exists
   - Check PVC status: `kubectl get pvc -n kcca-kla-connect`
   - Verify storage class matches in manifests

4. **Pod Not Starting:**
   - Check pod logs: `kubectl logs <pod-name> -n kcca-kla-connect`
   - Check pod events: `kubectl describe pod <pod-name> -n kcca-kla-connect`
   - Verify all secrets and configmaps exist


