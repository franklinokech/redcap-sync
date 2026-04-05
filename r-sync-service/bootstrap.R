#!/usr/bin/env Rscript
# bootstrap.R — Run once to set up the R environment
# Usage: Rscript bootstrap.R

cat("=== REDCap Sync Service — Bootstrap ===\n\n")

# 1. Install renv if missing
if (!requireNamespace("renv", quietly = TRUE)) {
  cat("Installing renv...\n")
  install.packages("renv", repos = "https://cloud.r-project.org")
}

# 2. Restore packages from renv.lock
cat("Restoring packages from renv.lock...\n")
renv::restore(prompt = FALSE)

# 3. Verify key packages load
cat("\nVerifying packages...\n")
packages <- c("REDCapR", "plumber", "dplyr", "lubridate", "jsonlite", "logger")
for (pkg in packages) {
  ok <- requireNamespace(pkg, quietly = TRUE)
  cat(sprintf("  %-15s %s\n", pkg, if (ok) "[OK]" else "[MISSING]"))
}

cat("\nBootstrap complete. Start the service with:\n")
cat("  Rscript run.R\n\n")