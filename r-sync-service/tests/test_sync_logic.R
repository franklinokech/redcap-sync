# tests/test_sync_logic.R
# Unit tests for sync_logic.R (no real REDCap connection needed)
# Run: Rscript tests/test_sync_logic.R

source("sync_logic.R")

passed <- 0
failed <- 0

assert <- function(desc, expr) {
  result <- tryCatch(expr, error = function(e) FALSE)
  if (isTRUE(result)) {
    cat(sprintf("  PASS  %s\n", desc))
    passed <<- passed + 1
  } else {
    cat(sprintf("  FAIL  %s\n", desc))
    failed <<- failed + 1
  }
}

cat("\n=== validate_inputs ===\n")
assert("empty token returns error",
  length(validate_inputs("", "https://redcap.example.com/api/")) > 0)
assert("token too short returns error",
  length(validate_inputs("shorttoken", "https://redcap.example.com/api/")) > 0)
assert("32-char token passes",
  length(validate_inputs(strrep("a", 32), "https://redcap.example.com/api/")) == 0)
assert("missing URL returns error",
  length(validate_inputs(strrep("a", 32), "")) > 0)
assert("URL without scheme returns error",
  length(validate_inputs(strrep("a", 32), "redcap.example.com/api/")) > 0)
assert("valid inputs return no errors",
  length(validate_inputs(strrep("a", 32), "https://redcap.example.com/api/")) == 0)

cat("\n=== validate_dates ===\n")
assert("null dates are valid",
  length(validate_dates(NULL, NULL)) == 0)
assert("valid date range passes",
  length(validate_dates("2024-01-01", "2024-06-30")) == 0)
assert("date_from after date_to fails",
  length(validate_dates("2024-12-01", "2024-01-01")) > 0)
assert("invalid date format fails",
  length(validate_dates("01/01/2024", NULL)) > 0)
assert("same date is valid",
  length(validate_dates("2024-06-15", "2024-06-15")) == 0)

cat(sprintf("\n=== Results: %d passed, %d failed ===\n\n", passed, failed))
if (failed > 0) quit(status = 1)