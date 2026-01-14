FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Nikto - Web server scanner"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    nikto \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENTRYPOINT ["nikto"]
