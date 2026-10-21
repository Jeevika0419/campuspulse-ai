# CampusPulse AI — Production Dockerfile
# =========================================
# Multi-stage build for optimized cloud deployment
# Compatible with AWS ECS, EC2, and ECR

FROM python:3.12-slim-trixie AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=production

# Create non-root user for security
RUN groupadd -r campuspulse && useradd -r -g campuspulse campuspulse

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Dependency Stage ----
FROM base AS dependencies

# Copy only requirements first (for Docker cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn==21.2.0

# ---- Final Production Stage ----
FROM dependencies AS final

# Copy application source code
COPY --chown=campuspulse:campuspulse . .

# Create upload directory with proper permissions
RUN mkdir -p /app/uploads && chown -R campuspulse:campuspulse /app/uploads

# Switch to non-root user
USER campuspulse

# Expose Flask port
EXPOSE 5000

# Health check for load balancer / ECS
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/test-db || exit 1

# Production WSGI server (Gunicorn with 4 workers)
CMD ["gunicorn", \
    "--workers", "4", \
    "--threads", "2", \
    "--bind", "0.0.0.0:5000", \
    "--timeout", "90", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--log-level", "info", \
    "app:app"]
