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
	@echo "  make build-push      - Build and push image to registry"
	@echo "  make stop            - Stop all deployments (keeps cluster)"
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
		echo "Usage: make build-push REGISTRY=your-registry.io [TAG=v1.0.0]"; \
		echo ""; \
		echo "Examples:"; \
		echo "  Docker Hub:  make build-push REGISTRY=your-username TAG=v1.0.0"; \
		echo "  DigitalOcean: make build-push REGISTRY=registry.digitalocean.com/your-registry TAG=v1.0.0"; \
		echo "  AWS ECR:    make build-push REGISTRY=123456789012.dkr.ecr.us-east-1.amazonaws.com/your-repo TAG=v1.0.0"; \
		exit 1; \
	fi; \
	IMAGE_TAG=$${TAG:-latest}; \
	FULL_IMAGE="$$REGISTRY/kcca-kla-connect-api:$$IMAGE_TAG"; \
	echo "🏗️  Building image: $$FULL_IMAGE"; \
	docker build -t $$FULL_IMAGE .; \
	echo "📤 Pushing image to registry..."; \
	docker push $$FULL_IMAGE; \
	echo "✅ Image pushed: $$FULL_IMAGE"; \
	if [ "$$IMAGE_TAG" != "latest" ]; then \
		echo "📌 Also tagging as latest..."; \
		docker tag $$FULL_IMAGE $$REGISTRY/kcca-kla-connect-api:latest; \
		docker push $$REGISTRY/kcca-kla-connect-api:latest; \
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
	read -p "Continue with this cluster? (yes/no): " confirm; \
	if [ "$$confirm" != "yes" ]; then \
		echo "Deployment cancelled."; \
		exit 0; \
	fi; \
	cd k8s && ./deploy-vps.sh

stop:
	@echo "🛑 Stopping all deployments..."
	@pkill -f "kubectl port-forward.*8000" 2>/dev/null || true
	@echo "✓ Port-forwards stopped"
	@kubectl delete namespace kcca-kla-connect --ignore-not-found=true && echo "✓ Namespace deleted" || echo "⚠️  Namespace not found or already deleted"
	@echo ""
	@echo "✅ All deployments stopped (cluster still running)"
	@echo "   To also delete the cluster: make clean"

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

