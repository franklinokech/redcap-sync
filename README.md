# REDCap Sync

A full-stack REDCap synchronization platform for securely validating, previewing, and synchronizing REDCap projects across institutions and environments.

Designed for clinical research workflows, multi-site studies, and health informatics environments where REDCap interoperability and controlled synchronization are required.

---

# Repository

```bash
git clone git@github.com:franklinokech/redcap-sync.git
cd redcap-sync
```

---

# Overview

REDCap Sync provides:

- Secure REDCap API token management
- Project validation against REDCap instances
- Previewing records before synchronization
- Asynchronous sync execution using Celery
- Multi-site project registry management
- Docker-based local development environment
- Frontend SPA for workflow management
- Dedicated R service for REDCapR-powered operations

The platform separates:

- UI and orchestration (Vue + Django)
- Sync engine (R + REDCapR)
- Background processing (Celery + Redis)
- Persistence (PostgreSQL)

This architecture allows scalable, maintainable, and reproducible synchronization workflows.

---

# Tech Stack

## Backend

- Python 3.14
- Django
- Django REST Framework
- SimpleJWT
- Gunicorn
- Celery
- Redis
- PostgreSQL
- HTTPX
- python-decouple

## Frontend

- Vue 3
- Vue Router
- Pinia
- Axios
- Vite
- Nginx

## R Sync Service

- R
- Plumber
- REDCapR
- httr2
- jsonlite

## Infrastructure

- Docker
- Docker Compose
- Nginx reverse proxy
- Alpine Linux containers

---

# Architecture

```text
Frontend (Vue + Nginx)
        |
        v
Backend API (Django REST)
        |
        +----------------+
        |                |
        v                v
 Redis / Celery      PostgreSQL
        |
        v
R Sync Service (Plumber + REDCapR)
        |
        v
REDCap Instances
```

---

# Local Development Setup

## 1. Clone Repository

```bash
git clone git@github.com:franklinokech/redcap-sync.git
cd redcap-sync
```

---

## 2. Create Environment File

```bash
cp .env.example .env
```

---

## 3. Configure Environment Variables

Example local development configuration:

```env
DEBUG=True
DJANGO_PORT=8001
FRONTEND_PORT=3000
R_SERVICE_PORT=8000
VITE_API_URL=http://localhost:8001
```

---

## 4. Local REDCap Access (Important)

If your REDCap instance runs locally on your host machine:

```text
http://redcap.local/api/
```

Docker containers cannot automatically resolve your host machine aliases.

This project uses:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

inside Docker Compose to allow containers to communicate with services running on the host machine.

Recommended local REDCap URL:

```text
http://host.docker.internal/api/
```

---

## 5. Start Services

```bash
docker compose -f docker-compose.dev.yml up --build
```

Detached mode:

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

---

## 6. Verify Services

```bash
docker compose -f docker-compose.dev.yml ps
```

Expected services:

- backend
- frontend
- db
- redis
- celery
- celery-beat
- r-service

---

# Application URLs

## Frontend

```text
http://localhost:3000
```

## Django API

```text
http://localhost:8001/api/
```

## Django Admin

```text
http://localhost:3000/admin/
```

## R Sync Service

```text
http://localhost:8000/health
```

---

# Initial Django Setup

## Run Migrations

```bash
docker exec -it redcap-sync-backend-1 python manage.py migrate
```

## Create Superuser

```bash
docker exec -it redcap-sync-backend-1 python manage.py createsuperuser
```

---

# Docker Networking Notes

Inside containers:

- `localhost` means the container itself
- not your host machine

Use:

```text
host.docker.internal
```

for accessing host services.

---

# Common Development Commands

## View Logs

```bash
docker compose -f docker-compose.dev.yml logs -f
```

## Backend Logs

```bash
docker compose -f docker-compose.dev.yml logs -f backend
```

## R Service Logs

```bash
docker compose -f docker-compose.dev.yml logs -f r-service
```

## Celery Logs

```bash
docker compose -f docker-compose.dev.yml logs -f celery
```

---

# Access Container Shells

## Backend

```bash
docker exec -it redcap-sync-backend-1 bash
```

## R Service

```bash
docker exec -it redcap-sync-r-service-1 bash
```

---

# Testing REDCap Connectivity

```bash
curl -X POST http://r-service:8000/validate-token \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_TOKEN",
    "redcap_url": "http://host.docker.internal/api/"
  }'
```

---

# Project Structure

```text
redcap-sync/
│
├── backend/
├── frontend/
├── r-sync-service/
├── docker-compose.dev.yml
├── .env
├── .env.example
└── README.md
```

---

# Frontend Architecture

The frontend uses:

- Vue 3 Composition API
- Pinia state management
- Axios interceptors
- Route guards
- Lazy-loaded views

Features include:

- Silent JWT refresh
- SPA routing
- Centralized API client
- Protected routes

---

# Backend Architecture

The Django backend provides:

- REST APIs
- JWT authentication
- Celery orchestration
- REDCap project management
- Encryption utilities
- Sync coordination

Patterns used:

- Service layer abstraction
- Thin HTTP client wrappers
- Environment-driven configuration
- Background task isolation

---

# R Sync Service

The R service is responsible for:

- REDCap token validation
- REDCap metadata access
- Record preview generation
- Synchronization execution

Implemented with:

- Plumber API
- REDCapR
- httr2

---

# Security Notes

Never commit:

- `.env`
- API tokens
- production secrets
- database dumps

Recommended `.gitignore`:

```gitignore
.env
celerybeat-schedule*
__pycache__/
*.pyc
node_modules/
```

---

# Troubleshooting

## 502 Bad Gateway During Token Validation

Usually caused by:

- Docker container cannot reach REDCap
- invalid REDCap URL
- missing `extra_hosts`
- firewall restrictions

Recommended local REDCap URL:

```text
http://host.docker.internal/api/
```

---

## Django Admin Redirect Problems

Ensure Nginx includes:

```nginx
location /admin/ {
    proxy_pass http://backend:8000;
}
```

---

# Technical Skills Demonstrated

This project demonstrates practical experience with:

## Backend Engineering

- REST API development
- Authentication systems
- Asynchronous task queues
- Service-oriented architecture
- Secure secret handling

## Frontend Engineering

- SPA development
- State management
- Reverse proxy integration

## Data Engineering

- REDCap interoperability
- Clinical research workflows
- ETL-style synchronization

## DevOps & Infrastructure

- Docker containerization
- Docker Compose orchestration
- Nginx reverse proxying
- Linux networking
- Service health checks

## Cross-Language Integration

- Python + R interoperability
- HTTP microservice communication
- Distributed processing workflows

---

# Future Improvements

Potential roadmap:

- OAuth / SSO
- Audit trails
- Real-time sync monitoring
- Kubernetes deployment
- DuckDB integration
- Great Expectations integration

---

# License

MIT License

---

# Author

Franklin Okech

GitHub:

```text
git@github.com:franklinokech/redcap-sync.git
```
