FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Masscan - Fast port scanner"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    masscan \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENTRYPOINT ["masscan"]
