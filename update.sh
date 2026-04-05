#!/bin/bash
# update.sh — Pull latest images and restart
# Usage: bash update.sh
# Usage with version: APP_VERSION=1.1.0 bash update.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== REDCap Sync Update ===${NC}"

# Update APP_VERSION in .env if provided
if [ ! -z "$APP_VERSION" ]; then
    sed -i "s/APP_VERSION=.*/APP_VERSION=$APP_VERSION/" .env
    echo -e "${YELLOW}Updated to version: $APP_VERSION${NC}"
fi

echo -e "${YELLOW}Pulling latest images...${NC}"
docker compose -f docker-compose.prod.yml pull

echo -e "${YELLOW}Restarting services...${NC}"
docker compose -f docker-compose.prod.yml up -d

echo -e "${GREEN}✓ Update complete${NC}"
docker compose -f docker-compose.prod.yml ps