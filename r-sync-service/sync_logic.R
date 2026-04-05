library(REDCapR)
library(dplyr)
library(lubridate)
library(jsonlite)
library(logger)

# ── Logging setup ─────────────────────────────────────────────────────────────

setup_logger <- function(log_dir = "logs") {
  if (!dir.exists(log_dir)) dir.create(log_dir, recursive = TRUE)
  log_file <- file.path(log_dir, paste0("sync_", format(Sys.time(), "%Y%m%d"), ".log"))
  log_appender(appender_tee(log_file))
  log_threshold(INFO)
}

# ── Token validation ──────────────────────────────────────────────────────────

validate_inputs <- function(token, redcap_url) {
  errors <- c()

  if (is.null(token) || nchar(trimws(token)) == 0) {
    errors <- c(errors, "API token is required")
  } else if (nchar(trimws(token)) != 32) {
    errors <- c(errors, "API token must be 32 characters")
  }

  if (is.null(redcap_url) || nchar(trimws(redcap_url)) == 0) {
    errors <- c(errors, "REDCap URL is required")
  } else if (!grepl("^https?://", redcap_url)) {
    errors <- c(errors, "REDCap URL must start with http:// or https://")
  }

  errors
}

validate_dates <- function(date_from, date_to) {
  errors <- c()

  if (!is.null(date_from) && !is.na(date_from)) {
    parsed <- tryCatch(ymd(date_from), error = function(e) NA)
    if (is.na(parsed)) errors <- c(errors, paste("Invalid date_from:", date_from))
  }

  if (!is.null(date_to) && !is.na(date_to)) {
    parsed <- tryCatch(ymd(date_to), error = function(e) NA)
    if (is.na(parsed)) errors <- c(errors, paste("Invalid date_to:", date_to))
  }

  if (!is.null(date_from) && !is.null(date_to) &&
      !is.na(ymd(date_from)) && !is.na(ymd(date_to))) {
    if (ymd(date_from) > ymd(date_to)) {
      errors <- c(errors, "date_from must be before or equal to date_to")
    }
  }

  errors
}

apply_record_id_prefix <- function(records, prefix) {
  if (is.null(prefix) || nchar(trimws(prefix)) == 0) {
    return(records)
  }

  if (ncol(records) == 0) {
    log_warn("No columns found — skipping prefix application")
    return(records)
  }

  # Use first column as ID field (REDCap convention — works for record_id,
  # survey_id, participant_id, or any custom identifier field)
  id_col <- names(records)[1]
  log_info("Applying prefix '{prefix}' to ID column: '{id_col}'")

  records[[id_col]] <- paste0(trimws(prefix), records[[id_col]])
  log_info("Sample IDs after prefix: {paste(head(records[[id_col]], 3), collapse=', ')}")

  return(records)
}

# ── Pull records from a source site ───────────────────────────────────────────

pull_records <- function(token, redcap_url, date_from = NULL, date_to = NULL,
                          full_sync = FALSE, fields = NULL, forms = NULL) {

  log_info("Pulling records from {redcap_url}")
  log_info("Full sync: {full_sync} | date_from: {date_from} | date_to: {date_to}")

  # Check actual redcap_read signature to handle version differences
  rc_args <- names(formals(REDCapR::redcap_read))

  result <- tryCatch({

    # Base args always supported
    call_args <- list(
      redcap_uri     = redcap_url,
      token          = token,
      fields         = fields,
      forms          = forms,
      verbose        = FALSE,
      config_options = list(ssl_verifypeer = TRUE)
    )

    # Add date filtering using datetime_range_begin/end (POSIXct) — this REDCapR version
    if (!full_sync && (!is.null(date_from) || !is.null(date_to))) {
      if ("datetime_range_begin" %in% rc_args) {
        if (!is.null(date_from))
          call_args$datetime_range_begin <- as.POSIXct(paste(date_from, "00:00:00"), tz = "UTC")
        if (!is.null(date_to))
          call_args$datetime_range_end   <- as.POSIXct(paste(date_to,   "23:59:59"), tz = "UTC")
        log_info("Using datetime_range_begin/end: {date_from} to {date_to}")
      } else {
        log_warn("No date range parameter found in this REDCapR version — returning all records")
      }
    }

    ds <- do.call(REDCapR::redcap_read, call_args)

    if (!ds$success) {
      log_error("Pull failed: {ds$status_code} — {ds$raw_text}")
      return(list(
        success        = FALSE,
        records_count  = 0,
        message        = paste("REDCap API error:", ds$status_code, "-", ds$raw_text),
        data           = NULL
      ))
    }

    records <- ds$data
    log_info("Pulled {nrow(records)} records successfully")

    list(
      success       = TRUE,
      records_count = nrow(records),
      message       = paste("Successfully pulled", nrow(records), "records"),
      data          = records
    )

  }, error = function(e) {
    log_error("Unexpected error during pull: {conditionMessage(e)}")
    list(
      success       = FALSE,
      records_count = 0,
      message       = paste("Unexpected error:", conditionMessage(e)),
      data          = NULL
    )
  })

  result
}

# ── Push records to central registry ─────────────────────────────────────────

push_records <- function(records, registry_token, registry_url,
                          overwrite_with_blanks = FALSE) {

  if (is.null(records) || nrow(records) == 0) {
    log_warn("No records to push — skipping write")
    return(list(
      success       = TRUE,
      records_count = 0,
      message       = "No records to push",
      data          = NULL
    ))
  }

  log_info("Pushing {nrow(records)} records to registry at {registry_url}")

  result <- tryCatch({
    write_result <- redcap_write(
      ds_to_write         = records,
      redcap_uri          = registry_url,
      token               = registry_token,
      overwrite_with_blanks = overwrite_with_blanks,
      verbose             = FALSE,
      config_options      = list(ssl_verifypeer = TRUE)
    )

    if (!write_result$success) {
      log_error("Push failed: {write_result$status_code} — {write_result$raw_text}")
      return(list(
        success       = FALSE,
        records_count = 0,
        message       = paste("Registry write error:", write_result$status_code,
                               "-", write_result$raw_text),
        data          = NULL
      ))
    }

    log_info("Pushed {nrow(records)} records successfully")
    list(
      success       = TRUE,
      records_count = nrow(records),
      message       = paste("Successfully pushed", nrow(records), "records to registry"),
      data          = write_result
    )

  }, error = function(e) {
    log_error("Unexpected error during push: {conditionMessage(e)}")
    list(
      success       = FALSE,
      records_count = 0,
      message       = paste("Unexpected error:", conditionMessage(e)),
      data          = NULL
    )
  })

  result
}

# ── Full sync pipeline ────────────────────────────────────────────────────────

run_sync <- function(source_token, source_url,
                      registry_token, registry_url,
                      date_from = NULL, date_to = NULL,
                      full_sync = FALSE,
                      fields = NULL, forms = NULL,
                      overwrite_with_blanks = FALSE,
                      record_id_prefix = NULL) {

  setup_logger()
  start_time <- Sys.time()

  log_info("=== Sync started ===")
  log_info("Source: {source_url} | Full: {full_sync}")

  # Validate inputs
  source_errors   <- validate_inputs(source_token, source_url)
  registry_errors <- validate_inputs(registry_token, registry_url)
  date_errors     <- validate_dates(date_from, date_to)
  all_errors      <- c(source_errors, registry_errors, date_errors)

  if (length(all_errors) > 0) {
    log_error("Validation failed: {paste(all_errors, collapse='; ')}")
    return(list(
      success        = FALSE,
      records_pulled = 0,
      records_pushed = 0,
      duration_secs  = 0,
      message        = paste("Validation errors:", paste(all_errors, collapse = "; ")),
      errors         = all_errors
    ))
  }

  # Pull from source
  pull_result <- pull_records(
    token      = source_token,
    redcap_url = source_url,
    date_from  = date_from,
    date_to    = date_to,
    full_sync  = full_sync,
    fields     = fields,
    forms      = forms
  )

  if (!pull_result$success) {
    return(list(
      success        = FALSE,
      records_pulled = 0,
      records_pushed = 0,
      duration_secs  = as.numeric(difftime(Sys.time(), start_time, units = "secs")),
      message        = pull_result$message,
      errors         = list(pull_result$message)
    ))
  }

  # This prevents record ID collisions when multiple sites push to same registry
  records_to_push <- apply_record_id_prefix(pull_result$data, record_id_prefix)

  # Push to registry
  push_result <- push_records(
    records               = records_to_push,
    registry_token        = registry_token,
    registry_url          = registry_url,
    overwrite_with_blanks = overwrite_with_blanks
  )

  duration <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))

  if (!push_result$success) {
    return(list(
      success        = FALSE,
      records_pulled = pull_result$records_count,
      records_pushed = 0,
      duration_secs  = duration,
      message        = push_result$message,
      errors         = list(push_result$message)
    ))
  }

  log_info("=== Sync complete in {round(duration, 2)}s | pulled={pull_result$records_count} pushed={push_result$records_count} ===")

  list(
    success        = TRUE,
    records_pulled = pull_result$records_count,
    records_pushed = push_result$records_count,
    duration_secs  = round(duration, 2),
    message        = paste0(
      "Sync complete. Pulled ", pull_result$records_count,
      " records, pushed ", push_result$records_count, " to registry."
    ),
    errors         = list()
  )
}

# ── Preview only (no write) ───────────────────────────────────────────────────

preview_records <- function(source_token, source_url,
                             date_from = NULL, date_to = NULL,
                             full_sync = FALSE, fields = NULL) {

  setup_logger()
  log_info("=== Preview started (no write) ===")

  source_errors <- validate_inputs(source_token, source_url)
  date_errors   <- validate_dates(date_from, date_to)
  all_errors    <- c(source_errors, date_errors)

  if (length(all_errors) > 0) {
    return(list(
      success       = FALSE,
      records_count = 0,
      preview       = NULL,
      message       = paste("Validation errors:", paste(all_errors, collapse = "; "))
    ))
  }

  pull_result <- pull_records(
    token      = source_token,
    redcap_url = source_url,
    date_from  = date_from,
    date_to    = date_to,
    full_sync  = full_sync,
    fields     = fields
  )

  if (!pull_result$success) {
    return(list(
      success       = FALSE,
      records_count = 0,
      preview       = NULL,
      message       = pull_result$message
    ))
  }

  # Return first 10 rows as preview sample
  preview_data <- head(pull_result$data, 10)

  list(
    success       = TRUE,
    records_count = pull_result$records_count,
    preview       = preview_data,
    columns       = names(pull_result$data),
    message       = paste("Preview: found", pull_result$records_count,
                           "records. Showing first", nrow(preview_data), ".")
  )
}

# ── Project metadata ──────────────────────────────────────────────────────────

get_project_info <- function(token, redcap_url) {
  setup_logger()
  errors <- validate_inputs(token, redcap_url)
  if (length(errors) > 0) {
    return(list(success = FALSE, message = paste(errors, collapse = "; "), info = NULL))
  }

  result <- tryCatch({
    info <- redcap_project_info_read(redcap_uri = redcap_url, token = token, verbose = FALSE)
    if (!info$success) {
      return(list(success = FALSE, message = paste("API error:", info$raw_text), info = NULL))
    }
    list(success = TRUE, message = "Project info retrieved", info = info$data)
  }, error = function(e) {
    list(success = FALSE, message = conditionMessage(e), info = NULL)
  })

  result
}