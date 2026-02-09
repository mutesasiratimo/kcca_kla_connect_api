#!/bin/bash

# Minimal Deployment Script for VPS using GHCR
# This script downloads manifests from GitHub and deploys without needing the repository
# Usage: ./deploy-ghcr-remote.sh [--image-tag=TAG] [--skip-db] [--no-confirm]

set -e

# Configuration
NAMESPACE="kcca-kla-connect"
REPO_OWNER="mutesasiratimo"
REPO_NAME="kcca_kla_connect_api"
BRANCH="main"
GHCR_IMAGE="ghcr.io/${REPO_OWNER}/${REPO_NAME}"
DEFAULT_TAG="latest"
MANIFESTS_BASE_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${BRANCH}/k8s"

# Flags
IMAGE_TAG=${IMAGE_TAG:-${DEFAULT_TAG}}
SKIP_DB=${SKIP_DB:-false}
NO_CONFIRM=${NO_CONFIRM:-false}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image-tag=*)
            IMAGE_TAG="${1#*=}"
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --no-confirm)
            NO_CONFIRM=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--image-tag=TAG] [--skip-db] [--no-confirm]"
            exit 1
            ;;
    esac
done

echo "🚀 KCCA Kla Connect - GHCR Remote Deployment"
echo "=============================================="
echo ""
echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
echo "Image: ${GHCR_IMAGE}:${IMAGE_TAG}"
echo "Namespace: ${NAMESPACE}"
echo ""

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Verify cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster."
    echo "   Make sure kubectl is configured correctly."
    exit 1
fi

CLUSTER_CONTEXT=$(kubectl config current-context)
echo "✓ Connected to cluster: ${CLUSTER_CONTEXT}"

# Confirm deployment
if [ "$NO_CONFIRM" = false ]; then
    echo ""
    echo "⚠️  About to deploy to: ${CLUSTER_CONTEXT}"
    read -p "Continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

# Create temporary directory for manifests
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

echo ""
echo "📥 Downloading Kubernetes manifests from GitHub..."

# Download required manifests
curl -sSL "${MANIFESTS_BASE_URL}/namespace.yaml" -o "${TEMP_DIR}/namespace.yaml"
curl -sSL "${MANIFESTS_BASE_URL}/configmap.yaml" -o "${TEMP_DIR}/configmap.yaml"
curl -sSL "${MANIFESTS_BASE_URL}/pvc-uploads.yaml" -o "${TEMP_DIR}/pvc-uploads.yaml"
curl -sSL "${MANIFESTS_BASE_URL}/deployment.yaml" -o "${TEMP_DIR}/deployment.yaml"
curl -sSL "${MANIFESTS_BASE_URL}/service.yaml" -o "${TEMP_DIR}/service.yaml"

if [ "$SKIP_DB" = false ]; then
    curl -sSL "${MANIFESTS_BASE_URL}/postgres.yaml" -o "${TEMP_DIR}/postgres.yaml"
fi

echo "✓ Manifests downloaded"

# Update deployment image
echo ""
echo "🔄 Updating deployment image to ${GHCR_IMAGE}:${IMAGE_TAG}..."
sed -i.bak "s|image:.*ghcr.io.*|image: ${GHCR_IMAGE}:${IMAGE_TAG}|g" "${TEMP_DIR}/deployment.yaml"
sed -i.bak 's|imagePullPolicy:.*|imagePullPolicy: Always|g' "${TEMP_DIR}/deployment.yaml"
rm -f "${TEMP_DIR}/deployment.yaml.bak"

# Step 1: Create namespace
echo ""
echo "🔷 Step 1/6: Creating namespace..."
kubectl apply -f "${TEMP_DIR}/namespace.yaml"
echo "✓ Namespace created"

# Step 2: Check/create GHCR pull secret
echo ""
echo "🔷 Step 2/6: Setting up GHCR pull secret..."
if kubectl get secret ghcr-pull-secret -n ${NAMESPACE} &> /dev/null; then
    echo "✓ GHCR pull secret already exists"
else
    echo "⚠️  GHCR pull secret not found!"
    echo ""
    echo "To create the secret, run:"
    echo "  kubectl create secret docker-registry ghcr-pull-secret \\"
    echo "    --docker-server=ghcr.io \\"
    echo "    --docker-username=YOUR_GITHUB_USERNAME \\"
    echo "    --docker-password=YOUR_GITHUB_PAT \\"
    echo "    --namespace=${NAMESPACE}"
    echo ""
    echo "⚠️  If your image is public, you can remove imagePullSecrets from deployment.yaml"
    read -p "Continue anyway? (yes/no): " continue_anyway
    if [ "$continue_anyway" != "yes" ]; then
        echo "Deployment cancelled. Please create the secret first."
        exit 1
    fi
fi

# Step 3: Check/create application secrets
echo ""
echo "🔷 Step 3/6: Setting up application secrets..."
if kubectl get secret kcca-kla-connect-secrets -n ${NAMESPACE} &> /dev/null; then
    echo "✓ Application secrets already exist"
else
    echo "⚠️  Application secrets not found!"
    echo ""
    echo "Creating default secrets (CHANGE THESE FOR PRODUCTION!)"
    kubectl create secret generic kcca-kla-connect-secrets \
        --from-literal=DATABASE_URL='postgresql://postgres:changeme123@postgres-service:5432/klaconnect' \
        --from-literal=SECRET='your-secret-key-change-this-in-production' \
        --from-literal=POSTGRES_PASSWORD='changeme123' \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "⚠️  WARNING: Using default secrets! Update them for production!"
fi

# Step 4: Deploy ConfigMap
echo ""
echo "🔷 Step 4/6: Deploying ConfigMap..."
kubectl apply -f "${TEMP_DIR}/configmap.yaml"
echo "✓ ConfigMap deployed"

# Step 5: Create PVCs
echo ""
echo "🔷 Step 5/6: Creating PersistentVolumeClaims..."
kubectl apply -f "${TEMP_DIR}/pvc-uploads.yaml"
echo "✓ PVCs created"

# Step 6: Deploy PostgreSQL (if not skipped)
if [ "$SKIP_DB" = false ]; then
    echo ""
    echo "🔷 Step 6/7: Deploying PostgreSQL..."
    kubectl apply -f "${TEMP_DIR}/postgres.yaml"
    echo "⏳ Waiting for PostgreSQL to be ready..."
    if kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=180s 2>/dev/null; then
        echo "✓ PostgreSQL is ready"
    else
        echo "⚠️  PostgreSQL may still be starting. Continuing..."
    fi
else
    echo ""
    echo "⏭️  Skipping PostgreSQL deployment (using external/managed database)"
fi

# Step 7: Deploy application
echo ""
echo "🔷 Step 7/7: Deploying application..."
echo "   Image: ${GHCR_IMAGE}:${IMAGE_TAG}"
kubectl apply -f "${TEMP_DIR}/deployment.yaml"

echo "⏳ Waiting for deployment to be ready..."
if kubectl wait --for=condition=available deployment/kcca-kla-connect-web -n ${NAMESPACE} --timeout=300s 2>/dev/null; then
    echo "✓ Deployment is ready"
else
    echo "⚠️  Deployment may still be starting..."
fi

# Step 8: Deploy services
echo ""
echo "🔷 Step 8/8: Deploying services..."
kubectl apply -f "${TEMP_DIR}/service.yaml"
echo "✓ Services deployed"

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
echo "   Restart:      kubectl rollout restart deployment/kcca-kla-connect-web -n ${NAMESPACE}"
echo "   Scale:        kubectl scale deployment kcca-kla-connect-web --replicas=3 -n ${NAMESPACE}"
echo "   Update image: kubectl set image deployment/kcca-kla-connect-web web=${GHCR_IMAGE}:NEW_TAG -n ${NAMESPACE}"
echo "   Delete:       kubectl delete namespace ${NAMESPACE}"
echo ""
echo "🎉 Deployment to VPS complete!"
echo ""


