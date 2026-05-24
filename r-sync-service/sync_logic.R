# r-sync-service/sync_logic.R
# ---------------------------------------------------------------------------
# Helpers + business logic for the R sync service.
# REDCapR::redcap_write() uses overwrite_with_blanks (logical), NOT
# overwrite_behaviour (character).  All verbose= args are explicit FALSE
# in production paths; TRUE in debug paths.
# ---------------------------------------------------------------------------

library(httr)
library(jsonlite)
library(xml2)
library(REDCapR)

# ---------------------------------------------------------------------------
# Null-coalescing operator
# ---------------------------------------------------------------------------
`%||%` <- function(a, b) {
  if (!is.null(a) && length(a) > 0 && !is.na(a[[1]])) a else b
}

# ---------------------------------------------------------------------------
# debug_log: timestamped stderr sink so every stage is traceable in Celery
# ---------------------------------------------------------------------------
debug_log <- function(..., level = "DEBUG") {
  ts  <- format(Sys.time(), "%Y-%m-%d %H:%M:%S UTC", tz = "UTC")
  msg <- paste0("[", ts, "] [", level, "] ", paste(..., sep = " "))
  message(msg)   # goes to stderr → captured by Python subprocess / Celery
  invisible(msg)
}

# ---------------------------------------------------------------------------
# extract_xml_error: pull <error> text out of a REDCap XML fault body
# ---------------------------------------------------------------------------
extract_xml_error <- function(text) {
  tryCatch({
    doc  <- xml2::read_xml(text)
    msgs <- xml2::xml_text(xml2::xml_find_all(doc, "//error"))
    if (length(msgs) > 0L) paste(msgs, collapse = "; ") else text
  }, error = function(e) text)
}

# ---------------------------------------------------------------------------
# safe_post: thin wrapper around httr::POST with full debug output
# ---------------------------------------------------------------------------
safe_post <- function(url, body, label = "safe_post") {
  debug_log(sprintf("[%s] POST → %s  body_keys=%s",
                    label, url, paste(names(body), collapse = ",")))
  tryCatch({
    resp <- httr::POST(url, body = body, encode = "form")
    code <- httr::status_code(resp)
    raw  <- httr::content(resp, as = "text", encoding = "UTF-8")

    debug_log(sprintf("[%s] HTTP %d  body_preview=%s",
                      label, code,
                      substr(gsub("\n", " ", raw), 1L, 200L)))

    list(ok = (code >= 200L && code < 300L), status = code, body = raw)
  }, error = function(e) {
    debug_log(sprintf("[%s] connection error: %s", label, conditionMessage(e)),
              level = "ERROR")
    list(ok = FALSE, status = NA_integer_, body = conditionMessage(e))
  })
}

# ---------------------------------------------------------------------------
# build_datetime_range: convert YYYY-MM-DD strings → UTC POSIXct or NULL
# ---------------------------------------------------------------------------
build_datetime_range <- function(date_from = NULL, date_to = NULL) {

  to_posixct <- function(x, end_of_day = FALSE) {
    if (is.null(x) || !nzchar(trimws(x))) return(NULL)
    x <- trimws(x)
    if (grepl("^\\d{4}-\\d{2}-\\d{2}$", x)) {
      x <- paste(x, if (end_of_day) "23:59:59" else "00:00:00")
    }
    dt <- tryCatch(
      as.POSIXct(x, format = "%Y-%m-%d %H:%M:%S", tz = "UTC"),
      error = function(e) NULL
    )
    if (is.null(dt) || is.na(dt)) {
      warning(sprintf("build_datetime_range: cannot parse '%s' — ignoring", x))
      return(NULL)
    }
    dt
  }

  range <- list(
    begin = to_posixct(date_from, end_of_day = FALSE),
    end   = to_posixct(date_to,   end_of_day = TRUE)
  )

  debug_log(sprintf("build_datetime_range: begin=%s  end=%s",
                    range$begin %||% "NULL", range$end %||% "NULL"))
  range
}

# ---------------------------------------------------------------------------
# validate_token: check connectivity + return project metadata
# ---------------------------------------------------------------------------
validate_token <- function(token, redcap_url) {
  debug_log(sprintf("validate_token: url=%s  token_tail=%s",
                    redcap_url, substr(token, nchar(token) - 3L, nchar(token))))

  v <- safe_post(redcap_url,
                 list(token = token, content = "version", format = "json"),
                 label = "validate_token/version")

  if (!v$ok) {
    msg <- if (!is.na(v$status)) {
      sprintf("REDCap version check failed (HTTP %d): %s", v$status, v$body)
    } else {
      sprintf("REDCap connection error: %s", v$body)
    }
    debug_log(msg, level = "ERROR")
    return(list(success = FALSE, message = msg))
  }

  redcap_version <- trimws(v$body) %||% "unknown"
  debug_log(sprintf("validate_token: REDCap version=%s", redcap_version))

  p <- safe_post(redcap_url,
                 list(token = token, content = "project", format = "json"),
                 label = "validate_token/project")

  if (!p$ok) {
    readable <- extract_xml_error(p$body)
    msg <- sprintf("REDCap project info failed (HTTP %d): %s",
                   p$status %||% 0L, readable)
    debug_log(msg, level = "ERROR")
    return(list(success = FALSE, message = msg))
  }

  project <- tryCatch(
    jsonlite::fromJSON(p$body, simplifyVector = TRUE),
    error = function(e) {
      debug_log(sprintf("validate_token: JSON parse error: %s", conditionMessage(e)),
                level = "WARN")
      NULL
    }
  )

  if (is.null(project)) {
    return(list(success = TRUE, project_id = NULL,
                project_title = "Unknown", redcap_version = redcap_version))
  }

  if (is.data.frame(project)) project <- as.list(project[1L, , drop = FALSE])

  project_id    <- suppressWarnings(as.integer(project[["project_id"]]    %||% NA_integer_))
  project_title <- as.character(              project[["project_title"]] %||% "Unknown")

  debug_log(sprintf("validate_token: project_id=%s  title=%s",
                    project_id %||% "NULL", project_title))

  list(
    success        = TRUE,
    project_id     = if (is.na(project_id)) NULL else project_id,
    project_title  = project_title,
    redcap_version = redcap_version
  )
}

# ---------------------------------------------------------------------------
# inspect_project: deep diagnostic — exports metadata, user rights, arm list
# Call this before sync_records when you hit a write 400 to understand
# exactly what the destination project allows.
# ---------------------------------------------------------------------------
inspect_project <- function(token, redcap_url) {

  debug_log(sprintf("inspect_project: url=%s", redcap_url))

  results <- list()

  # ── 1. Arms (longitudinal projects require redcap_event_name) ────────────
  arms_resp <- safe_post(redcap_url,
                         list(token = token, content = "arm",
                              format = "json", returnFormat = "json"),
                         label = "inspect_project/arms")
  results$arms <- tryCatch(
    jsonlite::fromJSON(arms_resp$body, simplifyVector = TRUE),
    error = function(e) list(error = conditionMessage(e))
  )
  debug_log(sprintf("inspect_project: arms=%s",
                    jsonlite::toJSON(results$arms, auto_unbox = TRUE)))

  # ── 2. Events ─────────────────────────────────────────────────────────────
  events_resp <- safe_post(redcap_url,
                           list(token = token, content = "event",
                                format = "json", returnFormat = "json"),
                           label = "inspect_project/events")
  results$events <- tryCatch(
    jsonlite::fromJSON(events_resp$body, simplifyVector = TRUE),
    error = function(e) list(error = conditionMessage(e))
  )
  n_events <- if (is.data.frame(results$events)) nrow(results$events) else 0L
  debug_log(sprintf("inspect_project: event_count=%d", n_events))

  # ── 3. Field metadata ─────────────────────────────────────────────────────
  meta_resp <- safe_post(redcap_url,
                         list(token = token, content = "metadata",
                              format = "json", returnFormat = "json"),
                         label = "inspect_project/metadata")
  meta <- tryCatch(
    jsonlite::fromJSON(meta_resp$body, simplifyVector = TRUE),
    error = function(e) NULL
  )
  results$field_count   <- if (is.data.frame(meta)) nrow(meta) else 0L
  results$record_id_field <- if (is.data.frame(meta) && nrow(meta) > 0L)
    meta$field_name[[1L]] else NA_character_
  debug_log(sprintf("inspect_project: field_count=%d  record_id_field=%s",
                    results$field_count, results$record_id_field %||% "UNKNOWN"))

  # ── 4. User rights for this token ─────────────────────────────────────────
  user_resp <- safe_post(redcap_url,
                         list(token = token, content = "user",
                              format = "json", returnFormat = "json"),
                         label = "inspect_project/users")
  users <- tryCatch(
    jsonlite::fromJSON(user_resp$body, simplifyVector = TRUE),
    error = function(e) NULL
  )

  if (is.data.frame(users) && nrow(users) > 0L) {
    # The API user is whichever row owns this token — we can't directly match
    # token→user via the API, so log all users' import rights
    rights_summary <- tryCatch({
      users[, intersect(names(users),
                        c("username", "data_access_group", "data_import",
                          "data_export_tool", "api_import", "api_export")),
            drop = FALSE]
    }, error = function(e) users)

    debug_log(sprintf("inspect_project: user_rights=%s",
                      jsonlite::toJSON(rights_summary, auto_unbox = TRUE)))
    results$user_rights <- rights_summary
  } else {
    debug_log("inspect_project: could not retrieve user rights (token may lack User Rights export privilege)",
              level = "WARN")
    results$user_rights <- NULL
  }

  # ── 5. Try reading 1 record to confirm read access ─────────────────────────
  read_test <- tryCatch({
    r <- REDCapR::redcap_read(
      redcap_uri = redcap_url,
      token      = token,
      records    = 1L,
      verbose    = TRUE    # ← verbose=TRUE intentionally for diagnostics
    )
    list(
      success      = isTRUE(r$success),
      record_count = nrow(r$data),
      fields       = names(r$data),
      outcome      = r$outcome_message
    )
  }, error = function(e) {
    list(success = FALSE, message = conditionMessage(e))
  })

  debug_log(sprintf("inspect_project: read_test success=%s  records=%s  outcome=%s",
                    read_test$success,
                    read_test$record_count %||% "N/A",
                    read_test$outcome      %||% read_test$message %||% ""))
  results$read_test <- read_test

  results
}

# ---------------------------------------------------------------------------
# preview_records: dry-run read — returns record count + field names
# ---------------------------------------------------------------------------
preview_records <- function(token, redcap_url,
                            date_from = NULL, date_to = NULL,
                            forms = NULL, fields = NULL) {

  debug_log(sprintf("preview_records: url=%s  forms=%s  fields=%s  date_from=%s  date_to=%s",
                    redcap_url,
                    paste(forms  %||% "NULL", collapse = ","),
                    paste(fields %||% "NULL", collapse = ","),
                    date_from %||% "NULL",
                    date_to   %||% "NULL"))

  tryCatch({
    dr <- build_datetime_range(date_from, date_to)

    result <- REDCapR::redcap_read(
      redcap_uri           = redcap_url,
      token                = token,
      forms                = forms,
      fields               = fields,
      datetime_range_begin = dr$begin,
      datetime_range_end   = dr$end,
      verbose              = TRUE   # ← always verbose in preview; it's diagnostic
    )

    debug_log(sprintf("preview_records: success=%s  records=%d  outcome=%s",
                      result$success,
                      nrow(result$data),
                      result$outcome_message %||% ""))

    if (!isTRUE(result$success)) {
      return(list(
        success = FALSE,
        message = result$outcome_message %||% "REDCap read failed"
      ))
    }

    list(
      success      = TRUE,
      record_count = nrow(result$data),
      fields       = names(result$data)
    )

  }, error = function(e) {
    debug_log(sprintf("preview_records: exception: %s", conditionMessage(e)),
              level = "ERROR")
    list(success = FALSE, message = conditionMessage(e))
  })
}

# ---------------------------------------------------------------------------
# sync_records: read from source, optionally prefix IDs, write to target
#
# KEY FACT: REDCapR::redcap_write() parameter is overwrite_with_blanks
#           (logical TRUE/FALSE).  There is NO overwrite_behaviour param
#           in this version.  Passing an unknown arg crashes R with
#           "unused argument (overwrite_behaviour = ...)".
# ---------------------------------------------------------------------------
sync_records <- function(token,
                         redcap_url,
                         target_token,
                         target_redcap_url,
                         forms                 = NULL,
                         fields                = NULL,
                         record_id_prefix      = NULL,
                         date_from             = NULL,
                         date_to               = NULL,
                         overwrite_with_blanks = FALSE) {
  tryCatch({

    # ── Log all incoming parameters (mask token tails only) ──────────────
    debug_log(sprintf(
      "sync_records: START  src_url=%s  src_token_tail=...%s  dst_url=%s  dst_token_tail=...%s",
      redcap_url,
      substr(token,        nchar(token)        - 3L, nchar(token)),
      target_redcap_url,
      substr(target_token, nchar(target_token) - 3L, nchar(target_token))
    ))
    debug_log(sprintf(
      "sync_records: params  forms=%s  fields=%s  prefix=%s  date_from=%s  date_to=%s  owb=%s",
      paste(forms  %||% "NULL", collapse = ","),
      paste(fields %||% "NULL", collapse = ","),
      record_id_prefix      %||% "NULL",
      date_from             %||% "NULL",
      date_to               %||% "NULL",
      overwrite_with_blanks %||% "FALSE"
    ))

    # ── Coerce overwrite_with_blanks to a plain logical scalar ───────────
    owb <- isTRUE(as.logical(overwrite_with_blanks))
    debug_log(sprintf("sync_records: overwrite_with_blanks coerced to %s", owb))

    # ── Step 1: inspect the destination before writing ───────────────────
    debug_log("sync_records: running inspect_project on DESTINATION")
    dst_info <- inspect_project(target_token, target_redcap_url)
    debug_log(sprintf(
      "sync_records: dst record_id_field=%s  field_count=%d  read_test=%s",
      dst_info$record_id_field %||% "UNKNOWN",
      dst_info$field_count     %||% 0L,
      dst_info$read_test$success %||% FALSE
    ))

    # ── Step 2: inspect the source ────────────────────────────────────────
    debug_log("sync_records: running inspect_project on SOURCE")
    src_info <- inspect_project(token, redcap_url)
    debug_log(sprintf(
      "sync_records: src record_id_field=%s  field_count=%d  read_test=%s",
      src_info$record_id_field %||% "UNKNOWN",
      src_info$field_count     %||% 0L,
      src_info$read_test$success %||% FALSE
    ))

    # ── Step 3: build optional date range ────────────────────────────────
    dr <- build_datetime_range(date_from, date_to)

    # ── Step 4: read from source ──────────────────────────────────────────
    debug_log("sync_records: reading from source (verbose=TRUE)")
    read_result <- REDCapR::redcap_read(
      redcap_uri           = redcap_url,
      token                = token,
      forms                = forms,
      fields               = fields,
      datetime_range_begin = dr$begin,
      datetime_range_end   = dr$end,
      col_types            = readr::cols(.default = readr::col_character()),
      na                   = character(0),   # nothing is NA — keep raw strings
      guess_type           = FALSE,          # no type inference at all
      verbose              = TRUE   # ← verbose for all reads while debugging
    )

    debug_log(sprintf(
      "sync_records: read complete  success=%s  records=%d  outcome=%s",
      read_result$success,
      nrow(read_result$data),
      read_result$outcome_message %||% ""
    ))

    if (!isTRUE(read_result$success)) {
      msg <- read_result$outcome_message %||% "Source read failed"
      debug_log(sprintf("sync_records: read FAILED: %s", msg), level = "ERROR")
      return(list(
        success         = FALSE,
        message         = msg,
        records_pulled  = 0L,
        records_pushed  = 0L,
        records_skipped = 0L
      ))
    }

    data           <- read_result$data
    records_pulled <- nrow(data)

    debug_log(sprintf(
      "sync_records: source data  rows=%d  cols=%d  names=%s",
      records_pulled,
      ncol(data),
      paste(names(data), collapse = ",")
    ))

    if (records_pulled == 0L) {
      debug_log("sync_records: no records to sync — returning early")
      return(list(
        success         = TRUE,
        records_pulled  = 0L,
        records_pushed  = 0L,
        records_skipped = 0L
      ))
    }

    # ── Step 5: verify source record_id field matches destination ─────────
    src_id_field <- src_info$record_id_field %||% "record_id"
    dst_id_field <- dst_info$record_id_field %||% "record_id"

    debug_log(sprintf(
      "sync_records: id field check  src=%s  dst=%s  match=%s",
      src_id_field, dst_id_field,
      src_id_field == dst_id_field
    ))

    if (!(src_id_field %in% names(data))) {
      msg <- sprintf(
        "Source data does not contain expected record_id field '%s'. Available: %s",
        src_id_field, paste(names(data), collapse = ", ")
      )
      debug_log(msg, level = "ERROR")
      return(list(success = FALSE, message = msg,
                  records_pulled = records_pulled, records_pushed = 0L,
                  records_skipped = 0L))
    }

    # ── Step 6: log sample of first record for field-value inspection ─────
    first_rec <- as.list(data[1L, , drop = FALSE])
    debug_log(sprintf("sync_records: first record sample = %s",
                      substr(jsonlite::toJSON(first_rec, auto_unbox = TRUE), 1L, 500L)))

    # ── Step 7: apply record_id prefix ───────────────────────────────────
    prefix <- trimws(record_id_prefix %||% "")
    if (nchar(prefix) > 0L && src_id_field %in% names(data)) {
      before <- data[[src_id_field]][1L]
      data[[src_id_field]] <- paste0(prefix, data[[src_id_field]])
      after  <- data[[src_id_field]][1L]
      debug_log(sprintf("sync_records: prefix applied  example %s → %s", before, after))
    }

    # ── Step 8: check destination field compatibility ─────────────────────
    dst_fields <- if (!is.null(dst_info$read_test$fields))
      dst_info$read_test$fields else character(0)

    if (length(dst_fields) > 0L) {
      src_cols         <- names(data)
      missing_in_dst   <- setdiff(src_cols, dst_fields)
      missing_in_src   <- setdiff(dst_fields, src_cols)

      debug_log(sprintf(
        "sync_records: field diff  src_cols=%d  dst_cols=%d  in_src_not_dst=%s  in_dst_not_src=%s",
        length(src_cols),
        length(dst_fields),
        if (length(missing_in_dst) == 0L) "none"
          else paste(head(missing_in_dst, 10L), collapse = ","),
        if (length(missing_in_src) == 0L) "none"
          else paste(head(missing_in_src, 10L), collapse = ",")
      ))

      # Drop columns that don't exist in destination — REDCap rejects unknowns
      cols_to_drop <- missing_in_dst
      if (length(cols_to_drop) > 0L) {
        debug_log(sprintf(
          "sync_records: dropping %d columns absent from destination: %s",
          length(cols_to_drop),
          paste(head(cols_to_drop, 20L), collapse = ",")
        ), level = "WARN")
        data <- data[, !(names(data) %in% cols_to_drop), drop = FALSE]
      }
    }

    # ── Step 9: write to target ───────────────────────────────────────────
    debug_log(sprintf(
      "sync_records: writing to destination  rows=%d  cols=%d  owb=%s  verbose=TRUE",
      nrow(data), ncol(data), owb
    ))

    write_result <- REDCapR::redcap_write(
      ds_to_write           = data,
      redcap_uri            = target_redcap_url,
      token                 = target_token,
      overwrite_with_blanks = owb,
      verbose               = TRUE   # ← verbose=TRUE to get the actual REDCap error
    )

    debug_log(sprintf(
      "sync_records: write complete  success=%s  affected=%s  outcome=%s",
      write_result$success,
      write_result$records_affected_count %||% "N/A",
      write_result$outcome_message        %||% ""
    ))

    if (!isTRUE(write_result$success)) {
      msg <- write_result$outcome_message %||% "Target write failed"
      debug_log(sprintf("sync_records: write FAILED: %s", msg), level = "ERROR")
      return(list(
        success         = FALSE,
        message         = msg,
        records_pulled  = records_pulled,
        records_pushed  = 0L,
        records_skipped = 0L
      ))
    }

    debug_log(sprintf(
      "sync_records: SUCCESS  pulled=%d  pushed=%d",
      records_pulled,
      write_result$records_affected_count %||% records_pulled
    ))

    list(
      success         = TRUE,
      records_pulled  = records_pulled,
      records_pushed  = write_result$records_affected_count %||% records_pulled,
      records_skipped = 0L
    )

  }, error = function(e) {
    debug_log(sprintf("sync_records: EXCEPTION: %s", conditionMessage(e)),
              level = "ERROR")
    list(
      success         = FALSE,
      message         = conditionMessage(e),
      records_pulled  = 0L,
      records_pushed  = 0L,
      records_skipped = 0L
    )
  })
}
