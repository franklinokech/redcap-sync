# REDCap Sync

Multi-site REDCap data synchronisation system.

## Requirements

- Docker
- Docker Compose
- Git

## First time deployment
```bash
# 1. Clone the repository
git clone https://github.com/franklinokech/redcap-sync.git
cd redcap-sync

# 2. Copy and edit the environment file
cp .env.template .env
nano .env    # fill in your site-specific values

# 3. Deploy
bash deploy.sh
```

## Access

- Frontend: http://localhost
- API: http://localhost:8001/api/
- R service: http://localhost:8000/health

## Update to a new version
```bash
bash update.sh
# or for a specific version:
APP_VERSION=1.1.0 bash update.sh
```

## Useful commands
```bash
# View all logs
docker compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker compose -f docker-compose.prod.yml logs -f backend

# Stop all services
docker compose -f docker-compose.prod.yml down

# Stop and wipe database (CAUTION)
docker compose -f docker-compose.prod.yml down -v

# Open Django shell
docker compose -f docker-compose.prod.yml exec backend python manage.py shell

# Create another admin user
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py createsuperuser
```

## Environment variables

See `.env.template` for all available configuration options.

## Support

Contact your system administrator.