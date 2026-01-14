# Nmap - Network exploration and security auditing
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Nmap network scanner"
LABEL tool="nmap"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    nmap \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -s /bin/bash tooluser

ENTRYPOINT ["nmap"]
