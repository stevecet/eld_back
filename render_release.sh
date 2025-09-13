#!/usr/bin/env bash
# Make sure the script exits on any error
set -o errexit

echo "=== Running release phase on Render ==="

# Check if the database connection is available
echo "Waiting for database..."
/usr/bin/wait-for-db

# Apply Django database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Release phase complete."