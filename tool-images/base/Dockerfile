# Base image for Kali tools
# Copyright 2025 milbert.ai
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Base image for security tools"

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install common dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    dnsutils \
    net-tools \
    iputils-ping \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Create non-root user for running tools
RUN useradd -m -s /bin/bash tooluser

# Default command
CMD ["/bin/bash"]
