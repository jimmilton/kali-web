FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="John the Ripper - Password cracker"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    john \
    wordlists \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENTRYPOINT ["john"]
