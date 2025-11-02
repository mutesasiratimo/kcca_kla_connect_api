# PostgreSQL Backup Guide

This guide explains how to backup and restore your PostgreSQL database in Kubernetes.

## Understanding Data Persistence

### Current Setup
- PostgreSQL uses a **PersistentVolumeClaim (PVC)** named `postgres-pvc`
- Data persists across pod restarts
- **⚠️ IMPORTANT:** When you delete the namespace (`make stop`), the PVC and all data are deleted

### Protecting Your Data

You have several options to keep copies of your database:

1. **Automated Daily Backups** (Recommended)
2. **Manual Backups** (On-demand)
3. **Export Before Stopping** (Before `make stop`)
4. **PVC Retention** (Keep PVC when deleting namespace)

---

## Quick Start

### Setup Automated Backups
```bash
make backup-setup
```
This creates a CronJob that backs up your database daily at 2 AM.

### Create Manual Backup
```bash
make backup-manual
```

### Download Backup to Local
```bash
make backup-download
```

### Full Backup Workflow (Backup + Download)
```bash
make backup
```

### Restore from Backup
```bash
make restore FILE=backup-20240101-120000.sql.gz
```

---

## Method 1: Automated Daily Backups

**Setup:**
```bash
make backup-setup
```

**What it does:**
- Creates a CronJob that runs daily at 2 AM
- Stores backups in a separate PVC (`postgres-backup-pvc`)
- Keeps last 7 days of backups automatically
- Backups are compressed SQL dumps

**View scheduled backups:**
```bash
kubectl get cronjob postgres-backup -n kcca-kla-connect
kubectl get jobs -n kcca-kla-connect | grep backup
```

**List available backups:**
```bash
# Get backup pod
POD=$(kubectl get pods -n kcca-kla-connect -l component=backup -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n kcca-kla-connect $POD -- ls -lh /backups/
```

---

## Method 2: Manual Backup

**Create a backup now:**
```bash
make backup-manual
```

**Or manually:**
```bash
kubectl apply -f k8s/manual-backup-job.yaml
kubectl wait --for=condition=complete job/postgres-backup-manual -n kcca-kla-connect --timeout=300s
```

**Download the backup:**
```bash
make backup-download
```

**Or manually:**
```bash
# Find the backup pod
POD=$(kubectl get pods -n kcca-kla-connect -l component=backup --field-selector=status.phase=Succeeded -o jsonpath='{.items[0].metadata.name}')

# List backups
kubectl exec -n kcca-kla-connect $POD -- ls -lh /backups/

# Download latest backup
BACKUP_FILE=$(kubectl exec -n kcca-kla-connect $POD -- ls -t /backups/*.sql.gz | head -1 | xargs basename)
kubectl cp kcca-kla-connect/$POD:/backups/$BACKUP_FILE ./$BACKUP_FILE
```

---

## Method 3: Export Before Stopping

**Before running `make stop`, export your data:**
```bash
# Step 1: Create backup
make backup

# Step 2: Verify backup file exists locally
ls -lh backup-*.sql.gz

# Step 3: Now safe to stop
make stop
```

**The backup files on your local machine are safe** even after deleting the namespace.

---

## Method 4: Direct Database Export (Alternative)

If you prefer to export directly from the database:

```bash
# Port-forward to database
kubectl port-forward -n kcca-kla-connect service/postgres-service 5432:5432 &

# Export database
PGPASSWORD=changeme123 pg_dump -h localhost -U postgres -d klaconnect -F c -f backup-$(date +%Y%m%d-%H%M%S).dump

# Compress
gzip backup-*.dump

# Stop port-forward
pkill -f "kubectl port-forward.*5432"
```

---

## Restoring from Backup

### Restore to Existing Database

```bash
make restore FILE=backup-20240101-120000.sql.gz
```

### Manual Restore

```bash
# Option 1: Using pg_restore (for custom format)
kubectl cp backup-20240101-120000.sql.gz kcca-kla-connect/<postgres-pod>:/tmp/
kubectl exec -n kcca-kla-connect <postgres-pod> -- \
  bash -c "gunzip -c /tmp/backup-20240101-120000.sql.gz | \
  PGPASSWORD=\$POSTGRES_PASSWORD pg_restore -h localhost -U postgres -d klaconnect --clean --if-exists"

# Option 2: Using psql (for plain SQL)
kubectl exec -n kcca-kla-connect <postgres-pod> -- \
  bash -c "gunzip -c /tmp/backup-20240101-120000.sql.gz | \
  PGPASSWORD=\$POSTGRES_PASSWORD psql -h localhost -U postgres -d klaconnect"
```

---

## Backup Storage

### Where Backups are Stored

1. **In Kubernetes:** 
   - PVC: `postgres-backup-pvc` (10Gi)
   - Location: `/backups/` in backup pods

2. **Locally (after download):**
   - Current directory: `./backup-YYYYMMDD-HHMMSS.sql.gz`

### Backup Retention

- **Automated backups:** Last 7 days (configurable in `backup-job.yaml`)
- **Manual backups:** Until manually deleted or PVC is deleted

---

## Important Notes

### ⚠️ Before Running `make stop`

**If you have important data:**
1. **Always backup first:**
   ```bash
   make backup
   ```

2. **Verify backup exists:**
   ```bash
   ls -lh backup-*.sql.gz
   ```

3. **Then you can safely stop:**
   ```bash
   make stop
   ```

### Data Persistence Rules

| Action | PVC Status | Data Status |
|--------|-----------|-------------|
| Pod restart | ✅ Preserved | ✅ Safe |
| `kubectl delete pod` | ✅ Preserved | ✅ Safe |
| `make stop` | ❌ Deleted | ❌ **Lost** |
| `make clean` | ❌ Deleted | ❌ **Lost** |

**Solution:** Always backup before stopping/cleaning!

---

## Best Practices

1. **Set up automated backups:**
   ```bash
   make backup-setup
   ```

2. **Test restore process** regularly:
   ```bash
   # Create test backup
   make backup-manual
   
   # Download it
   make backup-download
   
   # Test restore (on a test database)
   ```

3. **Keep backups off-cluster:**
   - Download backups to local machine
   - Store in cloud storage (S3, Google Drive, etc.)
   - Version control for database schema dumps

4. **Before major changes:**
   ```bash
   make backup
   ```

---

## Troubleshooting

### Backup job fails
```bash
# Check job status
kubectl get jobs -n kcca-kla-connect | grep backup

# View logs
kubectl logs -n kcca-kla-connect job/postgres-backup-manual
```

### No backup PVC found
```bash
# Create backup PVC
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-backup-pvc
  namespace: kcca-kla-connect
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard
  resources:
    requests:
      storage: 10Gi
EOF
```

### Can't find backup files
```bash
# List all backup pods
kubectl get pods -n kcca-kla-connect -l component=backup

# Check backup PVC
kubectl get pvc postgres-backup-pvc -n kcca-kla-connect
```

---

## Backup File Formats

### Custom Format (`.dump` or `.sql.gz` compressed)
- **Advantages:** Faster, supports parallel restore, compressed
- **Created by:** `pg_dump -F c`
- **Restore with:** `pg_restore`

### Plain SQL (`.sql` or `.sql.gz` compressed)
- **Advantages:** Human-readable, works anywhere
- **Created by:** `pg_dump -F p` (default)
- **Restore with:** `psql`

Both formats are supported by the backup scripts.

---

## Additional Resources

- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [Kubernetes CronJob Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)


