# Required Dependencies for GHCR Deployment

## 🎯 Quick Summary

When pulling the image from GHCR, you need these dependencies ready on your VPS:

---

## ✅ What's Already in the Container Image

The following are **included** in the container image - you don't need to install them:

- ✅ Python 3.9+
- ✅ All Python packages (FastAPI, SQLAlchemy, Alembic, etc.)
- ✅ Application code
- ✅ PostgreSQL client tools (`pg_isready`)
- ✅ Firebase service account JSON file
- ✅ All system dependencies (gcc, build tools, etc.)

---

## 📦 What You Need on Your VPS

### 1. **Kubernetes Cluster** (Required)
- **k3s** (recommended for VPS)
- **microk8s** (alternative)
- **Full Kubernetes** (if preferred)

**Install k3s:**
```bash
curl -sfL https://get.k3s.io | sh -
```

### 2. **kubectl** (Required)
- Kubernetes command-line tool

**Install kubectl:**
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

### 3. **Storage Class** (Required)
- For PersistentVolumeClaims (uploads and database storage)
- k3s: Uses `local-path` by default ✅
- microk8s: Enable with `microk8s enable storage`

**Verify:**
```bash
kubectl get storageclass
```

### 4. **GHCR Pull Secret** (Required if image is private)
- GitHub Personal Access Token with `read:packages` permission

**Create secret:**
```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_PAT \
  --namespace=kcca-kla-connect
```

**Note:** If your image is public, skip this step and remove `imagePullSecrets` from deployment.yaml.

### 5. **Application Secrets** (Required)
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET` - JWT secret key
- `POSTGRES_PASSWORD` - Only if using in-cluster PostgreSQL

**Create secrets:**
```bash
kubectl create secret generic kcca-kla-connect-secrets \
  --from-literal=DATABASE_URL='postgresql://user:password@host:5432/klaconnect' \
  --from-literal=SECRET='your-strong-secret-key' \
  --from-literal=POSTGRES_PASSWORD='postgres-password' \
  --namespace=kcca-kla-connect
```

### 6. **PostgreSQL Database** (Required)
Choose **one** option:

#### Option A: In-Cluster PostgreSQL
- Deploy PostgreSQL using provided `postgres.yaml`
- Requires 20Gi storage for database
- Database automatically created

#### Option B: External/Managed Database (Recommended)
- AWS RDS, DigitalOcean, Google Cloud SQL, etc.
- Must be accessible from Kubernetes cluster
- Connection string in `DATABASE_URL` secret
- Deploy with `--skip-db` flag

**External Database Example:**
```bash
DATABASE_URL="postgresql://user:pass@external-db-host:5432/klaconnect?sslmode=require"
```

### 7. **Kubernetes Manifests** (Required)
Download from GitHub or use the deployment script:

```bash
# Option 1: Use deployment script (downloads automatically)
curl -sSL https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/deploy-ghcr-remote.sh -o deploy-ghcr-remote.sh
chmod +x deploy-ghcr-remote.sh

# Option 2: Download manually
curl -o namespace.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/namespace.yaml
curl -o configmap.yaml https://raw.githubusercontent.com/mutesasiratimo/kcca_kla_connect_api/main/k8s/configmap.yaml
# ... etc
```

---

## 📋 Minimum Setup Checklist

Before deploying, ensure you have:

- [ ] Kubernetes cluster installed and running
- [ ] kubectl installed and configured
- [ ] Storage class available
- [ ] GHCR pull secret created (if image is private)
- [ ] Application secrets created (DATABASE_URL, SECRET)
- [ ] PostgreSQL database ready (in-cluster or external)
- [ ] Kubernetes manifests downloaded

---

## 🚀 Deployment Commands

Once all dependencies are ready:

```bash
# Deploy using the script
./deploy-ghcr-remote.sh --no-confirm

# Or deploy manually
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f pvc-uploads.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

---

## 🔍 Verify Dependencies

**Before deployment:**
```bash
# 1. Check cluster
kubectl get nodes

# 2. Check storage
kubectl get storageclass

# 3. Check secrets
kubectl get secrets -n kcca-kla-connect

# 4. Test image pull (if private)
docker pull ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest
```

**After deployment:**
```bash
# Check deployment status
kubectl get all -n kcca-kla-connect

# Check logs
kubectl logs -f deployment/kcca-kla-connect-web -n kcca-kla-connect
```

---

## 📚 Additional Resources

- **Full checklist:** See [DEPENDENCIES_CHECKLIST.md](./DEPENDENCIES_CHECKLIST.md)
- **Deployment guide:** See [GHCR_VPS_DEPLOYMENT.md](./GHCR_VPS_DEPLOYMENT.md)
- **Quick start:** See [QUICK_START_GHCR.md](./QUICK_START_GHCR.md)

---

## 💡 Key Points

1. **Container image includes:** All code, dependencies, and tools
2. **VPS needs:** Only Kubernetes, kubectl, and configuration
3. **Database:** Can be in-cluster or external
4. **No repo needed:** Everything deploys from GHCR and GitHub manifests
5. **Storage:** Automatic with k3s/local-path

---

## 🆘 Common Issues

**Image pull fails:**
- Check GHCR pull secret is created
- Verify PAT has `read:packages` permission
- Check if image is public/private

**Database connection fails:**
- Verify DATABASE_URL is correct
- Check database is accessible from cluster
- For external DB: Check firewall rules

**Storage issues:**
- Verify storage class exists: `kubectl get storageclass`
- Check PVC status: `kubectl get pvc -n kcca-kla-connect`










