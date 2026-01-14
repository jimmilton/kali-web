# WPScan - WordPress security scanner
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="WPScan WordPress security scanner"
LABEL tool="wpscan"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    wpscan \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -s /bin/bash tooluser

ENTRYPOINT ["wpscan"]
