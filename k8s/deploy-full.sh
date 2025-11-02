#!/bin/bash

# Complete Kubernetes Deployment Pipeline
# This script handles: cluster setup, image build, and full deployment
# Usage: ./deploy-full.sh [--skip-build] [--skip-cluster] [--skip-port-forward]

set -e

# Configuration
CLUSTER_NAME="kcca-kla-connect"
NAMESPACE="kcca-kla-connect"
IMAGE_NAME="kcca-kla-connect-api-web:latest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Flags
SKIP_BUILD=false
SKIP_CLUSTER=false
SKIP_PORT_FORWARD=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-cluster)
            SKIP_CLUSTER=true
            shift
            ;;
        --skip-port-forward)
            SKIP_PORT_FORWARD=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-build] [--skip-cluster] [--skip-port-forward]"
            exit 1
            ;;
    esac
done

echo "🚀 KCCA Kla Connect - Full Kubernetes Deployment Pipeline"
echo "========================================================="
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
check_command docker
check_command kubectl
check_command kind

# Step 1: Create/verify Kubernetes cluster
if [ "$SKIP_CLUSTER" = false ]; then
    echo ""
    echo "🔷 Step 1/9: Setting up Kubernetes cluster..."
    
    if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        echo "✓ Cluster '${CLUSTER_NAME}' already exists"
        
        # Check if we can connect
        if kubectl cluster-info --context kind-${CLUSTER_NAME} &> /dev/null; then
            echo "✓ Cluster is accessible"
            kubectl config use-context kind-${CLUSTER_NAME}
        else
            echo "⚠️  Cluster exists but not accessible. Removing and recreating..."
            kind delete cluster --name ${CLUSTER_NAME}
            kind create cluster --name ${CLUSTER_NAME}
            kubectl config use-context kind-${CLUSTER_NAME}
        fi
    else
        echo "📦 Creating new cluster '${CLUSTER_NAME}'..."
        kind create cluster --name ${CLUSTER_NAME}
        kubectl config use-context kind-${CLUSTER_NAME}
        echo "✓ Cluster created"
    fi
else
    echo "⏭️  Skipping cluster setup (using existing cluster)"
    # Try to use the cluster
    if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        kubectl config use-context kind-${CLUSTER_NAME} 2>/dev/null || true
    fi
fi

# Verify cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster."
    exit 1
fi

# Step 2: Build Docker image
if [ "$SKIP_BUILD" = false ]; then
    echo ""
    echo "🔷 Step 2/9: Building Docker image..."
    cd "${PROJECT_ROOT}"
    docker build -t ${IMAGE_NAME} .
    echo "✓ Docker image built: ${IMAGE_NAME}"
else
    echo "⏭️  Skipping Docker build"
fi

# Step 3: Load image into kind cluster
echo ""
echo "🔷 Step 3/9: Loading image into cluster..."
if [ "$SKIP_BUILD" = false ]; then
    kind load docker-image ${IMAGE_NAME} --name ${CLUSTER_NAME}
    echo "✓ Image loaded into cluster"
else
    # Try to load anyway in case image was built externally
    if docker images | grep -q "${IMAGE_NAME%:*}"; then
        kind load docker-image ${IMAGE_NAME} --name ${CLUSTER_NAME} || echo "⚠️  Could not load image (may already exist)"
    fi
fi

# Step 4: Create namespace
echo ""
echo "🔷 Step 4/9: Creating namespace..."
kubectl apply -f "${SCRIPT_DIR}/namespace.yaml"
echo "✓ Namespace created"

# Step 5: Create secrets (or update if exists)
echo ""
echo "🔷 Step 5/9: Setting up secrets..."
if kubectl get secret kcca-kla-connect-secrets -n ${NAMESPACE} &> /dev/null; then
    echo "✓ Secrets already exist (skipping creation)"
else
    echo "🔐 Creating secrets..."
    kubectl create secret generic kcca-kla-connect-secrets \
        --from-literal=DATABASE_URL='postgresql://postgres:changeme123@postgres-service:5432/klaconnect' \
        --from-literal=SECRET='your-secret-key-change-this-in-production-please-use-strong-secret' \
        --from-literal=POSTGRES_PASSWORD='changeme123' \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "✓ Secrets created"
    echo "⚠️  WARNING: Using default secrets! Change them for production:"
    echo "   kubectl create secret generic kcca-kla-connect-secrets \\"
    echo "     --from-literal=DATABASE_URL='postgresql://...' \\"
    echo "     --from-literal=SECRET='your-secret' \\"
    echo "     --from-literal=POSTGRES_PASSWORD='password' \\"
    echo "     --namespace=${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -"
fi

# Step 6: Deploy ConfigMap
echo ""
echo "🔷 Step 6/9: Deploying ConfigMap..."
kubectl apply -f "${SCRIPT_DIR}/configmap.yaml"
echo "✓ ConfigMap deployed"

# Step 7: Deploy PostgreSQL and PVCs
echo ""
echo "🔷 Step 7/9: Deploying PostgreSQL database..."
kubectl apply -f "${SCRIPT_DIR}/pvc-uploads.yaml"
kubectl apply -f "${SCRIPT_DIR}/postgres.yaml"
echo "⏳ Waiting for PostgreSQL to be ready..."
if kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=180s 2>/dev/null; then
    echo "✓ PostgreSQL is ready"
else
    echo "⚠️  PostgreSQL may still be starting. Continuing..."
fi

# Step 8: Deploy application
echo ""
echo "🔷 Step 8/9: Deploying FastAPI application..."
kubectl apply -f "${SCRIPT_DIR}/deployment.yaml"
echo "⏳ Waiting for deployment to be ready..."
if kubectl wait --for=condition=available deployment/kcca-kla-connect-web -n ${NAMESPACE} --timeout=300s 2>/dev/null; then
    echo "✓ Deployment is ready"
else
    echo "⚠️  Deployment may still be starting..."
fi

# Deploy services
kubectl apply -f "${SCRIPT_DIR}/service.yaml"
echo "✓ Services deployed"

# Optional: Deploy HPA
if [ -f "${SCRIPT_DIR}/hpa.yaml" ]; then
    echo "📈 Deploying HorizontalPodAutoscaler..."
    kubectl apply -f "${SCRIPT_DIR}/hpa.yaml" || echo "⚠️  HPA deployment failed (may require metrics-server)"
fi

# Step 9: Verify deployment
echo ""
echo "🔷 Step 9/9: Verifying deployment..."
echo ""
kubectl get all -n ${NAMESPACE}

echo ""
echo "✅ Deployment complete!"
echo ""

# Check pod status
PODS_READY=$(kubectl get pods -n ${NAMESPACE} -l app=kcca-kla-connect,component=web --no-headers 2>/dev/null | grep -c "Running" || echo "0")
TOTAL_PODS=$(kubectl get pods -n ${NAMESPACE} -l app=kcca-kla-connect,component=web --no-headers 2>/dev/null | wc -l | tr -d ' ' || echo "0")

if [ "$PODS_READY" -gt 0 ]; then
    echo "✓ ${PODS_READY}/${TOTAL_PODS} application pods are running"
else
    echo "⚠️  Pods are still starting. Check status with:"
    echo "   kubectl get pods -n ${NAMESPACE}"
fi

# Port-forward setup
if [ "$SKIP_PORT_FORWARD" = false ]; then
    echo ""
    echo "🔗 Setting up port-forward..."
    
    # Kill existing port-forwards on port 8000
    pkill -f "kubectl port-forward.*8000" 2>/dev/null || true
    
    # Start port-forward in background
    kubectl port-forward -n ${NAMESPACE} service/kcca-kla-connect-internal 8000:8000 > /dev/null 2>&1 &
    PORT_FORWARD_PID=$!
    
    # Wait a moment for port-forward to establish
    sleep 2
    
    # Test if port-forward is working
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        echo "✓ Port-forward active on port 8000"
        echo ""
        echo "🌐 Access your API at:"
        echo "   📖 Swagger UI: http://localhost:8000/docs"
        echo "   📋 API Root:  http://localhost:8000"
        echo ""
        echo "   To stop port-forward: pkill -f 'kubectl port-forward.*8000'"
    else
        echo "⚠️  Port-forward started but API not responding yet"
        echo "   Wait a moment and try: http://localhost:8000/docs"
    fi
else
    echo ""
    echo "🔗 To access the API, run:"
    echo "   kubectl port-forward -n ${NAMESPACE} service/kcca-kla-connect-internal 8000:8000"
fi

echo ""
echo "📝 Useful commands:"
echo "   View logs:    kubectl logs -f deployment/kcca-kla-connect-web -n ${NAMESPACE}"
echo "   View pods:    kubectl get pods -n ${NAMESPACE}"
echo "   Scale:        kubectl scale deployment kcca-kla-connect-web --replicas=5 -n ${NAMESPACE}"
echo "   Delete all:   kubectl delete namespace ${NAMESPACE}"
echo ""
echo "🎉 All done! Your API should be running."
echo ""

