# Nuclei - Fast vulnerability scanner
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Nuclei vulnerability scanner"
LABEL tool="nuclei"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    nuclei \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Update nuclei templates
RUN nuclei -ut || true

WORKDIR /app

RUN useradd -m -s /bin/bash tooluser

ENTRYPOINT ["nuclei"]
