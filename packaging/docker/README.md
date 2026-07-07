# Aloha — Docker

The all-in-one image bundles Home Assistant and the Aloha agent.

## Bundled (HA + Aloha in one container)

```bash
docker run -d --name aloha \
  -p 8123:8123 -p 7123:7123 \
  -v aloha-data:/data \
  ghcr.io/sackio/aloha:latest
```

- **Aloha UI:** http://localhost:7123 · **Home Assistant:** http://localhost:8123

Or with compose:

```bash
docker compose -f packaging/docker/docker-compose.yml up -d
```

## Standalone (bring your own Home Assistant)

```bash
docker run -d --name aloha -p 7123:7123 \
  -e ALOHA_MODE=standalone -e ALOHA_HA_URL=http://your-ha:8123 \
  -v aloha-data:/data ghcr.io/sackio/aloha:latest
```

## Confirm it works

```bash
./packaging/docker/confirm.sh          # builds locally, runs, waits for both services
```
