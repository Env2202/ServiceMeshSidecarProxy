FROM swe-arena-base

RUN apt-get update && apt-get install -y \
    openssl \
    python3-pip \
    python3-virtualenv \
    python3-venv \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

ENV COMMIT_HASH=fe4f7f4213515a9b942d96b1c10c1ec9e8be1b16
ENV REPO_URL=https://github.com/Env2202/ServiceMeshSidecarProxy.git
ENV REPO_NAME=ServiceMeshSidecarProxy

WORKDIR /testbed/${REPO_NAME}

RUN git init && \
    git remote add origin ${REPO_URL} && \
    git fetch --depth 1 origin ${COMMIT_HASH} && \
    git checkout FETCH_HEAD && \
    git remote remove origin

RUN pip3 install \
    "aiohttp>=3.9" \
    "httpx>=0.26" \
    "fastapi>=0.109" \
    "uvicorn[standard]>=0.27" \
    "pydantic>=2.5" \
    "pydantic-settings>=2.1" \
    "pyyaml>=6.0" \
    "click>=8.1" \
    "tenacity>=8.2" \
    "grpcio>=1.59" \
    "grpcio-tools>=1.59" \
    "protobuf>=4.24" \
    "xds" \
    "prometheus-client>=0.19" \
    "structlog>=24.1" \
    "opentelemetry-api>=1.20" \
    "opentelemetry-sdk>=1.20" \
    "opentelemetry-exporter-otlp-proto-grpc>=1.20" \
    "opentelemetry-propagator-b3>=1.20" \
    "cryptography>=41.0" \
    "pytest>=7.4" \
    "pytest-asyncio>=0.23" \
    "pytest-cov>=4.1" \
    "respx>=0.21" \
    "aioresponses>=0.7" \
    "ruff>=0.2" \
    "mypy>=1.8" \
    --break-system-packages
