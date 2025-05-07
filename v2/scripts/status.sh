#!/bin/bash

# Skrypt do sprawdzania stanu systemu

# Kolory dla lepszej czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "================================================="
echo "  System Autonomiczny z Redundantnymi Rdzeniami  "
echo "  Status Systemu                                 "
echo "================================================="
echo -e "${NC}"

# Wczytanie aktualnego stanu
ACTIVE_CORE=$(grep ACTIVE_CORE_ID .env | cut -d= -f2)

echo -e "${YELLOW}Aktywny rdzeń: $ACTIVE_CORE${NC}"
echo ""

# Sprawdzenie statusu kontenerów
echo -e "${YELLOW}Status kontenerów:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""

# Sprawdzenie statusu API rdzenia
echo -e "${YELLOW}Status API rdzenia:${NC}"
curl -s http://localhost:5000/status | jq .

echo ""

# Sprawdzenie statusu dostępnych funkcji
echo -e "${YELLOW}Dostępne funkcje:${NC}"
curl -s http://localhost:5000/components | jq .

echo ""

# Sprawdzenie statusu GitLab
echo -e "${YELLOW}Status GitLab:${NC}"
GITLAB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080)
if [ "$GITLAB_STATUS" == "200" ]; then
    echo -e "${GREEN}GitLab działa (HTTP 200)${NC}"
else
    echo -e "${RED}GitLab nie odpowiada (HTTP $GITLAB_STATUS)${NC}"
fi

# Sprawdzenie statusu Ollama
echo -e "${YELLOW}Status Ollama:${NC}"
OLLAMA_RESPONSE=$(curl -s http://localhost:11434/api/tags)
if [ $? -eq 0 ]; then
    MODELS=$(echo $OLLAMA_RESPONSE | jq '.models | length')
    echo -e "${GREEN}Ollama działa, dostępne modele: $MODELS${NC}"
else
    echo -e "${RED}Ollama nie odpowiada${NC}"
fi

# Sprawdzenie statusu Rocket.Chat
echo -e "${YELLOW}Status Rocket.Chat:${NC}"
ROCKETCHAT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
if [ "$ROCKETCHAT_STATUS" == "200" ]; then
    echo -e "${GREEN}Rocket.Chat działa (HTTP 200)${NC}"
else
    echo -e "${RED}Rocket.Chat nie odpowiada (HTTP $ROCKETCHAT_STATUS)${NC}"
fi

# Sprawdzenie statusu systemu monitorowania
echo -e "${YELLOW}Status systemu monitorowania:${NC}"
MONITOR_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5021/status)
if [ "$MONITOR_STATUS" == "200" ]; then
    echo -e "${GREEN}System monitorowania działa (HTTP 200)${NC}"
else
    echo -e "${RED}System monitorowania nie odpowiada (HTTP $MONITOR_STATUS)${NC}"
fi