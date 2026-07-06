# Stage 1: Build the React frontend
FROM node:20-slim AS ui-builder
WORKDIR /ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm install
COPY ui/ .
RUN npm run build

# Stage 2: Final image — HA base with Aloha layered on top
# Entrypoint is inherited from the HA base image (s6-overlay)
FROM ghcr.io/home-assistant/home-assistant:stable

COPY requirements.txt /tmp/aloha-req.txt
RUN pip3 install --no-cache-dir -r /tmp/aloha-req.txt && rm /tmp/aloha-req.txt

# Bundle cloudflared so the box can offer a free public MCP URL out of the box
# (the "Cloudflare tunnel" option in aloha/public_url.py). Arch-matched binary.
RUN set -eux; \
    if command -v apk >/dev/null; then apk add --no-cache curl ca-certificates; \
    elif command -v apt-get >/dev/null; then apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*; fi; \
    case "$(uname -m)" in x86_64) A=amd64;; aarch64) A=arm64;; armv7l|armhf|arm) A=arm;; *) A=amd64;; esac; \
    curl -fsSL -o /usr/local/bin/cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${A}"; \
    chmod +x /usr/local/bin/cloudflared

COPY aloha/ /aloha/
ENV PYTHONPATH=/

COPY --from=ui-builder /ui/dist /aloha/static/

COPY rootfs/ /
RUN chmod +x /etc/s6-overlay/s6-rc.d/aloha/run /etc/cont-init.d/aloha-init.sh

EXPOSE 8123 7123
VOLUME ["/data"]
