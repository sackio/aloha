#!/usr/bin/env bashio

# Read options from the add-on configuration
AI_PROVIDER=$(bashio::config 'ai_provider')
MODEL=$(bashio::config 'model')
SAFETY_MODE=$(bashio::config 'safety_mode')
CONTEXT_REFRESH_MINUTES=$(bashio::config 'context_refresh_minutes')

# Export Aloha environment variables
export ALOHA_MODE="standalone"
export ALOHA_AI_PROVIDER="${AI_PROVIDER}"
export ALOHA_MODEL="${MODEL}"
export ALOHA_SAFETY_MODE="${SAFETY_MODE}"
export ALOHA_CONTEXT_REFRESH_MINUTES="${CONTEXT_REFRESH_MINUTES}"

# Home Assistant connection via Supervisor
export ALOHA_HA_URL="http://supervisor/core"
export ALOHA_HA_TOKEN="${SUPERVISOR_TOKEN}"

# Data directory inside the add-on data volume
export ALOHA_DATA_DIR="/data/aloha"

# Ensure the data directory exists
mkdir -p /data/aloha

bashio::log.info "Starting Aloha (provider=${AI_PROVIDER}, model=${MODEL}, safety=${SAFETY_MODE})"

exec python3 -m aloha
