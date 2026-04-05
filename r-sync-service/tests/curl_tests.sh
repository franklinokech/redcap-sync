#!/usr/bin/env bash
# tests/curl_tests.sh
# Manual curl tests for the REDCap sync plumber service
#
# Usage:
#   chmod +x tests/curl_tests.sh
#   ./tests/curl_tests.sh
#
# Override the base URL:
#   BASE_URL=http://my-server:8000 ./tests/curl_tests.sh
#
# Set real tokens before running sync/preview tests:
#   SOURCE_TOKEN=your32chartoken SOURCE_URL=https://... ./tests/curl_tests.sh

BASE_URL="${BASE_URL:-http://localhost:8000}"

# ── Credentials (replace with real values or set via env) ─────────────────────
SOURCE_TOKEN="${SOURCE_TOKEN:-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX}"
SOURCE_URL="${SOURCE_URL:-https://redcap.yoursite.edu/api/}"
REGISTRY_TOKEN="${REGISTRY_TOKEN:-YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY}"
REGISTRY_URL="${REGISTRY_URL:-https://redcap.central.edu/api/}"

# ── Colour helpers ─────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
sep() { echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
title() { sep; echo -e "${GREEN}▶ $1${NC}"; sep; }

# ── 1. Health check ────────────────────────────────────────────────────────────
title "1. Health check — GET /health"
curl -s -X GET "${BASE_URL}/health" \
  -H "Content-Type: application/json" | python3 -m json.tool

# ── 2. Project info (validates token) ─────────────────────────────────────────
title "2. Project info — POST /project-info"
curl -s -X POST "${BASE_URL}/project-info" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\":      \"${SOURCE_TOKEN}\",
    \"redcap_url\": \"${SOURCE_URL}\"
  }" | python3 -m json.tool

# ── 3. Validation error — missing token ───────────────────────────────────────
title "3. Validation error — empty token"
curl -s -X POST "${BASE_URL}/project-info" \
  -H "Content-Type: application/json" \
  -d '{
    "token":      "",
    "redcap_url": "https://redcap.example.com/api/"
  }' | python3 -m json.tool

# ── 4. Validation error — bad date range ──────────────────────────────────────
title "4. Validation error — date_from after date_to"
curl -s -X POST "${BASE_URL}/preview" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\":      \"${SOURCE_TOKEN}\",
    \"redcap_url\": \"${SOURCE_URL}\",
    \"date_from\":  \"2024-12-01\",
    \"date_to\":    \"2024-01-01\"
  }" | python3 -m json.tool

# ── 5. Preview — date range ────────────────────────────────────────────────────
title "5. Preview — partial date range (no write)"
curl -s -X POST "${BASE_URL}/preview" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\":      \"${SOURCE_TOKEN}\",
    \"redcap_url\": \"${SOURCE_URL}\",
    \"date_from\":  \"2024-01-01\",
    \"date_to\":    \"2024-06-30\",
    \"full_sync\":  false
  }" | python3 -m json.tool

# ── 6. Preview — full sync ─────────────────────────────────────────────────────
title "6. Preview — full sync (no write)"
curl -s -X POST "${BASE_URL}/preview" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\":      \"${SOURCE_TOKEN}\",
    \"redcap_url\": \"${SOURCE_URL}\",
    \"full_sync\":  true
  }" | python3 -m json.tool

# ── 7. Preview — specific fields only ─────────────────────────────────────────
title "7. Preview — specific fields (record_id, dob, site_id)"
curl -s -X POST "${BASE_URL}/preview" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\":      \"${SOURCE_TOKEN}\",
    \"redcap_url\": \"${SOURCE_URL}\",
    \"full_sync\":  true,
    \"fields\":     \"record_id,dob,site_id\"
  }" | python3 -m json.tool

# ── 8. Sync — partial date range ──────────────────────────────────────────────
title "8. Sync — partial date range (WRITES to registry)"
echo -e "${RED}⚠  This writes data. Confirm tokens are correct before running.${NC}"
curl -s -X POST "${BASE_URL}/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_token\":   \"${SOURCE_TOKEN}\",
    \"source_url\":     \"${SOURCE_URL}\",
    \"registry_token\": \"${REGISTRY_TOKEN}\",
    \"registry_url\":   \"${REGISTRY_URL}\",
    \"date_from\":      \"2024-01-01\",
    \"date_to\":        \"2024-06-30\",
    \"full_sync\":      false
  }" | python3 -m json.tool

# ── 9. Sync — full sync ────────────────────────────────────────────────────────
title "9. Full sync (WRITES all records to registry)"
echo -e "${RED}⚠  This writes ALL data. Use with caution.${NC}"
curl -s -X POST "${BASE_URL}/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_token\":   \"${SOURCE_TOKEN}\",
    \"source_url\":     \"${SOURCE_URL}\",
    \"registry_token\": \"${REGISTRY_TOKEN}\",
    \"registry_url\":   \"${REGISTRY_URL}\",
    \"full_sync\":      true
  }" | python3 -m json.tool

# ── 10. Sync — specific forms only ────────────────────────────────────────────
title "10. Sync — specific forms (enrollment, baseline_visit)"
curl -s -X POST "${BASE_URL}/sync" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_token\":   \"${SOURCE_TOKEN}\",
    \"source_url\":     \"${SOURCE_URL}\",
    \"registry_token\": \"${REGISTRY_TOKEN}\",
    \"registry_url\":   \"${REGISTRY_URL}\",
    \"forms\":          \"enrollment,baseline_visit\",
    \"full_sync\":      true
  }" | python3 -m json.tool

sep
echo -e "\n${GREEN}All tests sent. Review output above.${NC}\n"