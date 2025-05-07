#!/bin/bash

# Skrypt do budowania obrazów Docker dla projektu Heyken

# Kolory dla lepszej czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "================================================="
echo "  Heyken - System Autonomiczny                  "
echo "  Budowanie obrazów Docker                       "
echo "================================================="
echo -e "${NC}"

cd "$(dirname "$0")/.."
DOCKER_DIR="$(pwd)/docker"

# Lista obrazów do zbudowania
IMAGES=(
    "core_manager"
    "feature_runner"
    "sandbox_manager"
    "component_registry"
    "logger_api"
    "system_monitor"
)

# Budowanie obrazów
for IMAGE in "${IMAGES[@]}"; do
    echo -e "${YELLOW}Budowanie obrazu ${IMAGE}...${NC}"
    
    if [ -d "${DOCKER_DIR}/${IMAGE}" ]; then
        docker build -t ${IMAGE}:latest "${DOCKER_DIR}/${IMAGE}"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Obraz ${IMAGE} zbudowany pomyślnie.${NC}"
        else
            echo -e "${RED}Błąd podczas budowania obrazu ${IMAGE}!${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Brak katalogu ${DOCKER_DIR}/${IMAGE}!${NC}"
        exit 1
    fi
done

echo -e "${GREEN}Wszystkie obrazy zostały pomyślnie zbudowane.${NC}"
echo -e "${YELLOW}Możesz teraz uruchomić './scripts/deploy.sh' aby wdrożyć system.${NC}"
