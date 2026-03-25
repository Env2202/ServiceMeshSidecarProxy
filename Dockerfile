# Dockerfile (placeholder per plan)
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source
COPY sidecar/ sidecar/

# Default command
CMD ["python", "-m", "sidecar", "--config", "/config/sidecar-config.yaml"]
