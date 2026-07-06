ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python dependencies
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Bundle cloudflared for the free "Cloudflare tunnel" public-URL option.
RUN set -eux; \
    if command -v apk >/dev/null; then apk add --no-cache curl ca-certificates; \
    elif command -v apt-get >/dev/null; then apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*; fi; \
    case "$(uname -m)" in x86_64) A=amd64;; aarch64) A=arm64;; armv7l|armhf|arm) A=arm;; *) A=amd64;; esac; \
    curl -fsSL -o /usr/local/bin/cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${A}"; \
    chmod +x /usr/local/bin/cloudflared

# Copy the Aloha Python package
COPY aloha/ /app/aloha/

# Copy built React frontend static files
COPY frontend/dist/ /app/aloha/frontend/dist/

# Copy the add-on run script
COPY haos-addon/run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
