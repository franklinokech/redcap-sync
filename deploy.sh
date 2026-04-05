#!/bin/bash
# deploy.sh — First time deployment script
# Usage: bash deploy.sh

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== REDCap Sync Deployment ===${NC}\n"

# ── Check Docker ──────────────────────────────────────────────────────────────
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}ERROR: Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker found${NC}"

# ── Check .env ────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found — creating from template...${NC}"
    cp .env.template .env
    echo -e "${RED}STOP: Edit .env with your site values then run this script again${NC}"
    echo -e "Command: nano .env"
    exit 1
fi

# Warn if template values not changed
if grep -q "generate-a-unique-key-here" .env; then
    echo -e "${RED}ERROR: .env still has template values — please fill in all fields${NC}"
    exit 1
fi

echo -e "${GREEN}✓ .env found${NC}"

# ── Pull images ───────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Pulling images from DockerHub...${NC}"
docker compose -f docker-compose.prod.yml pull

echo -e "${GREEN}✓ Images pulled${NC}"

# ── Start services ────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Starting services...${NC}"
docker compose -f docker-compose.prod.yml up -d

# ── Wait for backend to be ready ──────────────────────────────────────────────
echo -e "\n${YELLOW}Waiting for backend to be ready...${NC}"
attempt=0
max_attempts=30
until docker compose -f docker-compose.prod.yml exec -T backend \
    python manage.py check --database default &> /dev/null; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo -e "${RED}ERROR: Backend did not start in time${NC}"
        docker compose -f docker-compose.prod.yml logs backend
        exit 1
    fi
    echo "Waiting... ($attempt/$max_attempts)"
    sleep 5
done

echo -e "${GREEN}✓ Services started${NC}"

# ── Status ────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}=== Deployment complete ===${NC}"
echo ""
docker compose -f docker-compose.prod.yml ps
echo ""
echo -e "${GREEN}Access the application:${NC}"
echo -e "  Frontend:  http://localhost:${FRONTEND_PORT:-80}"
echo -e "  API:       http://localhost:${DJANGO_PORT:-8001}/api/"
echo -e "  R service: http://localhost:${R_SERVICE_PORT:-8000}/health"
echo ""
echo -e "${YELLOW}Login with:${NC}"
echo -e "  Username: $(grep DJANGO_SUPERUSER_USERNAME .env | cut -d= -f2)"
echo -e "  Password: (as set in .env)"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  View logs:    docker compose -f docker-compose.prod.yml logs -f"
echo -e "  Stop:         docker compose -f docker-compose.prod.yml down"
echo -e "  Update:       bash update.sh"