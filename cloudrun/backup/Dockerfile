FROM google/cloud-sdk:slim

# Install dependencies: pg_dump (postgresql-client) and bash
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    ca-certificates \
    curl \
    unzip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# Copy entrypoint
COPY entrypoint.sh /work/entrypoint.sh
RUN chmod +x /work/entrypoint.sh

ENV PATH="/work:$PATH"

ENTRYPOINT ["/work/entrypoint.sh"]
