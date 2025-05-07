#!/bin/bash

# ===== Heyken - Ollama Setup Script =====
# Script to setup and configure Ollama for Heyken

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set base project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR" || { echo -e "${RED}Cannot change to project directory!${NC}"; exit 1; }

# Load environment variables
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
else
  echo -e "${RED}Error: .env file not found. Run ./run.sh first to create it.${NC}"
  exit 1
fi

# Set default values if not defined
OLLAMA_MODEL=${OLLAMA_MODEL:-llama3}
OLLAMA_PORT=${OLLAMA_PORT:-11434}
DATA_DIR=${DATA_DIR:-"$PROJECT_DIR/data"}
LOGS_DIR=${LOGS_DIR:-"$PROJECT_DIR/logs"}

# Create necessary directories
OLLAMA_MODELS_DIR="$DATA_DIR/ollama"
mkdir -p "$OLLAMA_MODELS_DIR"
mkdir -p "$LOGS_DIR/ollama"

# Function for logging
log() {
  local level=$1
  local message=$2
  local color=$NC
  
  case $level in
    "INFO") color=$GREEN ;;
    "WARN") color=$YELLOW ;;
    "ERROR") color=$RED ;;
    "DEBUG") color=$BLUE ;;
  esac
  
  echo -e "${color}[$level] $message${NC}"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOGS_DIR/ollama/setup.log"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  log "ERROR" "Docker is not installed. Please install Docker first."
  exit 1
fi

# Check if Ollama container is already running
if docker ps | grep -q ollama; then
  log "WARN" "Stopping existing Ollama container..."
  docker stop ollama > /dev/null 2>&1
  docker rm ollama > /dev/null 2>&1
fi

# Set permissions for Ollama directory
log "INFO" "Setting permissions for Ollama directory..."
chmod -R 777 "$OLLAMA_MODELS_DIR"

# Check if model is already downloaded
MODEL_DOWNLOADED=false
if [ -d "$OLLAMA_MODELS_DIR/models" ]; then
  if find "$OLLAMA_MODELS_DIR/models" -type f -name "*$OLLAMA_MODEL*" | grep -q .; then
    log "INFO" "Model $OLLAMA_MODEL is already available locally."
    MODEL_DOWNLOADED=true
  fi
fi

# If model is not downloaded, prepare for download
if [ "$MODEL_DOWNLOADED" = false ]; then
  log "INFO" "Model $OLLAMA_MODEL is not available locally. Will be downloaded when Ollama starts."
  mkdir -p "$OLLAMA_MODELS_DIR/models"
fi

# Start Ollama container
log "INFO" "Starting Ollama container..."
docker run -d \
  --name ollama \
  --restart unless-stopped \
  -p $OLLAMA_PORT:11434 \
  -v "$OLLAMA_MODELS_DIR:/root/.ollama" \
  ollama/ollama:latest

# Wait for Ollama to start
log "INFO" "Waiting for Ollama to start..."
MAX_ATTEMPTS=30
ATTEMPT=0
OLLAMA_READY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  echo -n "."
  # Try to connect to Ollama
  if curl -s "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null; then
    echo ""
    log "INFO" "Ollama is ready!"
    OLLAMA_READY=true
    break
  fi
  ATTEMPT=$((ATTEMPT+1))
  sleep 2
done

if [ "$OLLAMA_READY" = false ]; then
  log "ERROR" "Ollama did not start properly. Check docker logs."
  exit 1
fi

# Pull the model if not already downloaded
if [ "$MODEL_DOWNLOADED" = false ]; then
  log "INFO" "Pulling model $OLLAMA_MODEL..."
  curl -X POST "http://localhost:$OLLAMA_PORT/api/pull" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$OLLAMA_MODEL\"}" || {
      log "ERROR" "Failed to pull model $OLLAMA_MODEL"
      exit 1
    }
  log "INFO" "Model $OLLAMA_MODEL pulled successfully."
fi

log "INFO" "Ollama setup completed successfully."
log "INFO" "Ollama API available at: http://localhost:$OLLAMA_PORT"
log "INFO" "Model in use: $OLLAMA_MODEL"

exit 0
