FROM rocker/r-ver:4.5.1

WORKDIR /app

# ─────────────────────────────
# System dependencies
# ─────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    curl \
    libsodium-dev \
    libxt-dev \
    pkg-config \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────
# renv install
# ─────────────────────────────
RUN R -e "install.packages('remotes', repos='https://cloud.r-project.org'); \
          remotes::install_version('renv', version='1.1.4', repos='https://cloud.r-project.org')"

# ─────────────────────────────
# Set env
# ─────────────────────────────
ENV RENV_CONFIG_REPOS_OVERRIDE=https://cloud.r-project.org

# ─────────────────────────────
# Copy FULL renv context FIRST (IMPORTANT FIX)
# ─────────────────────────────
COPY renv.lock ./
COPY renv/ renv/
COPY .Rprofile ./

# ─────────────────────────────
# Restore dependencies
# ─────────────────────────────
RUN R -e "renv::restore(prompt = FALSE)"

# ─────────────────────────────
# Copy application code
# ─────────────────────────────
COPY . .

# ─────────────────────────────
# Fix entrypoint permissions (if used)
# ─────────────────────────────
RUN chmod +x /app/entrypoint.sh || true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["Rscript", "run.R"]
