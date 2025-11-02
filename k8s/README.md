# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the KCCA Kla Connect API.

## Prerequisites

1. **Kubernetes Cluster** (one of the following):
   - Local: [minikube](https://minikube.sigs.k8s.io/), [kind](https://kind.sigs.k8s.io/), or [Docker Desktop Kubernetes](https://www.docker.com/products/docker-desktop)
   - Cloud: AWS EKS, Google GKE, Azure AKS, or other managed Kubernetes service
   - On-premises: Configured Kubernetes cluster

2. **kubectl** installed and configured to access your cluster

3. **Container Image**: Build and push your Docker image to a container registry:
   ```bash
   # Build the image
   docker build -t kcca-kla-connect-api-web:latest .
   
   # For cloud deployments, tag and push to registry:
   # docker tag kcca-kla-connect-api-web:latest your-registry.io/kcca-kla-connect-api-web:v1.0.0
   # docker push your-registry.io/kcca-kla-connect-api-web:v1.0.0
   ```

4. **Load Balancer Controller** (for LoadBalancer services):
   - AWS: AWS Load Balancer Controller
   - GCP: Built-in (no setup needed)
   - Azure: Azure Load Balancer

5. **Ingress Controller** (optional, for Ingress):
   - NGINX Ingress Controller: `kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml`
   - AWS: AWS ALB Ingress Controller
   - Other: Follow your platform's ingress controller setup

## Quick Start - One Command Deployment

**🚀 Deploy everything with a single command:**

```bash
# From the project root
make deploy

# Or from the k8s directory
cd k8s && ./deploy-full.sh
```

This single command will:
- ✅ Create/verify Kubernetes cluster (kind)
- ✅ Build Docker image
- ✅ Load image into cluster
- ✅ Create namespace, secrets, and configs
- ✅ Deploy PostgreSQL database
- ✅ Deploy FastAPI application
- ✅ Set up port-forward to http://localhost:8000

**Other useful commands:**
```bash
make deploy-fast      # Skip Docker build (if image already exists)
make clean            # Delete everything
make logs             # View application logs
make status           # Show deployment status
make scale NUM=5      # Scale to 5 replicas
make port-forward     # Start port-forward manually
```

---

## Manual Deployment

### 1. Create Secrets

**Option A: Using kubectl (recommended for quick setup)**
```bash
kubectl create namespace kcca-kla-connect

kubectl create secret generic kcca-kla-connect-secrets \
  --from-literal=DATABASE_URL='postgresql://postgres:password@postgres-service:5432/klaconnect' \
  --from-literal=SECRET='your-secret-key-change-in-production' \
  --from-literal=POSTGRES_PASSWORD='password' \
  --namespace=kcca-kla-connect
```

**Option B: Using the template file**
1. Copy `secret.yaml.template` to `secret.yaml`
2. Update the values in `secret.yaml`
3. `kubectl apply -f secret.yaml`

### 2. Deploy Database (Optional)

**For in-cluster PostgreSQL:**
```bash
kubectl apply -f postgres.yaml
```

**For managed database (recommended for production):**
- AWS RDS
- Google Cloud SQL
- Azure Database for PostgreSQL
- Update `DATABASE_URL` in secrets accordingly

### 3. Deploy Application

**Deploy all resources:**
```bash
# Deploy in order
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml  # or use kubectl create secret as above
kubectl apply -f pvc-uploads.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml
```

**Or using kustomize:**
```bash
kubectl apply -k .
```

### 4. Verify Deployment

```bash
# Check namespace
kubectl get namespaces | grep kcca-kla-connect

# Check pods
kubectl get pods -n kcca-kla-connect

# Check services
kubectl get services -n kcca-kla-connect

# Check ingress
kubectl get ingress -n kcca-kla-connect

# View logs
kubectl logs -f deployment/kcca-kla-connect-web -n kcca-kla-connect

# Describe deployment
kubectl describe deployment kcca-kla-connect-web -n kcca-kla-connect
```

### 5. Access the Application

**LoadBalancer Service:**
```bash
# Get external IP (may take a few minutes)
kubectl get service kcca-kla-connect-service -n kcca-kla-connect

# Access via external IP
curl http://<EXTERNAL-IP>/docs
```

**Ingress:**
- If using Ingress, access via the configured domain (e.g., `api.kcca.go.ug`)
- Ensure your DNS points to the Ingress LoadBalancer IP

## Configuration

### Environment Variables

Update `configmap.yaml` for non-sensitive configuration:
- `ALGORITHM`: JWT algorithm
- `UPLOAD_FOLDER`: Path for file uploads

Update `secret.yaml` for sensitive data:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET`: JWT signing secret
- `POSTGRES_PASSWORD`: Database password (if using in-cluster DB)

### Scaling

**Manual Scaling:**
```bash
kubectl scale deployment kcca-kla-connect-web --replicas=5 -n kcca-kla-connect
```

**Automatic Scaling:**
The HPA (HorizontalPodAutoscaler) is configured to:
- Scale between 2-10 pods
- Scale based on CPU (70% target) and Memory (80% target)
- Scale up quickly, scale down gradually

### Resource Limits

Update `deployment.yaml` to adjust resource requests/limits:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Storage

The `pvc-uploads.yaml` creates a 10Gi persistent volume for uploads.

**For ReadWriteMany access modes**, your storage class must support it:
- AWS EFS
- NFS-based storage
- Some cloud provider file storage services

If not available, change to `ReadWriteOnce` in `pvc-uploads.yaml`.

## Platform-Specific Notes

### AWS (EKS)

1. **Load Balancer:**
   - Annotate service for Network Load Balancer:
     ```yaml
     metadata:
       annotations:
         service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
     ```

2. **Ingress (ALB):**
   - Install AWS Load Balancer Controller
   - See commented section in `ingress.yaml`

3. **Storage:**
   - Use EBS CSI driver for persistent volumes
   - For ReadWriteMany, use EFS CSI driver

### Google Cloud (GKE)

1. **Load Balancer:**
   - Built-in support, no configuration needed

2. **Ingress:**
   - Use GKE Ingress (or NGINX Ingress)

3. **Storage:**
   - Default storage class supports ReadWriteOnce
   - For ReadWriteMany, use Cloud Filestore

### Azure (AKS)

1. **Load Balancer:**
   - Built-in support, no configuration needed

2. **Ingress:**
   - Use NGINX Ingress or Azure Application Gateway Ingress Controller

3. **Storage:**
   - Default storage class supports ReadWriteOnce
   - For ReadWriteMany, use Azure Files

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name> -n kcca-kla-connect
kubectl logs <pod-name> -n kcca-kla-connect
```

### Database connection issues
- Verify `DATABASE_URL` in secrets
- Check PostgreSQL service: `kubectl get svc postgres-service -n kcca-kla-connect`
- Test connection: `kubectl exec -it <pod-name> -n kcca-kla-connect -- psql $DATABASE_URL`

### LoadBalancer not getting external IP
- Check cloud provider quotas/limits
- Verify Load Balancer controller is installed
- Check events: `kubectl get events -n kcca-kla-connect --sort-by='.lastTimestamp'`

### Ingress not working
- Verify Ingress controller is running: `kubectl get pods -n ingress-nginx`
- Check Ingress status: `kubectl describe ingress kcca-kla-connect-ingress -n kcca-kla-connect`
- Verify DNS points to LoadBalancer IP

## Production Checklist

- [ ] Use managed database service (RDS, Cloud SQL, etc.)
- [ ] Push images to container registry with version tags
- [ ] Use proper secrets management (HashiCorp Vault, AWS Secrets Manager, etc.)
- [ ] Enable TLS/HTTPS for Ingress
- [ ] Configure resource limits appropriately
- [ ] Set up monitoring and logging (Prometheus, Grafana, ELK, etc.)
- [ ] Configure backup strategy for persistent volumes
- [ ] Set up CI/CD pipeline
- [ ] Review and adjust HPA thresholds
- [ ] Enable network policies for security
- [ ] Configure PodDisruptionBudget for graceful shutdowns

## Updates and Rollouts

**Update image:**
```bash
kubectl set image deployment/kcca-kla-connect-web \
  web=kcca-kla-connect-api-web:v1.0.1 \
  -n kcca-kla-connect
```

**Rollback:**
```bash
kubectl rollout undo deployment/kcca-kla-connect-web -n kcca-kla-connect
```

**Watch rollout:**
```bash
kubectl rollout status deployment/kcca-kla-connect-web -n kcca-kla-connect
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace kcca-kla-connect

# Or delete individually
kubectl delete -f .
```

## Support

For issues or questions, refer to:
- Kubernetes documentation: https://kubernetes.io/docs/
- Your cloud provider's Kubernetes documentation

