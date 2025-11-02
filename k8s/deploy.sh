#!/bin/bash

# Kubernetes Deployment Script
# Usage: ./deploy.sh [environment]
# Example: ./deploy.sh production

set -e

ENVIRONMENT=${1:-production}
NAMESPACE="kcca-kla-connect"

echo "🚀 Deploying KCCA Kla Connect API to Kubernetes (${ENVIRONMENT})..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

echo "✓ Cluster connection verified"

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f namespace.yaml

# Create secrets (check if exists first)
if ! kubectl get secret kcca-kla-connect-secrets -n ${NAMESPACE} &> /dev/null; then
    echo "⚠️  Secret 'kcca-kla-connect-secrets' not found."
    echo "   Please create it using:"
    echo "   kubectl create secret generic kcca-kla-connect-secrets \\"
    echo "     --from-literal=DATABASE_URL='postgresql://...' \\"
    echo "     --from-literal=SECRET='your-secret' \\"
    echo "     --from-literal=POSTGRES_PASSWORD='password' \\"
    echo "     --namespace=${NAMESPACE}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ Secrets already exist"
fi

# Apply ConfigMap
echo "📋 Applying ConfigMap..."
kubectl apply -f configmap.yaml

# Apply PVCs
echo "💾 Creating PersistentVolumeClaims..."
kubectl apply -f pvc-uploads.yaml

# Optional: Deploy PostgreSQL
read -p "Deploy in-cluster PostgreSQL? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🐘 Deploying PostgreSQL..."
    kubectl apply -f postgres.yaml
    echo "⏳ Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=300s
fi

# Apply Deployment
echo "🚢 Deploying application..."
kubectl apply -f deployment.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available deployment/kcca-kla-connect-web -n ${NAMESPACE} --timeout=300s

# Apply Service
echo "🌐 Creating Service..."
kubectl apply -f service.yaml

# Apply Ingress (optional)
read -p "Deploy Ingress? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔀 Creating Ingress..."
    kubectl apply -f ingress.yaml
fi

# Apply HPA
echo "📈 Creating HorizontalPodAutoscaler..."
kubectl apply -f hpa.yaml

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Current status:"
kubectl get all -n ${NAMESPACE}

echo ""
echo "🔗 Access the API:"

# Get LoadBalancer IP
LB_IP=$(kubectl get service kcca-kla-connect-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
if [ -n "$LB_IP" ]; then
    echo "   LoadBalancer: http://${LB_IP}/docs"
else
    echo "   LoadBalancer IP pending... Check with:"
    echo "   kubectl get service kcca-kla-connect-service -n ${NAMESPACE}"
fi

# Get Ingress
INGRESS_HOST=$(kubectl get ingress kcca-kla-connect-ingress -n ${NAMESPACE} -o jsonpath='{.spec.rules[0].host}' 2>/dev/null)
if [ -n "$INGRESS_HOST" ]; then
    INGRESS_IP=$(kubectl get ingress kcca-kla-connect-ingress -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    if [ -n "$INGRESS_IP" ]; then
        echo "   Ingress: http://${INGRESS_HOST} (${INGRESS_IP})"
    else
        echo "   Ingress: http://${INGRESS_HOST} (IP pending...)"
    fi
fi

echo ""
echo "📝 Useful commands:"
echo "   View logs: kubectl logs -f deployment/kcca-kla-connect-web -n ${NAMESPACE}"
echo "   View pods: kubectl get pods -n ${NAMESPACE}"
echo "   Describe pod: kubectl describe pod <pod-name> -n ${NAMESPACE}"

