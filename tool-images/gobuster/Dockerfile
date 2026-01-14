# Gobuster - Directory/DNS/VHost busting tool
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Gobuster directory and DNS scanner"
LABEL tool="gobuster"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    gobuster \
    seclists \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -s /bin/bash tooluser

ENTRYPOINT ["gobuster"]
