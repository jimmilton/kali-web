FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Subfinder - Subdomain discovery tool"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    subfinder \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENTRYPOINT ["subfinder"]
