#!/bin/sh
set -e

echo "=== REDCap Sync Backend ==="

echo "Running migrations..."
uv run python manage.py migrate --noinput

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

echo "Creating superuser if not exists..."
uv run python manage.py shell -c "
from apps.accounts.models import User
import os
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email    = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@redcap.local')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        role='admin',
        organisation='System Administrator'
    )
    print(f'Superuser created: {username}')
else:
    print(f'Superuser already exists: {username}')
"

echo "=== Starting server ==="
exec "$@"