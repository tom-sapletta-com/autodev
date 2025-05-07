#!/bin/bash

# Skrypt do przełączania między rdzeniami systemu

# Kolory dla lepszej czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Sprawdzenie argumentów
if [ $# -ne 1 ]; then
    echo -e "${RED}Błąd: Podaj numer rdzenia (1 lub 2)${NC}"
    echo "Użycie: $0 [1|2]"
    exit 1
fi

CORE_ID=$1

if [ "$CORE_ID" != "1" ] && [ "$CORE_ID" != "2" ]; then
    echo -e "${RED}Błąd: Numer rdzenia musi być 1 lub 2${NC}"
    exit 1
fi

# Banner
echo -e "${BLUE}"
echo "================================================="
echo "  Heyken - System Autonomiczny                  "
echo "  Przełączanie Aktywnego Rdzenia                  "
echo "================================================="
echo -e "${NC}"

# Wczytanie aktualnego stanu
CURRENT_CORE=$(grep ACTIVE_CORE_ID .env | cut -d= -f2)

if [ "$CURRENT_CORE" == "$CORE_ID" ]; then
    echo -e "${YELLOW}Rdzeń $CORE_ID jest już aktywny!${NC}"
    exit 0
fi

echo -e "${YELLOW}Przełączanie z rdzenia $CURRENT_CORE na rdzeń $CORE_ID...${NC}"

# Aktualizacja pliku .env
sed -i "s/ACTIVE_CORE_ID=.*/ACTIVE_CORE_ID=$CORE_ID/" .env

# Aktualizacja konfiguracji Terraform
cd terraform
terraform apply -var="active_core_id=${CORE_ID}" -auto-approve
if [ $? -ne 0 ]; then
    echo -e "${RED}Błąd podczas aktualizacji Terraform!${NC}"
    echo -e "${RED}Przywracanie poprzedniego stanu...${NC}"
    sed -i "s/ACTIVE_CORE_ID=.*/ACTIVE_CORE_ID=$CURRENT_CORE/" ../.env
    terraform apply -var="active_core_id=${CURRENT_CORE}" -auto-approve
    exit 1
fi
cd ..

# Aktualizacja shared state
echo "Active core: $CORE_ID" > data/shared/active_core

# Oczekiwanie na przełączenie
echo -e "${YELLOW}Oczekiwanie na przełączenie rdzeni...${NC}"
sleep 10

# Sprawdzenie statusu nowego rdzenia
./scripts/status.sh

echo -e "${GREEN}Przełączenie na rdzeń $CORE_ID zakończone pomyślnie.${NC}"