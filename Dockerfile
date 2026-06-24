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

COPY aloha/ /aloha/
ENV PYTHONPATH=/

COPY --from=ui-builder /ui/dist /aloha/static/

COPY rootfs/ /
RUN chmod +x /etc/s6-overlay/s6-rc.d/aloha/run /etc/cont-init.d/aloha-init.sh

EXPOSE 8123 7123
VOLUME ["/data"]
