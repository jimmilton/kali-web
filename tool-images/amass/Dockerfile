# Amass - Network mapping and external asset discovery
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="OWASP Amass - network mapping and external asset discovery"
LABEL tool="amass"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    amass \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -s /bin/bash tooluser

ENTRYPOINT ["amass"]
