# Sclerotium OS v5.2 — Production Docker Image
# Multi-stage build for minimal production image

FROM python:3.12-slim AS builder

WORKDIR /app
RUN pip install --no-cache-dir uv

# Install dependencies
COPY pyproject.toml .
RUN uv pip install --system \
    aiohttp \
    chromadb \
    sqlite3 \
    pydantic \
    psutil \
    watchdog \
    Pillow \
    numpy \
    && rm -rf /root/.cache

FROM python:3.12-slim AS runtime

LABEL org.sclerotium.os.version="5.2.0"
LABEL org.sclerotium.os.description="Super Electronic Lifeform"

WORKDIR /app

# Copy deps from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy application
COPY . .

# Create data directories
RUN mkdir -p /app/data/sessions /app/data/brain_chroma /app/data/tokens /app/logs

# Non-root user
RUN useradd -m -s /bin/bash sclerotium && chown -R sclerotium:sclerotium /app
USER sclerotium

ENV SCLEROTIUM_API_BASE=https://api.deepseek.com/v1
ENV PYTHONUNBUFFERED=1

EXPOSE 18789

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:18789/health')" || exit 1

CMD ["python", "-u", "sclerotium.py"]
