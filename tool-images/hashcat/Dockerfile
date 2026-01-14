# Hashcat - Advanced password recovery
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Hashcat password recovery utility"
LABEL tool="hashcat"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    hashcat \
    hashcat-utils \
    wordlists \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy common wordlists
RUN mkdir -p /app/wordlists && \
    cp /usr/share/wordlists/rockyou.txt.gz /app/wordlists/ 2>/dev/null || true && \
    gunzip /app/wordlists/rockyou.txt.gz 2>/dev/null || true

RUN useradd -m -s /bin/bash tooluser

ENTRYPOINT ["hashcat"]
