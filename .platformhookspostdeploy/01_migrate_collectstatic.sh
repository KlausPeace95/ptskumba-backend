#!/bin/bash

# Exit on any error
set -e

# Set environment variables
export PYTHONPATH=/var/app/current:$PYTHONPATH

# Navigate to application directory
cd /var/app/current

# Run Django migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput --clear

echo "Migration and static file collection completed successfully"