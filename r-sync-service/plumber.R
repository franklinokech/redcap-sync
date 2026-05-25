# r-sync-service/plumber.R
# ---------------------------------------------------------------------------
# Plumber API — exposes sync_logic.R over HTTP.
# Endpoints accept parameters via query string OR JSON body (with aliases).
# ---------------------------------------------------------------------------

library(plumber)
library(jsonlite)

source("sync_logic.R")   # brings in %||%, validate_token, preview_records, sync_records

# ---------------------------------------------------------------------------
# auth_check: honour R_SYNC_SERVICE_API_KEY env var if set
# ---------------------------------------------------------------------------
auth_check <- function(req) {
  expected <- Sys.getenv("R_SYNC_SERVICE_API_KEY", unset = "")
  if (!nzchar(expected)) return(invisible(TRUE))
  provided <- req$HTTP_X_API_KEY %||% ""
  if (!identical(provided, expected)) stop("Unauthorized: invalid or missing X-Api-Key header")
  invisible(TRUE)
}

# ---------------------------------------------------------------------------
# safe_handler: wraps every endpoint body; maps errors → HTTP status codes
# ---------------------------------------------------------------------------
safe_handler <- function(expr_fn, res) {
  tryCatch(expr_fn(), error = function(e) {
    msg <- conditionMessage(e)
    res$status <- if (grepl("^Unauthorized", msg)) 401L else 500L
    list(success = FALSE, message = msg)
  })
}

# ---------------------------------------------------------------------------
# parse_body: decode JSON body once per request (plumber only injects
# declared @param names; everything else lives in req$postBody)
# ---------------------------------------------------------------------------
parse_body <- function(req) {
  tryCatch(
    jsonlite::fromJSON(req$postBody %||% "{}", simplifyVector = FALSE),
    error = function(e) list()
  )
}

# Flatten a JSON array or plain string → character vector (or NULL if empty)
normalise_vec <- function(x) {
  if (is.null(x)) return(NULL)
  x <- trimws(as.character(unlist(x, use.names = FALSE)))
  x <- x[nzchar(x)]
  if (length(x) == 0L) NULL else x
}

# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

#* @get /health
#* @serializer unboxedJSON
function(res) {
  res$status <- 200L
  list(status = "ok", service = "r-sync-service")
}

# ---------------------------------------------------------------------------
# POST /project-info   (alias: POST /validate-token)
# ---------------------------------------------------------------------------

#* @post /project-info
#* @serializer unboxedJSON
#* @param token      REDCap API token
#* @param redcap_url Base URL of the REDCap instance
function(req, res, token = "", redcap_url = "") {
  safe_handler(res = res, expr_fn = function() {
    auth_check(req)
    body <- parse_body(req)

    if (!nzchar(trimws(token)))      token      <- body[["token"]]      %||% ""
    if (!nzchar(trimws(redcap_url))) redcap_url <- body[["redcap_url"]] %||%
                                                   body[["url"]]        %||% ""

    if (!nzchar(trimws(token))) {
      res$status <- 400L; return(list(success = FALSE, message = "token is required"))
    }
    if (!nzchar(trimws(redcap_url))) {
      res$status <- 400L; return(list(success = FALSE, message = "redcap_url is required"))
    }

    result <- validate_token(token = token, redcap_url = redcap_url)
    res$status <- if (isTRUE(result$success)) 200L else 400L
    result
  })
}

#* @post /validate-token
#* @serializer unboxedJSON
#* @param token      REDCap API token
#* @param redcap_url Base URL of the REDCap instance
function(req, res, token = "", redcap_url = "") {
  safe_handler(res = res, expr_fn = function() {
    auth_check(req)
    body <- parse_body(req)

    if (!nzchar(trimws(token)))      token      <- body[["token"]]      %||% ""
    if (!nzchar(trimws(redcap_url))) redcap_url <- body[["redcap_url"]] %||%
                                                   body[["url"]]        %||% ""

    if (!nzchar(trimws(token))) {
      res$status <- 400L; return(list(success = FALSE, message = "token is required"))
    }
    if (!nzchar(trimws(redcap_url))) {
      res$status <- 400L; return(list(success = FALSE, message = "redcap_url is required"))
    }

    result <- validate_token(token = token, redcap_url = redcap_url)
    res$status <- if (isTRUE(result$success)) 200L else 400L
    result
  })
}

# ---------------------------------------------------------------------------
# POST /preview
# ---------------------------------------------------------------------------

#* @post /preview
#* @serializer unboxedJSON
#* @param token      REDCap API token
#* @param redcap_url Base URL of the REDCap instance
#* @param date_from  Optional start date YYYY-MM-DD
#* @param date_to    Optional end date YYYY-MM-DD
#* @param forms      Optional form filter (string or JSON array)
#* @param fields     Optional field filter (string or JSON array)
function(req, res,
         token      = "",
         redcap_url = "",
         date_from  = NULL,
         date_to    = NULL,
         forms      = NULL,
         fields     = NULL) {

  safe_handler(res = res, expr_fn = function() {
    auth_check(req)
    body <- parse_body(req)

    if (!nzchar(trimws(token)))      token      <- body[["token"]]      %||% ""
    if (!nzchar(trimws(redcap_url))) redcap_url <- body[["redcap_url"]] %||%
                                                   body[["url"]]        %||% ""
    if (is.null(date_from)) date_from <- body[["date_from"]] %||% NULL
    if (is.null(date_to))   date_to   <- body[["date_to"]]   %||% NULL
    if (is.null(forms))     forms     <- body[["forms"]]
    if (is.null(fields))    fields    <- body[["fields"]]

    if (!nzchar(trimws(token))) {
      res$status <- 400L; return(list(success = FALSE, message = "token is required"))
    }
    if (!nzchar(trimws(redcap_url))) {
      res$status <- 400L; return(list(success = FALSE, message = "redcap_url is required"))
    }

    result <- preview_records(
      token      = token,
      redcap_url = redcap_url,
      date_from  = date_from,
      date_to    = date_to,
      forms      = normalise_vec(forms),
      fields     = normalise_vec(fields)
    )

    res$status <- if (isTRUE(result$success)) 200L else 400L
    result
  })
}

# ---------------------------------------------------------------------------
# POST /sync
#
# Reads records from a site REDCap project and writes them to the central
# registry.  Accepts parameters via query string or JSON body.
#
# Aliases accepted in JSON body:
#   token            → source_token
#   redcap_url       → source_url
#   target_token     → registry_token
#   target_redcap_url→ registry_url
#
# Response keys (must match core/r_client.py _require_keys):
#   records_pulled, records_pushed, records_skipped
# ---------------------------------------------------------------------------

#* @post /sync
#* @serializer unboxedJSON
#* @param token               Source REDCap API token
#* @param redcap_url          Source REDCap URL
#* @param target_token        Target (registry) REDCap API token
#* @param target_redcap_url   Target (registry) REDCap URL
#* @param date_from           Optional start date YYYY-MM-DD
#* @param date_to             Optional end date YYYY-MM-DD
#* @param forms               Optional form filter (string or JSON array)
#* @param fields              Optional field filter (string or JSON array)
#* @param record_id_prefix    Prefix applied to record IDs before writing
#* @param overwrite_with_blanks Overwrite existing fields with blank values
function(req, res,
         token                 = "",
         redcap_url            = "",
         target_token          = "",
         target_redcap_url     = "",
         date_from             = NULL,
         date_to               = NULL,
         forms                 = NULL,
         fields                = NULL,
         record_id_prefix      = "",
         overwrite_with_blanks = FALSE) {

  safe_handler(res = res, expr_fn = function() {
    auth_check(req)
    body <- parse_body(req)

    # ── Resolve aliases ────────────────────────────────────────────────
    if (!nzchar(trimws(token))) {
      token <- body[["token"]] %||% body[["source_token"]] %||% ""
    }
    if (!nzchar(trimws(redcap_url))) {
      redcap_url <- body[["redcap_url"]] %||% body[["source_url"]] %||% ""
    }
    if (!nzchar(trimws(target_token))) {
      target_token <- body[["target_token"]] %||% body[["registry_token"]] %||% ""
    }
    if (!nzchar(trimws(target_redcap_url))) {
      target_redcap_url <- body[["target_redcap_url"]] %||%
                           body[["registry_url"]] %||% ""
    }

    if (is.null(date_from)) date_from <- body[["date_from"]] %||% NULL
    if (is.null(date_to))   date_to   <- body[["date_to"]]   %||% NULL
    if (is.null(forms))     forms     <- body[["forms"]]
    if (is.null(fields))    fields    <- body[["fields"]]

    if (!nzchar(trimws(record_id_prefix %||% ""))) {
      record_id_prefix <- body[["record_id_prefix"]] %||% ""
    }

    # overwrite_with_blanks may arrive as string "false"/"true" from query params
    owb <- isTRUE(as.logical(
      body[["overwrite_with_blanks"]] %||% overwrite_with_blanks
    ))

    # ── Validate required params ───────────────────────────────────────
    checks <- list(
      "token (source REDCap API token)"          = token,
      "redcap_url (source REDCap URL)"           = redcap_url,
      "target_token (registry REDCap API token)" = target_token,
      "target_redcap_url (registry REDCap URL)"  = target_redcap_url
    )
    for (label in names(checks)) {
      if (!nzchar(trimws(checks[[label]]))) {
        res$status <- 400L
        return(list(success = FALSE, message = sprintf("%s is required", label),
                    code = "MISSING_PARAM"))
      }
    }

    # ── Execute sync ───────────────────────────────────────────────────
    result <- sync_records(
      token                 = token,
      redcap_url            = redcap_url,
      target_token          = target_token,
      target_redcap_url     = target_redcap_url,
      date_from             = date_from,
      date_to               = date_to,
      forms                 = normalise_vec(forms),
      fields                = normalise_vec(fields),
      record_id_prefix      = record_id_prefix,
      overwrite_with_blanks = owb
    )

    res$status <- if (isTRUE(result$success)) 200L else 400L
    result
  })
}
