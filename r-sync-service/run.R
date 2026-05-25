#!/usr/bin/env Rscript
# run.R -- Start the REDCap Sync plumber service
#
# Usage:
#   Rscript run.R                 # default port 8000, host 0.0.0.0
#   PORT=9000 Rscript run.R       # custom port via environment variable
#   Rscript run.R --port 9000     # custom port via command-line argument
#   DEBUG=true Rscript run.R      # enable plumber debug mode
#
# Assumptions:
#   - Working directory is the project root (i.e. where renv/ lives).
#   - renv/activate.R is present when running inside the renv environment.
#   - plumber.R and sync_logic.R are in the same directory as this script.

# ---------------------------------------------------------------------------
# 1. renv bootstrap
#    Must be relative to the project root -- here::here() is not yet loaded.
# ---------------------------------------------------------------------------
renv_activate <- file.path("renv", "activate.R")
if (file.exists(renv_activate)) {
  source(renv_activate)
} else {
  message("[run.R] renv/activate.R not found -- using system library")
}


# ---------------------------------------------------------------------------
# 2. Libraries
# ---------------------------------------------------------------------------
library(here)
library(plumber)


# ---------------------------------------------------------------------------
# 3. Parse --port argument
# ---------------------------------------------------------------------------
args     <- commandArgs(trailingOnly = TRUE)
port_idx <- which(args == "--port")

raw_port <- if (length(port_idx) > 0 && length(args) >= port_idx + 1L) {
  args[[port_idx + 1L]]
} else {
  Sys.getenv("PORT", unset = "8000")
}

port <- suppressWarnings(as.integer(raw_port))
if (is.na(port) || port < 1L || port > 65535L) {
  stop(sprintf(
    "[run.R] Invalid port value '%s'. Supply a number between 1 and 65535.",
    raw_port
  ))
}


# ---------------------------------------------------------------------------
# 4. Host
# ---------------------------------------------------------------------------
host <- Sys.getenv("HOST", unset = "0.0.0.0")


# ---------------------------------------------------------------------------
# 5. Debug flag
#    Normalise to lowercase so "true", "TRUE", "True", "1" all work.
# ---------------------------------------------------------------------------
debug_env <- tolower(trimws(Sys.getenv("DEBUG", unset = "false")))
debug     <- debug_env %in% c("true", "1")


# ---------------------------------------------------------------------------
# 6. Banner
# ---------------------------------------------------------------------------
cat(sprintf(
  "\n  REDCap Sync Service\n  Listening on : http://%s:%d\n  Swagger UI   : http://localhost:%d/__docs__/\n  Debug mode   : %s\n\n",
  host, port, port, if (debug) "on" else "off"
))


# ---------------------------------------------------------------------------
# 7. Build and run the plumber router
# ---------------------------------------------------------------------------
pr <- plumber::plumb(here::here("plumber.R"))

tryCatch(
  pr$run(
    host  = host,
    port  = port,
    # 'swagger' is the canonical parameter name in plumber >= 1.0.0.
    # The 'docs' alias still works but emits a deprecation warning.
    swagger = TRUE,
    debug = debug
  ),
  error = function(e) {
    stop(sprintf(
      "[run.R] Failed to start server on %s:%d -- %s",
      host, port, conditionMessage(e)
    ))
  }
)
