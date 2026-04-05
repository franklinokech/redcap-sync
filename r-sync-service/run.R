#!/usr/bin/env Rscript
# run.R — Start the REDCap sync plumber service
#
# Usage:
#   Rscript run.R               # default port 8000
#   PORT=9000 Rscript run.R     # custom port via env var
#   Rscript run.R --port 9000   # custom port via arg
if (file.exists("renv/activate.R")) source("renv/activate.R")

library(here)
library(plumber)




# Parse args
args <- commandArgs(trailingOnly = TRUE)
port_idx <- which(args == "--port")
port <- if (length(port_idx) > 0 && length(args) >= port_idx + 1) {
  as.integer(args[port_idx + 1])
} else {
  as.integer(Sys.getenv("PORT", unset = "8000"))
}

host <- Sys.getenv("HOST", unset = "0.0.0.0")

cat(sprintf("\n  REDCap Sync Service\n"))
cat(sprintf("  Starting on http://%s:%d\n", host, port))
cat(sprintf("  Swagger UI: http://localhost:%d/__docs__/\n\n", port))

pr <- plumb(here::here("plumber.R"))

pr$run(
  host   = host,
  port   = port,
  docs   = TRUE,        # enable Swagger UI at /__docs__/
  debug  = Sys.getenv("DEBUG", "false") == "true"
)