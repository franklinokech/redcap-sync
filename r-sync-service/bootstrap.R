#!/usr/bin/env Rscript
# bootstrap.R -- One-time setup of the R environment for the REDCap Sync Service.
#
# Usage:
#   Rscript bootstrap.R
#
# Run this script from the project root directory (the directory containing
# renv.lock).  It must be executed once before starting the service with
# Rscript run.R.
#
# Exit codes:
#   0  -- all packages verified successfully
#   1  -- renv restore failed or one or more packages are missing after restore

# ---------------------------------------------------------------------------
# 0. Helpers
# ---------------------------------------------------------------------------

#' Write a timestamped, prefixed message to stdout.
log_msg <- function(...) {
  cat(sprintf("[bootstrap] %s\n", paste0(...)))
}

#' Abort with a message and exit code 1.
abort <- function(...) {
  cat(sprintf("[bootstrap] ERROR: %s\n", paste0(...)), file = stderr())
  quit(save = "no", status = 1L)
}


# ---------------------------------------------------------------------------
# 1. Working directory guard
#    renv::restore() looks for renv.lock in getwd().  Fail early with a clear
#    message rather than letting renv complain about a missing lock file.
# ---------------------------------------------------------------------------
cat("=== REDCap Sync Service -- Bootstrap ===\n\n")

if (!file.exists("renv.lock")) {
  abort(
    "'renv.lock' not found in the current directory (", getwd(), "). ",
    "Run this script from the project root."
  )
}


# ---------------------------------------------------------------------------
# 2. Install renv itself if it is not available
# ---------------------------------------------------------------------------
if (!requireNamespace("renv", quietly = TRUE)) {
  log_msg("renv not found -- installing from CRAN...")
  install.packages("renv", repos = "https://cloud.r-project.org", quiet = TRUE)

  if (!requireNamespace("renv", quietly = TRUE)) {
    abort("Failed to install renv. Check your internet connection and CRAN mirror.")
  }
  log_msg("renv installed successfully.")
}


# ---------------------------------------------------------------------------
# 3. Activate renv (sets up the project library path)
# ---------------------------------------------------------------------------
renv_activate <- file.path("renv", "activate.R")
if (file.exists(renv_activate)) {
  log_msg("Activating renv project library...")
  source(renv_activate)
} else {
  log_msg("renv/activate.R not found -- skipping activation (will use renv::restore directly)")
}


# ---------------------------------------------------------------------------
# 4. Restore packages from renv.lock
# ---------------------------------------------------------------------------
log_msg("Restoring packages from renv.lock (this may take a few minutes on first run)...")

restore_ok <- tryCatch({
  renv::restore(prompt = FALSE)
  TRUE
}, error = function(e) {
  cat(sprintf("[bootstrap] ERROR: renv::restore() failed:\n  %s\n",
              conditionMessage(e)), file = stderr())
  FALSE
})

if (!restore_ok) {
  abort("Package restore failed. See error above.")
}

log_msg("Package restore complete.")


# ---------------------------------------------------------------------------
# 5. Verify that all required packages can be loaded
#    Check against the renv project library explicitly so the result reflects
#    what the running service will see, not the system library.
# ---------------------------------------------------------------------------
cat("\n")
log_msg("Verifying required packages...")

# Packages that must be present for the service to operate.
required_packages <- c(
  "REDCapR",   # REDCap API client
  "plumber",   # REST API framework
  "dplyr",     # data manipulation
  "lubridate", # date/time parsing
  "jsonlite",  # JSON serialisation
  "logger",    # structured logging
  "here",      # project-relative paths
  "glue"       # string interpolation used in sync_logic.R
)

missing_packages <- character(0)

for (pkg in required_packages) {
  # find.package() searches the currently active library paths, which include
  # the renv project library after activation above.
  found <- tryCatch({
    find.package(pkg)
    TRUE
  }, error = function(e) FALSE)

  status <- if (found) "[OK]     " else "[MISSING]"
  cat(sprintf("  %-15s %s\n", pkg, status))

  if (!found) {
    missing_packages <- c(missing_packages, pkg)
  }
}


# ---------------------------------------------------------------------------
# 6. Final report
# ---------------------------------------------------------------------------
cat("\n")

if (length(missing_packages) > 0L) {
  cat(sprintf(
    "[bootstrap] ERROR: The following package(s) are missing after restore:\n  %s\n\n",
    paste(missing_packages, collapse = ", ")
  ), file = stderr())
  cat("[bootstrap] Try running:  renv::install() or check renv.lock for these packages.\n\n",
      file = stderr())
  quit(save = "no", status = 1L)
}

cat("[bootstrap] All packages verified.\n\n")
cat("Bootstrap complete. Start the service with:\n")
cat("  Rscript run.R\n\n")

quit(save = "no", status = 0L)
