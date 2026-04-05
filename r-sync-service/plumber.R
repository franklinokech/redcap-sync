# plumber.R
# REDCap Sync Service — plumber REST API
# Exposes: /health, /project-info, /preview, /sync
#
# Start with: Rscript run.R
# Or:         plumber::plumb("plumber.R")$run(host="0.0.0.0", port=8000)

library(plumber)
library(jsonlite)
library(logger)
library(here)




source(here::here("sync_logic.R"))

# ── CORS & global filters ─────────────────────────────────────────────────────

#* @filter cors
function(req, res) {
  res$setHeader("Access-Control-Allow-Origin",  "*")
  res$setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
  res$setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Api-Key")

  if (req$REQUEST_METHOD == "OPTIONS") {
    res$status <- 200
    return(list())
  }
  plumber::forward()
}

#* @filter logger
function(req) {
  log_info("{req$REQUEST_METHOD} {req$PATH_INFO} — from {req$REMOTE_ADDR}")
  plumber::forward()
}

# ── Health check ──────────────────────────────────────────────────────────────

#* Service health check
#* @get /health
#* @tag utility
#* @response 200 Service status and version info
function() {
  list(
    status    = "ok",
    service   = "redcap-sync-r-service",
    version   = "1.0.0",
    r_version = as.character(getRversion()),
    timestamp = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  )
}

# ── Project info ──────────────────────────────────────────────────────────────

#* Retrieve REDCap project metadata (validates token + URL)
#* @post /project-info
#* @tag projects
#* @param token:string REDCap API token (32 chars)
#* @param redcap_url:string Full URL to REDCap API endpoint
#* @response 200 Project metadata
#* @response 400 Validation error
#* @response 500 REDCap API error
function(req, res, token = "", redcap_url = "") {

  # Support JSON body
  body <- tryCatch(jsonlite::fromJSON(req$postBody), error = function(e) list())
  if (nchar(token) == 0 && !is.null(body$token))       token      <- body$token
  if (nchar(redcap_url) == 0 && !is.null(body$redcap_url)) redcap_url <- body$redcap_url

  result <- get_project_info(token = token, redcap_url = redcap_url)

  if (!result$success) {
    res$status <- 400
    return(list(success = FALSE, message = result$message))
  }

  list(
    success = TRUE,
    message = result$message,
    info    = result$info
  )
}

# ── Preview (pull only, no write) ─────────────────────────────────────────────

#* Preview records that would be synced — no data is written
#* @post /preview
#* @tag sync
#* @param token:string Source REDCap API token
#* @param redcap_url:string Source REDCap API URL
#* @param date_from:string [optional] Start date YYYY-MM-DD
#* @param date_to:string [optional] End date YYYY-MM-DD
#* @param full_sync:logical [optional] Ignore dates and pull all records
#* @param fields:string [optional] Comma-separated list of fields
#* @response 200 Preview data and record count
#* @response 400 Validation or API error
function(req, res,
         token      = "",
         redcap_url = "",
         date_from  = NULL,
         date_to    = NULL,
         full_sync  = FALSE,
         fields     = NULL) {

  body <- tryCatch(jsonlite::fromJSON(req$postBody), error = function(e) list())
  if (nchar(token) == 0      && !is.null(body$token))      token      <- body$token
  if (nchar(redcap_url) == 0 && !is.null(body$redcap_url)) redcap_url <- body$redcap_url
  if (is.null(date_from)     && !is.null(body$date_from))  date_from  <- body$date_from
  if (is.null(date_to)       && !is.null(body$date_to))    date_to    <- body$date_to
  if (isFALSE(full_sync)     && !is.null(body$full_sync))  full_sync  <- as.logical(body$full_sync)
  if (is.null(fields)        && !is.null(body$fields))     fields     <- body$fields

  # Parse comma-separated fields string
  if (!is.null(fields) && is.character(fields) && grepl(",", fields)) {
    fields <- trimws(strsplit(fields, ",")[[1]])
  }

  result <- preview_records(
    source_token = token,
    source_url   = redcap_url,
    date_from    = date_from,
    date_to      = date_to,
    full_sync    = as.logical(full_sync),
    fields       = fields
  )

  if (!result$success) {
    res$status <- 400
    return(list(success = FALSE, message = result$message))
  }

  list(
    success       = TRUE,
    records_count = result$records_count,
    columns       = result$columns,
    preview       = result$preview,
    message       = result$message
  )
}

# ── Sync (pull + push) ────────────────────────────────────────────────────────

#* Sync records from a source REDCap project to the central registry
#* @post /sync
#* @tag sync
#* @param source_token:string     Source site REDCap API token
#* @param source_url:string       Source site REDCap API URL
#* @param registry_token:string   Central registry REDCap API token
#* @param registry_url:string     Central registry REDCap API URL
#* @param date_from:string        [optional] Start date YYYY-MM-DD (ignored if full_sync=TRUE)
#* @param date_to:string          [optional] End date YYYY-MM-DD (ignored if full_sync=TRUE)
#* @param full_sync:logical       [optional] Pull all records (default FALSE)
#* @param fields:string           [optional] Comma-separated field names to include
#* @param forms:string            [optional] Comma-separated form names to include
#* @param overwrite_with_blanks:logical [optional] Allow blank values to overwrite (default FALSE)
#* @response 200 Sync result with counts and duration
#* @response 400 Validation or sync error
#* @response 500 Unexpected server error
function(req, res,
         source_token          = "",
         source_url            = "",
         registry_token        = "",
         registry_url          = "",
         date_from             = NULL,
         date_to               = NULL,
         full_sync             = FALSE,
         fields                = NULL,
         forms                 = NULL,
         overwrite_with_blanks = FALSE,
         record_id_prefix      = NULL) {

  body <- tryCatch(jsonlite::fromJSON(req$postBody), error = function(e) list())

  # Merge JSON body params (body takes precedence over query params)
  resolve <- function(arg, key) {
    val <- body[[key]]
    if (!is.null(val)) val else arg
  }

  source_token          <- resolve(source_token,          "source_token")
  source_url            <- resolve(source_url,            "source_url")
  registry_token        <- resolve(registry_token,        "registry_token")
  registry_url          <- resolve(registry_url,          "registry_url")
  date_from             <- resolve(date_from,             "date_from")
  date_to               <- resolve(date_to,               "date_to")
  full_sync             <- resolve(full_sync,             "full_sync")
  fields                <- resolve(fields,                "fields")
  forms                 <- resolve(forms,                 "forms")
  overwrite_with_blanks <- resolve(overwrite_with_blanks, "overwrite_with_blanks")
  record_id_prefix      <- resolve(record_id_prefix,      "record_id_prefix")

  # Parse comma-separated strings to vectors
  parse_csv_param <- function(x) {
    if (!is.null(x) && is.character(x) && grepl(",", x))
      trimws(strsplit(x, ",")[[1]])
    else x
  }
  fields <- parse_csv_param(fields)
  forms  <- parse_csv_param(forms)

  result <- tryCatch({
    run_sync(
      source_token          = source_token,
      source_url            = source_url,
      registry_token        = registry_token,
      registry_url          = registry_url,
      date_from             = date_from,
      date_to               = date_to,
      full_sync             = as.logical(full_sync),
      fields                = fields,
      forms                 = forms,
      overwrite_with_blanks = as.logical(overwrite_with_blanks),
      record_id_prefix      = record_id_prefix
    )
  }, error = function(e) {
    log_error("Unhandled error in /sync: {conditionMessage(e)}")
    list(
      success        = FALSE,
      records_pulled = 0,
      records_pushed = 0,
      duration_secs  = 0,
      message        = paste("Internal server error:", conditionMessage(e)),
      errors         = list(conditionMessage(e))
    )
  })

  if (!result$success) {
    res$status <- 400
  }

  result
}