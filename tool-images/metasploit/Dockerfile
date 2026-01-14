# Metasploit Framework - Penetration testing framework
FROM kalilinux/kali-rolling:latest

LABEL maintainer="kwebbie - milbert.ai"
LABEL description="Metasploit Framework penetration testing platform"
LABEL tool="metasploit"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    metasploit-framework \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -s /bin/bash tooluser

# Initialize the database
RUN msfdb init || true

ENTRYPOINT ["msfconsole"]
