#!/bin/bash

# Install Prerequisites for VPS Deployment
# This script installs: Docker, kubectl, and optionally k3s
# Usage: ./install-prerequisites.sh [--install-k3s] [--install-docker] [--install-kubectl]

set -e

INSTALL_K3S=false
INSTALL_DOCKER=false
INSTALL_KUBECTL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-k3s)
            INSTALL_K3S=true
            shift
            ;;
        --install-docker)
            INSTALL_DOCKER=true
            shift
            ;;
        --install-kubectl)
            INSTALL_KUBECTL=true
            shift
            ;;
        --all)
            INSTALL_K3S=true
            INSTALL_DOCKER=true
            INSTALL_KUBECTL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--install-k3s] [--install-docker] [--install-kubectl] [--all]"
            exit 1
            ;;
    esac
done

# If no flags, show interactive menu
if [ "$INSTALL_K3S" = false ] && [ "$INSTALL_DOCKER" = false ] && [ "$INSTALL_KUBECTL" = false ]; then
    echo "📦 Prerequisites Installation"
    echo "============================="
    echo ""
    echo "What would you like to install?"
    echo ""
    echo "1. All (k3s, Docker, kubectl)"
    echo "2. k3s only (includes kubectl)"
    echo "3. Docker only"
    echo "4. kubectl only"
    echo "5. Skip installation"
    echo ""
    read -p "Enter choice (1-5): " choice
    
    case $choice in
        1)
            INSTALL_K3S=true
            INSTALL_DOCKER=true
            INSTALL_KUBECTL=true
            ;;
        2)
            INSTALL_K3S=true
            ;;
        3)
            INSTALL_DOCKER=true
            ;;
        4)
            INSTALL_KUBECTL=true
            ;;
        5)
            echo "⏭️  Skipping installation"
            exit 0
            ;;
        *)
            echo "Invalid choice"
            exit 1
            ;;
    esac
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "❌ Cannot detect OS. Please install manually."
    exit 1
fi

echo ""
echo "Detected OS: $OS $VERSION"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ] && ! sudo -n true 2>/dev/null; then
    echo "⚠️  Some installations require sudo. You may be prompted for password."
fi

# Install Docker
if [ "$INSTALL_DOCKER" = true ]; then
    echo "🐳 Installing Docker..."
    
    if command -v docker &> /dev/null; then
        echo "✓ Docker already installed: $(docker --version)"
    else
        case $OS in
            ubuntu|debian)
                sudo apt-get update
                sudo apt-get install -y ca-certificates curl gnupg lsb-release
                sudo mkdir -p /etc/apt/keyrings
                curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
                echo \
                  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
                  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
                sudo apt-get update
                sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                sudo systemctl enable docker
                sudo systemctl start docker
                sudo usermod -aG docker $USER
                echo "✓ Docker installed. You may need to log out and back in for group changes."
                ;;
            centos|rhel|fedora)
                sudo yum install -y yum-utils
                sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                sudo systemctl enable docker
                sudo systemctl start docker
                sudo usermod -aG docker $USER
                echo "✓ Docker installed"
                ;;
            *)
                echo "⚠️  OS $OS not directly supported. Please install Docker manually:"
                echo "   https://docs.docker.com/engine/install/"
                ;;
        esac
    fi
fi

# Install kubectl
if [ "$INSTALL_KUBECTL" = true ]; then
    echo ""
    echo "📦 Installing kubectl..."
    
    if command -v kubectl &> /dev/null; then
        echo "✓ kubectl already installed: $(kubectl version --client --short 2>/dev/null || echo 'installed')"
    else
        KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
        curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
        sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
        rm kubectl
        echo "✓ kubectl installed: $(kubectl version --client --short)"
    fi
fi

# Install k3s
if [ "$INSTALL_K3S" = true ]; then
    echo ""
    echo "🚀 Installing k3s..."
    
    if command -v k3s &> /dev/null || systemctl is-active --quiet k3s 2>/dev/null; then
        echo "✓ k3s already installed"
        sudo systemctl enable k3s 2>/dev/null || true
        sudo systemctl start k3s 2>/dev/null || true
    else
        curl -sfL https://get.k3s.io | sh -
        sudo systemctl enable k3s
        sudo systemctl start k3s
        
        echo "✓ k3s installed and started"
        
        # Configure kubectl for k3s
        echo ""
        echo "📝 Configuring kubectl for k3s..."
        mkdir -p ~/.kube
        sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config 2>/dev/null || true
        sudo chown $USER:$USER ~/.kube/config 2>/dev/null || true
        
        # Fix localhost in config if needed
        if grep -q "127.0.0.1" ~/.kube/config 2>/dev/null; then
            sed -i 's/127.0.0.1/localhost/g' ~/.kube/config 2>/dev/null || true
        fi
        
        echo "✓ kubectl configured for k3s"
        
        # Install kubectl if not present
        if ! command -v kubectl &> /dev/null; then
            echo "📦 Installing kubectl..."
            KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
            curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
            sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
            rm kubectl
        fi
    fi
    
    # Wait for k3s to be ready
    echo "⏳ Waiting for k3s to be ready..."
    sleep 5
    if kubectl cluster-info &> /dev/null; then
        echo "✓ k3s cluster is ready"
        kubectl get nodes
    else
        echo "⚠️  k3s may still be starting. Run: kubectl get nodes"
    fi
fi

echo ""
echo "✅ Prerequisites installation complete!"
echo ""
echo "📋 Summary:"
[ "$INSTALL_DOCKER" = true ] && command -v docker &> /dev/null && echo "  ✓ Docker: $(docker --version | cut -d' ' -f3 | cut -d',' -f1)"
[ "$INSTALL_KUBECTL" = true ] || [ "$INSTALL_K3S" = true ] && command -v kubectl &> /dev/null && echo "  ✓ kubectl: installed"
[ "$INSTALL_K3S" = true ] && systemctl is-active --quiet k3s 2>/dev/null && echo "  ✓ k3s: running"
echo ""
echo "📝 Next steps:"
if [ "$INSTALL_K3S" = true ]; then
    echo "   Your k3s cluster is ready! You can now run:"
    echo "   cd /path/to/kcca_kla_connect_api && make deploy-vps"
else
    echo "   Install Kubernetes (k3s recommended):"
    echo "   curl -sfL https://get.k3s.io | sh -"
    echo "   Then run: make deploy-vps"
fi

