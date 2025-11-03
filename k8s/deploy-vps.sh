#!/bin/bash

# VPS/Server Kubernetes Deployment Script
# For use with k3s, microk8s, or other existing Kubernetes clusters
# Usage: ./deploy-vps.sh [--skip-build] [--registry=REGISTRY] [--image-tag=TAG] [--no-confirm]
# Environment variables: SKIP_BUILD, REGISTRY, IMAGE_TAG, NO_CONFIRM, SKIP_DB

set -e

# Configuration
NAMESPACE="kcca-kla-connect"
IMAGE_NAME="kcca-kla-connect-api-web"
DEFAULT_TAG="latest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Flags from environment or arguments
SKIP_BUILD=${SKIP_BUILD:-false}
REGISTRY=${REGISTRY:-""}
IMAGE_TAG=${IMAGE_TAG:-"${DEFAULT_TAG}"}
NO_CONFIRM=${NO_CONFIRM:-false}
SKIP_DB=${SKIP_DB:-false}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --registry=*)
            REGISTRY="${1#*=}"
            shift
            ;;
        --image-tag=*)
            IMAGE_TAG="${1#*=}"
            shift
            ;;
        --no-confirm)
            NO_CONFIRM=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-build] [--registry=REGISTRY] [--image-tag=TAG] [--no-confirm] [--skip-db]"
            exit 1
            ;;
    esac
done

echo "🚀 KCCA Kla Connect - VPS/Server Deployment"
echo "============================================"
echo ""

# Function to check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 not found. Please install $1 first."
        exit 1
    fi
}

# Check prerequisites
echo "📋 Checking prerequisites..."
check_command kubectl

# Verify cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster."
    echo "   Make sure kubectl is configured correctly."
    echo "   For k3s: export KUBECONFIG=~/.kube/config"
    echo "   For microk8s: microk8s kubectl get nodes"
    exit 1
fi

CLUSTER_CONTEXT=$(kubectl config current-context)
echo "✓ Connected to cluster: ${CLUSTER_CONTEXT}"

# Confirm deployment (unless NO_CONFIRM is set)
if [ "$NO_CONFIRM" = false ]; then
    echo ""
    echo "⚠️  About to deploy to: ${CLUSTER_CONTEXT}"
    read -p "Continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

# Determine image name
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
    echo "📦 Using registry image: ${FULL_IMAGE}"
else
    FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
fi

# Step 1: Build Docker image (if not skipped and no registry)
if [ "$SKIP_BUILD" = false ] && [ -z "$REGISTRY" ]; then
    echo ""
    echo "🔷 Step 1/8: Building Docker image..."
    check_command docker
    
    if ! docker info &> /dev/null; then
        echo "❌ Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    cd "${PROJECT_ROOT}"
    docker build -t ${FULL_IMAGE} .
    echo "✓ Docker image built: ${FULL_IMAGE}"
    
    # Load image into k3s/microk8s if detected
    if command -v k3s &> /dev/null; then
        echo "📥 Loading image into k3s..."
        sudo k3s ctr images import <(docker save ${FULL_IMAGE}) 2>/dev/null || \
        echo "⚠️  Could not load into k3s (may need to copy image manually)"
    elif kubectl get nodes -o jsonpath='{.items[0].metadata.labels.node\\.kubernetes\\.io/instance-type}' 2>/dev/null | grep -q "k3s"; then
        echo "📥 Detected k3s cluster. Loading image..."
        # Try to use k3s ctr if available
        if command -v k3s &> /dev/null; then
            sudo k3s ctr images import <(docker save ${FULL_IMAGE}) 2>/dev/null || \
            echo "⚠️  Could not load into k3s"
        else
            echo "ℹ️  Build completed. Image should be available if Docker is shared with k3s."
        fi
    fi
else
    echo "⏭️  Skipping Docker build"
    if [ -z "$REGISTRY" ]; then
        echo "⚠️  WARNING: No registry specified and build skipped."
        echo "   Make sure the image ${FULL_IMAGE} exists in the cluster."
    fi
fi

# Step 2: Create namespace
echo ""
echo "🔷 Step 2/8: Creating namespace..."
kubectl apply -f "${SCRIPT_DIR}/namespace.yaml"
echo "✓ Namespace created"

# Step 3: Create/update secrets
echo ""
echo "🔷 Step 3/8: Setting up secrets..."
if kubectl get secret kcca-kla-connect-secrets -n ${NAMESPACE} &> /dev/null; then
    echo "✓ Secrets already exist (skipping creation)"
    echo "   To update secrets, run:"
    echo "   kubectl create secret generic kcca-kla-connect-secrets \\"
    echo "     --from-literal=DATABASE_URL='postgresql://...' \\"
    echo "     --from-literal=SECRET='your-secret' \\"
    echo "     --from-literal=POSTGRES_PASSWORD='password' \\"
    echo "     --namespace=${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -"
else
    echo "🔐 Creating default secrets..."
    echo "⚠️  WARNING: Using default secrets! Change them for production!"
    kubectl create secret generic kcca-kla-connect-secrets \
        --from-literal=DATABASE_URL='postgresql://postgres:changeme123@postgres-service:5432/klaconnect' \
        --from-literal=SECRET='your-secret-key-change-this-in-production-please-use-strong-secret' \
        --from-literal=POSTGRES_PASSWORD='changeme123' \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "✓ Secrets created (default values - UPDATE FOR PRODUCTION!)"
fi

# Step 4: Deploy ConfigMap
echo ""
echo "🔷 Step 4/8: Deploying ConfigMap..."
kubectl apply -f "${SCRIPT_DIR}/configmap.yaml"
echo "✓ ConfigMap deployed"

# Step 5: Create PVCs
echo ""
echo "🔷 Step 5/8: Creating PersistentVolumeClaims..."
kubectl apply -f "${SCRIPT_DIR}/pvc-uploads.yaml"
echo "✓ PVCs created"

# Step 6: Deploy PostgreSQL (if not skipped)
if [ "$SKIP_DB" = false ]; then
    echo ""
    echo "🔷 Step 6/8: Deploying PostgreSQL database..."
    kubectl apply -f "${SCRIPT_DIR}/postgres.yaml"
    echo "⏳ Waiting for PostgreSQL to be ready..."
    if kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=180s 2>/dev/null; then
        echo "✓ PostgreSQL is ready"
    else
        echo "⚠️  PostgreSQL may still be starting. Continuing..."
    fi
else
    echo "⏭️  Skipping PostgreSQL deployment (using external/managed database)"
fi

# Step 7: Deploy application
echo ""
echo "🔷 Step 7/8: Deploying FastAPI application..."
echo "   Using image: ${FULL_IMAGE}"

# Update deployment image if registry is specified
if [ -n "$REGISTRY" ]; then
    # Create a temporary deployment file with the registry image
    TEMP_DEPLOYMENT=$(mktemp)
    sed "s|image:.*kcca-kla-connect-api-web.*|image: ${FULL_IMAGE}|g; s|imagePullPolicy:.*|imagePullPolicy: Always|g" \
        "${SCRIPT_DIR}/deployment.yaml" > "${TEMP_DEPLOYMENT}"
    kubectl apply -f "${TEMP_DEPLOYMENT}"
    rm -f "${TEMP_DEPLOYMENT}"
else
    kubectl apply -f "${SCRIPT_DIR}/deployment.yaml"
fi

echo "⏳ Waiting for deployment to be ready..."
if kubectl wait --for=condition=available deployment/kcca-kla-connect-web -n ${NAMESPACE} --timeout=300s 2>/dev/null; then
    echo "✓ Deployment is ready"
else
    echo "⚠️  Deployment may still be starting..."
fi

# Step 8: Deploy services
echo ""
echo "🔷 Step 8/8: Deploying services..."
kubectl apply -f "${SCRIPT_DIR}/service.yaml"
echo "✓ Services deployed"

# Optional: Deploy HPA
if [ -f "${SCRIPT_DIR}/hpa.yaml" ]; then
    echo "📈 Deploying HorizontalPodAutoscaler..."
    kubectl apply -f "${SCRIPT_DIR}/hpa.yaml" || echo "⚠️  HPA deployment failed (may require metrics-server)"
fi

# Verify deployment
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Current status:"
kubectl get all -n ${NAMESPACE}

# Get access information
echo ""
echo "🔗 Access Information:"

# Check for LoadBalancer
LB_IP=$(kubectl get service kcca-kla-connect-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
LB_HOST=$(kubectl get service kcca-kla-connect-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
if [ -n "$LB_IP" ]; then
    echo "   🌐 LoadBalancer: http://${LB_IP}/docs"
elif [ -n "$LB_HOST" ]; then
    echo "   🌐 LoadBalancer: http://${LB_HOST}/docs"
else
    # Check for NodePort
    NODEPORT=$(kubectl get service kcca-kla-connect-service -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    if [ -n "$NODEPORT" ]; then
        NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null)
        if [ -z "$NODE_IP" ]; then
            NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null)
        fi
        if [ -n "$NODE_IP" ]; then
            echo "   🌐 NodePort: http://${NODE_IP}:${NODEPORT}/docs"
        else
            echo "   🌐 NodePort: <node-ip>:${NODEPORT}/docs"
        fi
    else
        echo "   📡 Service type: $(kubectl get service kcca-kla-connect-service -n ${NAMESPACE} -o jsonpath='{.spec.type}')"
        echo "   Use port-forward: kubectl port-forward -n ${NAMESPACE} service/kcca-kla-connect-internal 8000:8000"
    fi
fi

# Check for Ingress
INGRESS_HOST=$(kubectl get ingress kcca-kla-connect-ingress -n ${NAMESPACE} -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo "")
if [ -n "$INGRESS_HOST" ]; then
    INGRESS_IP=$(kubectl get ingress kcca-kla-connect-ingress -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -n "$INGRESS_IP" ]; then
        echo "   🔀 Ingress: http://${INGRESS_HOST} (${INGRESS_IP})"
    else
        echo "   🔀 Ingress: http://${INGRESS_HOST} (configure DNS to point to cluster)"
    fi
fi

echo ""
echo "📝 Useful commands:"
echo "   View logs:    kubectl logs -f deployment/kcca-kla-connect-web -n ${NAMESPACE}"
echo "   View pods:    kubectl get pods -n ${NAMESPACE}"
echo "   Scale:        kubectl scale deployment kcca-kla-connect-web --replicas=3 -n ${NAMESPACE}"
echo "   Delete:       kubectl delete namespace ${NAMESPACE}"
echo ""
echo "🎉 Deployment to VPS/server complete!"
echo ""

