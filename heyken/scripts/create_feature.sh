#!/bin/bash

# Skrypt do tworzenia nowej funkcji systemu

# Kolory dla lepszej czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Sprawdzenie argumentów
if [ $# -lt 1 ]; then
    echo -e "${RED}Błąd: Podaj nazwę funkcji${NC}"
    echo "Użycie: $0 <nazwa_funkcji> [opis]"
    exit 1
fi

FEATURE_NAME=$1
FEATURE_DESC=${2:-"Nowa funkcja systemu"}

# Banner
echo -e "${BLUE}"
echo "================================================="
echo "  System Autonomiczny z Redundantnymi Rdzeniami  "
echo "  Tworzenie Nowej Funkcji                        "
echo "================================================="
echo -e "${NC}"

# Wczytanie aktualnego stanu
ACTIVE_CORE=$(grep ACTIVE_CORE_ID .env | cut -d= -f2)

echo -e "${YELLOW}Tworzenie nowej funkcji: $FEATURE_NAME${NC}"
echo -e "${YELLOW}Opis: $FEATURE_DESC${NC}"
echo -e "${YELLOW}Aktywny rdzeń: $ACTIVE_CORE${NC}"
echo ""

# Tworzenie katalogu dla funkcji
FEATURE_DIR="components/$FEATURE_NAME"
mkdir -p $FEATURE_DIR

# Tworzenie podstawowych plików
echo -e "${YELLOW}Tworzenie struktury projektu...${NC}"

# Plik Dockerfile
cat > $FEATURE_DIR/Dockerfile << EOF
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
EOF

# Plik requirements.txt
cat > $FEATURE_DIR/requirements.txt << EOF
flask==2.0.1
requests==2.26.0
EOF

# Plik app.py
cat > $FEATURE_DIR/app.py << EOF
#!/usr/bin/env python3

import os
import json
import logging
from flask import Flask, request, jsonify

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("$FEATURE_NAME")

app = Flask(__name__)

@app.route('/status', methods=['GET'])
def status():
    """Endpoint statusu"""
    return jsonify({
        "name": "$FEATURE_NAME",
        "status": "ok",
        "description": "$FEATURE_DESC"
    })

@app.route('/process', methods=['POST'])
def process():
    """Główny endpoint przetwarzania"""
    data = request.json

    # Tutaj implementacja właściwej logiki

    return jsonify({
        "success": True,
        "message": "Przetwarzanie zakończone pomyślnie"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF

# Plik README.md
cat > $FEATURE_DIR/README.md << EOF
# $FEATURE_NAME

$FEATURE_DESC

## Opis

Nowa funkcja systemu autonomicznego z redundantnymi rdzeniami.

## API

### GET /status

Zwraca status komponentu.

### POST /process

Główny endpoint przetwarzania.

## Konfiguracja

Konfiguracja poprzez zmienne środowiskowe:

- \`PORT\` - Port na którym działa serwer (domyślnie 5000)
EOF

# Plik .gitlab-ci.yml
cat > $FEATURE_DIR/.gitlab-ci.yml << EOF
# .gitlab-ci.yml - Konfiguracja CI/CD dla funkcji $FEATURE_NAME

include:
  - project: 'system/templates'
    file: 'gitlab-ci-template.yml'

variables:
  COMPONENT_DESCRIPTION: "$FEATURE_DESC"
EOF

# Plik docker-compose.yml dla testów lokalnych
cat > $FEATURE_DIR/docker-compose.yml << EOF
version: '3.8'

services:
  $FEATURE_NAME:
    build: .
    container_name: $FEATURE_NAME
    ports:
      - "5000:5000"
    environment:
      - PORT=5000
    volumes:
      - ./:/app
EOF

# Utworzenie repozytorium GitLab
echo -e "${YELLOW}Tworzenie repozytorium GitLab...${NC}"

# Wczytanie tokenu GitLab z pliku .env
GITLAB_API_TOKEN=$(grep GITLAB_API_TOKEN .env | cut -d= -f2)

# Stworzenie projektu w GitLab
GITLAB_RESPONSE=$(curl -s -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$FEATURE_NAME\", \"description\": \"$FEATURE_DESC\", \"visibility\": \"internal\"}" \
  http://localhost:8080/api/v4/projects)

# Sprawdzenie, czy projekt został utworzony pomyślnie
if echo $GITLAB_RESPONSE | jq -e '.id' > /dev/null; then
    PROJECT_ID=$(echo $GITLAB_RESPONSE | jq -r '.id')
    echo -e "${GREEN}Repozytorium GitLab utworzone pomyślnie. ID: $PROJECT_ID${NC}"

    # Inicjalizacja repozytorium git
    cd $FEATURE_DIR
    git init
    git add .
    git commit -m "Inicjalna wersja funkcji $FEATURE_NAME"

    # Dodanie zdalnego repozytorium
    git remote add origin http://localhost:8080/system/$FEATURE_NAME.git

    # Ustawienie danych użytkownika
    git config user.name "System"
    git config user.email "system@example.com"

    # Wysłanie kodu do GitLab
    echo -e "${YELLOW}Wysyłanie kodu do GitLab...${NC}"
    git push -u origin master

    echo -e "${GREEN}Kod wysłany pomyślnie.${NC}"

    # Powrót do głównego katalogu
    cd ../..
else
    echo -e "${RED}Nie udało się utworzyć repozytorium GitLab.${NC}"
    echo $GITLAB_RESPONSE | jq .
fi

# Informacja końcowa
echo -e "${BLUE}"
echo "================================================="
echo "  Funkcja $FEATURE_NAME utworzona pomyślnie!     "
echo "================================================="
echo -e "${NC}"
echo "Struktura projektu znajduje się w katalogu: $FEATURE_DIR"
echo "Repozytorium GitLab: http://localhost:8080/system/$FEATURE_NAME"
echo ""
echo "Możliwe akcje:"
echo "- Edytuj kod funkcji: cd $FEATURE_DIR"
echo "- Zbuduj lokalnie: cd $FEATURE_DIR && docker-compose build"
echo "- Uruchom lokalnie: cd $FEATURE_DIR && docker-compose up"
echo "- Wypchnij zmiany: cd $FEATURE_DIR && git add . && git commit -m \"Update\" && git push"
echo ""
echo "Aby dodać funkcję do systemu, użyj pipeline'u w GitLab."