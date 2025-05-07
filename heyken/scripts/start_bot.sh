#!/bin/bash
# Skrypt do uruchomienia bota Heyken

# Kolory do komunikatów
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}         URUCHAMIANIE BOTA HEYKEN                ${NC}"
echo -e "${GREEN}=================================================${NC}"

# Sprawdź czy Node.js jest zainstalowany
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js nie jest zainstalowany. Proszę zainstalować Node.js.${NC}"
    exit 1
fi

# Sprawdź czy npm jest zainstalowany
if ! command -v npm &> /dev/null; then
    echo -e "${RED}npm nie jest zainstalowany. Proszę zainstalować npm.${NC}"
    exit 1
fi

# Przejdź do katalogu skryptów
cd "$(dirname "$0")"

# Sprawdź czy istnieje package.json, jeśli nie, utwórz go
if [ ! -f package.json ]; then
    echo -e "${YELLOW}Tworzenie pliku package.json...${NC}"
    npm init -y
fi

# Zainstaluj wymagane zależności
echo -e "${YELLOW}Instalowanie wymaganych zależności...${NC}"
npm install ws axios

# Uruchom bota
echo -e "${YELLOW}Uruchamianie bota...${NC}"
node heyken_bot.js

echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}         BOT HEYKEN URUCHOMIONY                  ${NC}"
echo -e "${GREEN}=================================================${NC}"
