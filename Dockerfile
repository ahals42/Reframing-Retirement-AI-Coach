# ==============================================================================
# Multi-stage Dockerfile for Reframing Retirement Coach API
# Security Features:
# - Multi-stage build to minimize image size
# - Runs as non-root user
# - Only copies necessary files (no secrets)
# - Minimal dependencies
# - Health check included
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in a virtual environment
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for running the application
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (excluding files in .dockerignore)
# This excludes .env, .git, __pycache__, etc.
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser coach/ ./coach/
COPY --chown=appuser:appuser rag/ ./rag/
COPY --chown=appuser:appuser frontend/ ./frontend/

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
