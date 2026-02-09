.PHONY: deploy deploy-fast deploy-restore deploy-no-cluster deploy-prod build-push stop clean logs status scale help backup backup-setup backup-manual backup-download restore

# Default target
help:
	@echo "KCCA Kla Connect - Kubernetes Deployment"
	@echo ""
	@echo "Available commands:"
	@echo "  make deploy          - Full deployment (cluster + build + deploy)"
	@echo "  make deploy-fast     - Skip build if image exists"
	@echo "  make deploy-restore  - Deploy and restore from backup if found"
	@echo "  make deploy-prod     - Deploy to production cloud (requires registry)"
	@echo "  make deploy-vps      - Deploy to VPS/server (k3s/microk8s)"
	@echo "                         Env vars: NO_CONFIRM=true, SKIP_BUILD=true, REGISTRY=..., IMAGE_TAG=..., SKIP_DB=true"
	@echo "  make deploy-ghcr     - Deploy fixed GHCR image (no build)"
	@echo "  make deploy-ghcr-remote - Deploy from GHCR on VPS without repo (downloads manifests)"
	@echo "                              Env vars: IMAGE_TAG=..., SKIP_DB=true, NO_CONFIRM=true"
	@echo "  make restart         - Stop app only, rebuild & redeploy (keeps data)"
	@echo "  make restart-fast    - Stop app only, redeploy without rebuild"
	@echo "  make build-push      - Build and push image to registry"
	@echo "  make stop            - Stop app only (keeps namespace & data)"
	@echo "  make teardown        - Delete namespace (removes app & data)"
	@echo "  make clean           - Delete everything (cluster + namespace)"
	@echo "  make logs            - View application logs"
	@echo "  make status          - Show deployment status"
	@echo "  make scale NUM=X          - Scale to X replicas"
	@echo "  make port-forward         - Start port-forward (localhost only)"
	@echo "  make port-forward-network - Expose API on network (for other devices)"
	@echo ""
	@echo "Database Backup Commands:"
	@echo "  make backup-setup    - Setup automated daily backups"
	@echo "  make backup-manual   - Create manual backup now"
	@echo "  make backup-download - Download latest backup to local"
	@echo "  make backup          - Quick backup (manual + download)"
	@echo "  make restore FILE=   - Restore from backup file"
	@echo ""

deploy:
	@echo "🚀 Starting full deployment..."
	@cd k8s && ./deploy-full.sh

deploy-fast:
	@echo "🚀 Starting deployment (skipping build if image exists)..."
	@cd k8s && ./deploy-full.sh --skip-build

deploy-restore:
	@echo "🚀 Starting deployment with backup restore..."
	@cd k8s && ./deploy-full.sh
	@echo ""
	@echo "🔍 Checking for backup files..."
	@BACKUP_FILE=$$(ls -t backup-*.sql.gz 2>/dev/null | head -1); \
	if [ -n "$$BACKUP_FILE" ]; then \
		echo "✓ Found backup: $$BACKUP_FILE"; \
		echo ""; \
		echo "⚠️  Database will be restored from backup."; \
		echo "   This will replace any existing data in the database."; \
		read -p "Restore from $$BACKUP_FILE? (yes/no): " confirm; \
		if [ "$$confirm" = "yes" ]; then \
			echo ""; \
			echo "⏳ Waiting for PostgreSQL to be ready..."; \
			kubectl wait --for=condition=ready pod -l app=postgres -n kcca-kla-connect --timeout=120s || echo "⚠️  PostgreSQL may still be starting"; \
			sleep 5; \
			echo ""; \
			echo "🔄 Restoring database from backup..."; \
			$(MAKE) restore FILE=$$BACKUP_FILE RESTORE_AUTO=yes || echo "⚠️  Restore failed. Check logs."; \
			echo ""; \
			echo "✅ Deployment and restore complete!"; \
		else \
			echo "⏭️  Skipping restore. Database will be empty or use existing data."; \
		fi; \
	else \
		echo "ℹ️  No backup files found (backup-*.sql.gz)"; \
		echo "   Deploying with fresh database."; \
		echo "   To restore later: make restore FILE=backup-YYYYMMDD-HHMMSS.sql.gz"; \
	fi

deploy-no-cluster:
	@echo "🚀 Deploying to existing cluster..."
	@cd k8s && ./deploy-full.sh --skip-cluster --skip-build

# Production deployment commands
build-push:
	@if [ -z "$(REGISTRY)" ]; then \
		echo "❌ REGISTRY not specified"; \
		echo "Usage: make build-push REGISTRY=ghcr.io/username [TAG=v1.0.0] [PLATFORM=linux/amd64]"; \
		echo ""; \
		echo "Examples:"; \
		echo "  GHCR:       make build-push REGISTRY=ghcr.io/mutesasiratimo/kcca_kla_connect_api"; \
		echo "  Docker Hub: make build-push REGISTRY=your-username/kcca-kla-connect-api TAG=v1.0.0"; \
		echo "  DigitalOcean: make build-push REGISTRY=registry.digitalocean.com/your-registry/kcca-kla-connect-api"; \
		exit 1; \
	fi; \
	IMAGE_TAG=$${TAG:-latest}; \
	PLATFORM=$${PLATFORM:-linux/amd64}; \
	FULL_IMAGE="$$REGISTRY:$$IMAGE_TAG"; \
	echo "🏗️  Building image: $$FULL_IMAGE"; \
	echo "📦 Platform: $$PLATFORM"; \
	echo ""; \
	echo "🔍 Checking Docker..."; \
	if ! docker info >/dev/null 2>&1; then \
		echo "❌ Docker is not running!"; \
		echo "   Please start Docker Desktop and try again."; \
		exit 1; \
	fi; \
	echo "✅ Docker is running"; \
	if command -v docker buildx &> /dev/null; then \
		echo "📦 Setting up Docker Buildx..."; \
		DOCKER_CONTEXT=$$(docker context ls --format '{{.Name}}' | grep -E '^\*|desktop' | head -1 | sed 's/^\*//' | sed 's/^ //'); \
		if [ -n "$$DOCKER_CONTEXT" ] && [ "$$DOCKER_CONTEXT" != "*" ]; then \
			echo "   Using Docker context: $$DOCKER_CONTEXT"; \
			docker context use "$$DOCKER_CONTEXT" 2>/dev/null || true; \
		fi; \
		if docker buildx ls 2>/dev/null | grep -q "multiplatform"; then \
			echo "   Using existing 'multiplatform' builder..."; \
			docker buildx use multiplatform 2>/dev/null || true; \
		else \
			echo "   Creating buildx builder 'multiplatform'..."; \
			docker buildx create --name multiplatform --driver docker-container --use 2>/dev/null || \
			docker buildx create --name multiplatform --use --bootstrap 2>/dev/null || \
			{ echo "   Using default builder..."; docker buildx use default 2>/dev/null || true; }; \
		fi; \
		echo "🏗️  Building and pushing with Buildx..."; \
		if docker buildx build --platform $$PLATFORM -t $$FULL_IMAGE --push .; then \
			echo "✅ Image pushed: $$FULL_IMAGE"; \
			if [ "$$IMAGE_TAG" != "latest" ]; then \
				echo "📌 Also tagging as latest..."; \
				LATEST_IMAGE="$$REGISTRY:latest"; \
				if docker buildx build --platform $$PLATFORM -t $$LATEST_IMAGE --push .; then \
					echo "✅ Latest tag pushed: $$LATEST_IMAGE"; \
				else \
					echo "⚠️  Failed to push latest tag"; \
				fi; \
			fi; \
		else \
			echo "❌ Build failed!"; \
			exit 1; \
		fi; \
	else \
		echo "⚠️  Docker Buildx not available, using standard Docker build..."; \
		echo "⚠️  Note: This may not work for cross-platform builds (e.g., Mac to Linux)"; \
		if docker build -t $$FULL_IMAGE . && docker push $$FULL_IMAGE; then \
			echo "✅ Image pushed: $$FULL_IMAGE"; \
			if [ "$$IMAGE_TAG" != "latest" ]; then \
				echo "📌 Also tagging as latest..."; \
				LATEST_IMAGE="$$REGISTRY:latest"; \
				docker tag $$FULL_IMAGE $$LATEST_IMAGE && docker push $$LATEST_IMAGE && \
				echo "✅ Latest tag pushed: $$LATEST_IMAGE" || echo "⚠️  Failed to push latest tag"; \
			fi; \
		else \
			echo "❌ Build or push failed!"; \
			exit 1; \
		fi; \
	fi

deploy-prod:
	@if [ -z "$(REGISTRY)" ]; then \
		echo "❌ REGISTRY not specified"; \
		echo "Usage: make deploy-prod REGISTRY=your-registry.io [TAG=v1.0.0] [SKIP_DB=true]"; \
		echo ""; \
		echo "This deploys to a production cloud Kubernetes cluster."; \
		echo "Make sure you have:"; \
		echo "  1. kubectl configured for your cluster"; \
		echo "  2. Image pushed to registry (run 'make build-push' first)"; \
		echo "  3. Secrets configured in the cluster"; \
		echo ""; \
		echo "Examples:"; \
		echo "  make deploy-prod REGISTRY=your-username TAG=v1.0.0"; \
		echo "  make deploy-prod REGISTRY=registry.digitalocean.com/your-registry TAG=v1.0.0 SKIP_DB=true"; \
		exit 1; \
	fi; \
	echo "🚀 Deploying to production cloud cluster..."; \
	echo "⚠️  Make sure your kubectl is configured for the correct cluster!"; \
	kubectl config current-context; \
	read -p "Continue with this cluster? (yes/no): " confirm; \
	if [ "$$confirm" != "yes" ]; then \
		echo "Deployment cancelled."; \
		exit 0; \
	fi; \
	IMAGE_TAG=$${TAG:-latest}; \
	cd k8s && \
	IMAGE_REGISTRY="$$REGISTRY" IMAGE_TAG="$$IMAGE_TAG" \
	./deploy-production.sh \
		--registry="$$REGISTRY" \
		--image-tag="$$IMAGE_TAG" \
		$$([ "$(SKIP_DB)" = "true" ] && echo "--skip-db" || echo "")

deploy-vps:
	@echo "🚀 Deploying to VPS/Server (k3s/microk8s)..."
	@echo "⚠️  Make sure you're on the server or have kubectl configured for it!"
	@if kubectl cluster-info &> /dev/null; then \
		kubectl config current-context; \
	else \
		echo "⚠️  Cannot connect to cluster. On server, install:"; \
		echo "   k3s: curl -sfL https://get.k3s.io | sh -"; \
		echo "   or microk8s: sudo snap install microk8s --classic"; \
		exit 1; \
	fi; \
	if [ "$$NO_CONFIRM" != "true" ]; then \
		read -p "Continue with this cluster? (yes/no): " confirm; \
		if [ "$$confirm" != "yes" ]; then \
			echo "Deployment cancelled."; \
			exit 0; \
		fi; \
	fi; \
	cd k8s && \
	SKIP_BUILD=$${SKIP_BUILD:-false} \
	REGISTRY=$${REGISTRY:-} \
	IMAGE_TAG=$${IMAGE_TAG:-latest} \
	NO_CONFIRM=$${NO_CONFIRM:-false} \
	SKIP_DB=$${SKIP_DB:-false} \
	./deploy-vps.sh \
	$$([ "$$SKIP_BUILD" = "true" ] && echo "--skip-build" || echo "") \
	$$([ -n "$$REGISTRY" ] && echo "--registry=$$REGISTRY" || echo "") \
	$$([ -n "$$IMAGE_TAG" ] && [ "$$IMAGE_TAG" != "latest" ] && echo "--image-tag=$$IMAGE_TAG" || echo "") \
	$$([ "$$NO_CONFIRM" = "true" ] && echo "--no-confirm" || echo "") \
	$$([ "$$SKIP_DB" = "true" ] && echo "--skip-db" || echo "")

stop:
	@echo "🛑 Stopping application (preserving data/PVCs)..."
	@pkill -f "kubectl port-forward.*8000" 2>/dev/null || true
	@echo "✓ Port-forwards stopped"
	@kubectl scale deployment kcca-kla-connect-web --replicas=0 -n kcca-kla-connect 2>/dev/null || echo "ℹ️  Deployment not found or already scaled to 0"
	@kubectl delete deployment kcca-kla-connect-web -n kcca-kla-connect --ignore-not-found=true && echo "✓ Deployment deleted" || true
	@kubectl delete service kcca-kla-connect-service -n kcca-kla-connect --ignore-not-found=true && echo "✓ Service deleted" || true
	@kubectl delete service kcca-kla-connect-internal -n kcca-kla-connect --ignore-not-found=true && echo "✓ Internal service deleted" || true
	@kubectl delete ingress kcca-kla-connect-ingress -n kcca-kla-connect --ignore-not-found=true && echo "✓ Ingress deleted" || true
	@echo ""
	@echo "✅ App stopped, namespace and PVCs retained: kcca-kla-connect"
	@echo "   To remove EVERYTHING including data: make teardown"

teardown:
	@echo "🧨 TEARDOWN: Deleting namespace (this removes PVCs/data depending on storage class)..."
	@read -p "Are you sure you want to delete namespace 'kcca-kla-connect'? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		kubectl delete namespace kcca-kla-connect --ignore-not-found=true && echo "✓ Namespace deleted" || echo "⚠️  Namespace not found or already deleted"; \
		echo ""; \
		echo "✅ Teardown complete"; \
	else \
		echo "Teardown cancelled."; \
	fi

deploy-ghcr:
	@echo "🚀 Deploying GHCR image (no build) ..."
	@cd k8s && \
	NO_CONFIRM=true SKIP_BUILD=true \
	FULL_IMAGE=ghcr.io/mutesasiratimo/kcca_kla_connect_api:latest \
	./deploy-vps.sh --skip-build --no-confirm --image=$$FULL_IMAGE

deploy-ghcr-remote:
	@echo "🚀 Deploying from GHCR on remote VPS (no repo needed)..."
	@echo "⚠️  This script downloads manifests from GitHub and deploys"
	@echo "   Make sure you're on the VPS or have kubectl configured for it!"
	@if kubectl cluster-info &> /dev/null; then \
		kubectl config current-context; \
	else \
		echo "❌ Cannot connect to cluster. Make sure kubectl is configured."; \
		exit 1; \
	fi; \
	cd k8s && \
	IMAGE_TAG=$${IMAGE_TAG:-latest} \
	SKIP_DB=$${SKIP_DB:-false} \
	NO_CONFIRM=$${NO_CONFIRM:-false} \
	./deploy-ghcr-remote.sh \
	$$([ -n "$$IMAGE_TAG" ] && [ "$$IMAGE_TAG" != "latest" ] && echo "--image-tag=$$IMAGE_TAG" || echo "") \
	$$([ "$$SKIP_DB" = "true" ] && echo "--skip-db" || echo "") \
	$$([ "$$NO_CONFIRM" = "true" ] && echo "--no-confirm" || echo "")

restart:
	@echo "🔁 Restarting application (preserving data/PVCs)..."
	@$(MAKE) stop
	@echo "🏗️  Rebuilding image and redeploying to existing cluster..."
	@cd k8s && ./deploy-full.sh --skip-cluster

restart-fast:
	@echo "🔁 Restarting application quickly (no rebuild, preserving data/PVCs)..."
	@$(MAKE) stop
	@echo "🚀 Redeploying to existing cluster (skipping build)..."
	@cd k8s && ./deploy-full.sh --skip-cluster --skip-build

clean:
	@echo "🧹 Cleaning up..."
	@kubectl delete namespace kcca-kla-connect --ignore-not-found=true
	@kind delete cluster --name kcca-kla-connect 2>/dev/null || true
	@echo "✓ Cleanup complete"

logs:
	@kubectl logs -f deployment/kcca-kla-connect-web -n kcca-kla-connect

status:
	@kubectl get all -n kcca-kla-connect

scale:
	@if [ -z "$(NUM)" ]; then \
		echo "Usage: make scale NUM=5"; \
	else \
		kubectl scale deployment kcca-kla-connect-web --replicas=$(NUM) -n kcca-kla-connect; \
		echo "✓ Scaled to $(NUM) replicas"; \
	fi

port-forward:
	@echo "🔗 Starting port-forward to http://localhost:8000"
	@kubectl port-forward -n kcca-kla-connect service/kcca-kla-connect-internal 8000:8000

port-forward-network:
	@echo "🌐 Starting network-exposed port-forward..."
	@echo "   This makes the API accessible from other devices on your network"
	@HOST_IP=$$(ifconfig | grep -E "inet.*broadcast" | awk '{print $$2}' | head -1); \
	if [ -z "$$HOST_IP" ]; then \
		echo "⚠️  Could not determine host IP. Using 0.0.0.0"; \
		HOST_IP="0.0.0.0"; \
	fi; \
	echo "   Access from other devices: http://$$HOST_IP:8000/docs"; \
	echo "   Press Ctrl+C to stop"; \
	kubectl port-forward -n kcca-kla-connect --address 0.0.0.0 service/kcca-kla-connect-internal 8000:8000

pods:
	@kubectl get pods -n kcca-kla-connect

describe:
	@kubectl describe deployment kcca-kla-connect-web -n kcca-kla-connect

# Database Backup Commands
backup-setup:
	@echo "📦 Setting up automated daily backups..."
	@kubectl apply -f k8s/backup-job.yaml
	@echo "✓ Automated backups configured (runs daily at 2 AM)"
	@echo "  View backups: kubectl get cronjob postgres-backup -n kcca-kla-connect"

backup-manual:
	@echo "💾 Creating manual backup..."
	@kubectl apply -f k8s/manual-backup-job.yaml
	@echo "⏳ Waiting for backup to complete..."
	@sleep 3
	@kubectl wait --for=condition=complete job/postgres-backup-manual -n kcca-kla-connect --timeout=300s || echo "⚠️  Backup job still running or completed with errors"
	@echo ""
	@echo "✅ Backup completed!"
	@echo "  Check backup pod: kubectl get pods -n kcca-kla-connect | grep backup"
	@echo "  View backup logs: kubectl logs -n kcca-kla-connect job/postgres-backup-manual"

backup-download:
	@echo "📥 Downloading latest backup..."
	@BACKUP_POD=$$(kubectl get pods -n kcca-kla-connect -l component=backup --field-selector=status.phase=Succeeded -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) || BACKUP_POD=""; \
	if [ -z "$$BACKUP_POD" ]; then \
		echo "❌ No completed backup pod found. Run 'make backup-manual' first."; \
		exit 1; \
	fi; \
	BACKUP_FILE=$$(kubectl exec -n kcca-kla-connect $$BACKUP_POD -- ls -t /backups/*.sql.gz 2>/dev/null | head -1 | xargs basename 2>/dev/null); \
	if [ -z "$$BACKUP_FILE" ]; then \
		echo "❌ No backup file found in pod."; \
		exit 1; \
	fi; \
	echo "Found backup: $$BACKUP_FILE"; \
	kubectl cp kcca-kla-connect/$$BACKUP_POD:/backups/$$BACKUP_FILE ./$$BACKUP_FILE && \
	echo "✅ Backup downloaded: ./$$BACKUP_FILE" || \
	echo "⚠️  Could not download. Try: kubectl cp kcca-kla-connect/$$BACKUP_POD:/backups/<file> ./"

backup: backup-manual
	@sleep 5
	@$(MAKE) backup-download

restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore FILE=backup-20240101-120000.sql.gz"; \
		echo "  Or use: make restore FILE=/path/to/backup.sql.gz"; \
		exit 1; \
	fi; \
	if [ ! -f "$(FILE)" ]; then \
		echo "❌ Backup file not found: $(FILE)"; \
		exit 1; \
	fi; \
	if [ "$(RESTORE_AUTO)" != "yes" ]; then \
		echo "⚠️  WARNING: This will restore the database from backup."; \
		echo "   Current data will be replaced!"; \
		read -p "Continue? (yes/no): " confirm; \
		if [ "$$confirm" != "yes" ]; then \
			echo "Restore cancelled."; \
			exit 0; \
		fi; \
	fi; \
	echo "📥 Copying backup file to pod..."; \
	BACKUP_NAME=$$(basename "$(FILE)"); \
	POSTGRES_POD=$$(kubectl get pods -n kcca-kla-connect -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POSTGRES_POD" ]; then \
		echo "❌ PostgreSQL pod not found. Is the database deployed?"; \
		exit 1; \
	fi; \
	kubectl cp "$(FILE)" kcca-kla-connect/$$POSTGRES_POD:/tmp/$$BACKUP_NAME; \
	echo "🔄 Restoring database..."; \
	kubectl exec -n kcca-kla-connect $$POSTGRES_POD -- \
		bash -c "gunzip -c /tmp/$$BACKUP_NAME | PGPASSWORD=\$$POSTGRES_PASSWORD pg_restore -h localhost -U postgres -d klaconnect --clean --if-exists --verbose" 2>/dev/null || \
	kubectl exec -n kcca-kla-connect $$POSTGRES_POD -- \
		bash -c "gunzip -c /tmp/$$BACKUP_NAME | PGPASSWORD=\$$POSTGRES_PASSWORD psql -h localhost -U postgres -d klaconnect"; \
	echo "✅ Database restored from $(FILE)"

