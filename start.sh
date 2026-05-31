#!/bin/bash
set -e

echo "======================================"
echo "    Starting Vidhema ERP Web Server   "
echo "======================================"

# Apply database migrations
echo "Applying database migrations..."
python manage.py makemigrations
python manage.py migrate

# Start the Django development server
echo "Starting Django development server..."
python manage.py runserver 0.0.0.0:8000
