# kwebbie - Single Docker Image
# Copyright 2025 milbert.ai

FROM python:3.11-slim

LABEL maintainer="kwebbie - milbert.ai"

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including weasyprint requirements and nmap
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools (for any wheels that need compiling)
    build-essential \
    gcc \
    libffi-dev \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    libcairo2 \
    libgirepository1.0-dev \
    gir1.2-pango-1.0 \
    shared-mime-info \
    fonts-liberation \
    # Security tools
    nmap \
    curl \
    # lxml dependencies
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create directories
RUN mkdir -p /app /data
WORKDIR /app

# Copy requirements and install Python dependencies
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend /app/backend

# Environment variables
ENV DATA_DIR=/data
ENV DATABASE_URL=sqlite:////data/kwebbie.db
ENV DEBUG=true
ENV PORT=8080

EXPOSE 8080
VOLUME ["/data"]

WORKDIR /app/backend

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:application", "--host", "0.0.0.0", "--port", "8080"]
