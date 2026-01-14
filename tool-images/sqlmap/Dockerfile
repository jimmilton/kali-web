# SQLMap - SQL Injection exploitation tool
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="SQLMap SQL injection tool"
LABEL tool="sqlmap"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    sqlmap \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -s /bin/bash tooluser

ENTRYPOINT ["sqlmap"]
