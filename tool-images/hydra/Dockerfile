# Hydra - Network logon cracker
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Hydra network logon cracker"
LABEL tool="hydra"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    hydra \
    seclists \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -s /bin/bash tooluser

ENTRYPOINT ["hydra"]
