FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    nodejs npm \
    curl wget git \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir httpx requests beautifulsoup4

WORKDIR /workspace
RUN chmod 777 /workspace

# Non-root user for safety
RUN useradd -m -s /bin/bash agent
USER agent

CMD ["sleep", "infinity"]
