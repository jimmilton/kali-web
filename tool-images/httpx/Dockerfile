FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="HTTPx - Fast HTTP probing tool"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    httpx-toolkit \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENTRYPOINT ["httpx-toolkit"]
