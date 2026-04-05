# REDCap Sync — R Plumber Service

REST API built with [plumber](https://www.rplumber.io/) and [REDCapR](https://ouhscbbmc.github.io/REDCapR/) that handles pulling records from source REDCap projects and pushing them to a central registry.

---

## Quick start

### 1. Install R (≥ 4.2)

```bash
# Ubuntu/Debian
sudo apt-get install r-base r-base-dev libcurl4-openssl-dev libssl-dev libxml2-dev

# macOS (Homebrew)
brew install r
```

### 2. Bootstrap R packages

```bash
cd r-sync-service
Rscript bootstrap.R
```

This runs `renv::restore()` from `renv.lock` — all packages are installed into the project-local `renv/library/` directory, not your system R.

### 3. Start the service

```bash
Rscript run.R
# or
PORT=9000 Rscript run.R
```

**Swagger UI** (interactive API docs): http://localhost:8000/__docs__/

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + version info |
| POST | `/project-info` | Validate token and fetch project metadata |
| POST | `/preview` | Pull records preview — **no write** |
| POST | `/sync` | Pull from source + push to registry |

---

## curl Examples

### Health check
```bash
curl http://localhost:8000/health
```

### Validate a token / project info
```bash
curl -s -X POST http://localhost:8000/project-info \
  -H "Content-Type: application/json" \
  -d '{
    "token":      "YOUR32CHARTOKEN0000000000000000",
    "redcap_url": "https://redcap.yoursite.edu/api/"
  }' | python3 -m json.tool
```

### Preview — date range (no write)
```bash
curl -s -X POST http://localhost:8000/preview \
  -H "Content-Type: application/json" \
  -d '{
    "token":      "YOUR32CHARTOKEN0000000000000000",
    "redcap_url": "https://redcap.yoursite.edu/api/",
    "date_from":  "2024-01-01",
    "date_to":    "2024-06-30"
  }' | python3 -m json.tool
```

### Preview — full project
```bash
curl -s -X POST http://localhost:8000/preview \
  -H "Content-Type: application/json" \
  -d '{
    "token":      "YOUR32CHARTOKEN0000000000000000",
    "redcap_url": "https://redcap.yoursite.edu/api/",
    "full_sync":  true
  }' | python3 -m json.tool
```

### Sync — partial date range
```bash
curl -s -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{
    "source_token":    "SOURCE32CHARTOKEN000000000000000",
    "source_url":      "https://redcap.yoursite.edu/api/",
    "registry_token":  "REGISTRY32CHARTOKEN00000000000000",
    "registry_url":    "https://redcap.central.edu/api/",
    "date_from":       "2024-01-01",
    "date_to":         "2024-06-30"
  }' | python3 -m json.tool
```

### Sync — full sync, specific forms
```bash
curl -s -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{
    "source_token":    "SOURCE32CHARTOKEN000000000000000",
    "source_url":      "https://redcap.yoursite.edu/api/",
    "registry_token":  "REGISTRY32CHARTOKEN00000000000000",
    "registry_url":    "https://redcap.central.edu/api/",
    "full_sync":       true,
    "forms":           "enrollment,baseline_visit,follow_up"
  }' | python3 -m json.tool
```

### Run all curl tests at once
```bash
chmod +x tests/curl_tests.sh

# With placeholder tokens (tests validation errors + health)
./tests/curl_tests.sh

# With real tokens
SOURCE_TOKEN=your32chartoken \
SOURCE_URL=https://redcap.yoursite.edu/api/ \
REGISTRY_TOKEN=registry32chartoken \
REGISTRY_URL=https://redcap.central.edu/api/ \
./tests/curl_tests.sh
```

---

## Expected responses

### `GET /health` → 200
```json
{
  "status": "ok",
  "service": "redcap-sync-r-service",
  "version": "1.0.0",
  "r_version": "4.3.2",
  "timestamp": "2024-07-15T10:30:00Z"
}
```

### `POST /sync` → 200 (success)
```json
{
  "success": true,
  "records_pulled": 142,
  "records_pushed": 142,
  "duration_secs": 3.84,
  "message": "Sync complete. Pulled 142 records, pushed 142 to registry.",
  "errors": []
}
```

### `POST /sync` → 400 (validation error)
```json
{
  "success": false,
  "message": "Validation errors: API token must be 32 characters"
}
```

---

## Running with Docker

```bash
# Build
docker build -t redcap-sync-r .

# Run
docker run -p 8000:8000 redcap-sync-r

# Run with debug logging
docker run -p 8000:8000 -e DEBUG=true redcap-sync-r
```

---

## Running unit tests

```bash
cd r-sync-service
Rscript tests/test_sync_logic.R
```

---

## File reference

| File | Purpose |
|------|---------|
| `plumber.R` | HTTP endpoints (routes, filters, CORS) |
| `sync_logic.R` | REDCapR pull/push business logic |
| `run.R` | Server entrypoint (host/port config) |
| `bootstrap.R` | One-time package install script |
| `renv.lock` | Pinned package versions |
| `.Rprofile` | Auto-activates renv on `Rscript` |
| `tests/curl_tests.sh` | curl integration tests |
| `tests/test_sync_logic.R` | R unit tests (no network needed) |
| `Dockerfile` | Container image |

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Listening port |
| `HOST` | `0.0.0.0` | Bind address |
| `DEBUG` | `false` | Enable plumber debug mode |

---

## Notes

- `date_from` / `date_to` use REDCapR's `date_begin` / `date_end` parameters which filter on the record's **last modified date** — confirm this matches your instrument's date field if needed.
- `full_sync=true` ignores all date parameters.
- Tokens are passed per-request and never stored by this service — storage and encryption are handled by the Django backend.
- Logs are written to `logs/sync_YYYYMMDD.log` and also printed to stdout.