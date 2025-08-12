#!/bin/sh
set -e

# This entrypoint is used by both the Cloud Run service and the migration job.
# The IS_MIGRATION_JOB environment variable is used to distinguish between the two.

if [ "$IS_MIGRATION_JOB" = "True" ]; then
  # Run migrations
  echo "Running database migrations..."
  python manage.py migrate --noinput
  echo "Migrations complete."
else
  # Run the web server
  echo "Starting web server..."
  exec uvicorn tranceautom.asgi:application --host 0.0.0.0 --port 8080 --workers 4
fi