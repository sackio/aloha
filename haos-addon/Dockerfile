# Aloha Home Assistant OS add-on image.
#
# Built from the REPO ROOT (so it can copy the aloha package + build the UI):
#   docker build -f haos-addon/Dockerfile --build-arg BUILD_FROM=<base> -t <img> .
# CI (build-addon.yml) builds+pushes ghcr.io/sackio/aloha-addon:{arch}.
#
# Unlike the standalone image this does NOT bundle Home Assistant — on HAOS the
# Supervisor provides Core (http://supervisor/core); this image is just the agent.

# BUILD_FROM (the HA base per arch) is used in stage 2's FROM, so it must be
# declared before any FROM.
ARG BUILD_FROM

# Stage 1: build the React UI (vite writes to ../aloha/static → /aloha/static)
FROM node:20-slim AS ui-builder
WORKDIR /ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm install
COPY ui/ .
RUN npm run build && cp -r /aloha/static /ui/dist

# Stage 2: the add-on (HA python base = Alpine + Python 3.12 + bashio)
FROM ${BUILD_FROM}
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# cloudflared for the free "Cloudflare tunnel" public-URL option (arch-matched)
RUN set -eux; \
    apk add --no-cache curl ca-certificates 2>/dev/null || true; \
    case "$(uname -m)" in x86_64) A=amd64;; aarch64) A=arm64;; armv7l|armhf|arm) A=arm;; *) A=amd64;; esac; \
    curl -fsSL -o /usr/local/bin/cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${A}"; \
    chmod +x /usr/local/bin/cloudflared

COPY aloha/ /app/aloha/
COPY --from=ui-builder /ui/dist /app/aloha/static/
ENV PYTHONPATH=/app

COPY haos-addon/run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
