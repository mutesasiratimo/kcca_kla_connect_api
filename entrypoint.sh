#!/bin/bash
set -e

echo "Entrypoint started..."

# Wait for database to be ready
echo "Waiting for database..."
# Use the database host from environment if set, otherwise default to 'db'
DB_HOST=${DATABASE_HOST:-db}
until pg_isready -h "$DB_HOST" -p 5432 -U postgres 2>/dev/null; do
  echo "Database not ready yet, waiting..."
  sleep 2
done

echo "Database is ready!"

# Run migrations
echo "Running migrations..."
cd /app && alembic upgrade head || echo "Migration failed, but continuing..."

# Start the application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload

