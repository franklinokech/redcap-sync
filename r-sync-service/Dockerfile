FROM rocker/r-ver:4.5.1

WORKDIR /app

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

RUN R -e "install.packages('remotes', repos='https://cloud.r-project.org'); remotes::install_version('renv', version='1.1.4', repos='https://cloud.r-project.org')"

COPY renv.lock .

COPY . .

RUN R -e "renv::restore(prompt=FALSE)"

EXPOSE 8000

CMD ["Rscript", "run.R"]