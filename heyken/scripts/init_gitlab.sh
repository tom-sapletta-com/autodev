#!/bin/bash

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
echo "  Inicjalizacja repozytoriów GitLab             "
echo "================================================="
echo -e "${NC}"

# Wczytanie zmiennych środowiskowych
if [ -f .env ]; then
    source .env
else
    echo -e "${RED}Brak pliku .env! Uruchom najpierw ./scripts/init.sh${NC}"
    exit 1
fi

# Sprawdzenie, czy wymagane zmienne są ustawione
if [ -z "$GITLAB_ROOT_PASSWORD" ] || [ -z "$GITLAB_API_TOKEN" ]; then
    echo -e "${RED}Brak wymaganych zmiennych GITLAB_ROOT_PASSWORD lub GITLAB_API_TOKEN w pliku .env${NC}"
    echo "Upewnij się, że te zmienne są ustawione i uruchom skrypt ponownie."
    exit 1
fi

ACTIVE_CORE=${ACTIVE_CORE_ID:-1}
GITLAB_URL="http://localhost:8080"
GITLAB_API_URL="${GITLAB_URL}/api/v4"
MAX_RETRIES=30
RETRY_INTERVAL=10

# Sprawdzenie, czy GitLab jest dostępny
check_gitlab_availability() {
    echo -e "${YELLOW}Sprawdzanie dostępności GitLab...${NC}"
    
    for ((i=1; i<=$MAX_RETRIES; i++)); do
        echo "Próba $i z $MAX_RETRIES..."
        
        # Testowanie połączenia z GitLab
        if curl -s "${GITLAB_URL}/users/sign_in" > /dev/null; then
            echo -e "${GREEN}GitLab jest dostępny!${NC}"
            return 0
        fi
        
        echo "GitLab jeszcze nie jest gotowy. Oczekiwanie $RETRY_INTERVAL sekund..."
        sleep $RETRY_INTERVAL
    done
    
    echo -e "${RED}Upłynął limit czasu oczekiwania na dostępność GitLab${NC}"
    return 1
}

# Funkcja oczekująca na w pełni działający GitLab
wait_for_gitlab_ready() {
    echo -e "${YELLOW}Oczekiwanie na pełną gotowość GitLab...${NC}"
    
    for ((i=1; i<=$MAX_RETRIES; i++)); do
        echo "Próba $i z $MAX_RETRIES..."
        
        # Sprawdzenie, czy API jest dostępne
        local response=$(curl -s -o /dev/null -w "%{http_code}" \
            --header "PRIVATE-TOKEN: ${GITLAB_API_TOKEN}" \
            "${GITLAB_API_URL}/version")
        
        if [[ "$response" -eq 200 ]]; then
            echo -e "${GREEN}GitLab API jest gotowe!${NC}"
            return 0
        fi
        
        echo "GitLab API jeszcze nie jest gotowe (kod: $response). Oczekiwanie $RETRY_INTERVAL sekund..."
        sleep $RETRY_INTERVAL
    done
    
    echo -e "${RED}Upłynął limit czasu oczekiwania na API GitLab${NC}"
    return 1
}

# Funkcja do tworzenia nowego repozytorium
create_repository() {
    local repo_name=$1
    local repo_description=$2
    
    echo -e "${YELLOW}Tworzenie repozytorium $repo_name...${NC}"
    
    # Sprawdzenie, czy repozytorium już istnieje
    local response=$(curl -s -o /dev/null -w "%{http_code}" \
        --header "PRIVATE-TOKEN: ${GITLAB_API_TOKEN}" \
        "${GITLAB_API_URL}/projects/root%2F${repo_name}")
    
    if [[ "$response" -eq 200 ]]; then
        echo -e "${YELLOW}Repozytorium $repo_name już istnieje${NC}"
        return 0
    fi
    
    # Utworzenie nowego repozytorium
    local create_response=$(curl -s -X POST \
        --header "PRIVATE-TOKEN: ${GITLAB_API_TOKEN}" \
        --header "Content-Type: application/json" \
        --data "{\"name\": \"${repo_name}\", \"namespace_id\": 1, \"description\": \"${repo_description}\", \"visibility\": \"internal\", \"initialize_with_readme\": true}" \
        "${GITLAB_API_URL}/projects")
    
    local project_id=$(echo "$create_response" | grep -o '"id":[0-9]*' | cut -d':' -f2 | head -1)
    
    if [[ -n "$project_id" ]]; then
        echo -e "${GREEN}Repozytorium $repo_name (ID: $project_id) utworzone pomyślnie${NC}"
        return 0
    else
        echo -e "${RED}Błąd podczas tworzenia repozytorium $repo_name${NC}"
        echo "Odpowiedź API: $create_response"
        return 1
    fi
}

# Funkcja do dodawania pliku do repozytorium
add_file_to_repo() {
    local repo_name=$1
    local file_path=$2
    local file_content=$3
    local commit_message=$4
    
    echo -e "${YELLOW}Dodawanie pliku $file_path do repozytorium $repo_name...${NC}"
    
    # Zakodowanie zawartości pliku w base64
    local content_base64=$(echo -n "$file_content" | base64 -w 0)
    
    # Dodanie pliku do repozytorium
    local response=$(curl -s -X POST \
        --header "PRIVATE-TOKEN: ${GITLAB_API_TOKEN}" \
        --header "Content-Type: application/json" \
        --data "{\"branch\": \"main\", \"commit_message\": \"${commit_message}\", \"actions\": [{\"action\": \"create\", \"file_path\": \"${file_path}\", \"content\": \"${content_base64}\", \"encoding\": \"base64\"}]}" \
        "${GITLAB_API_URL}/projects/root%2F${repo_name}/repository/commits")
    
    if echo "$response" | grep -q "\"id\":"; then
        echo -e "${GREEN}Plik $file_path dodany pomyślnie do repozytorium $repo_name${NC}"
        return 0
    else
        echo -e "${RED}Błąd podczas dodawania pliku $file_path do repozytorium $repo_name${NC}"
        echo "Odpowiedź API: $response"
        return 1
    fi
}

# Główna funkcja inicjalizująca
init_gitlab() {
    # Sprawdzenie dostępności GitLab
    if ! check_gitlab_availability; then
        echo -e "${RED}GitLab nie jest dostępny. Nie można kontynuować inicjalizacji.${NC}"
        exit 1
    fi
    
    # Oczekiwanie na pełną gotowość GitLab API
    if ! wait_for_gitlab_ready; then
        echo -e "${RED}GitLab API nie jest gotowe. Nie można kontynuować inicjalizacji.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}GitLab jest dostępny i gotowy do inicjalizacji!${NC}"
    
    # Lista repozytoriów do utworzenia
    create_repository "heyken-core" "Główny kod rdzenia systemu Heyken"
    create_repository "heyken-features" "Repozytorium funkcji systemu Heyken"
    create_repository "heyken-config" "Konfiguracja systemu Heyken"
    create_repository "heyken-docs" "Dokumentacja systemu Heyken"
    
    # Dodawanie podstawowych plików konfiguracyjnych
    add_file_to_repo "heyken-config" "config/domains.conf" "PRIMARY_DOMAIN=hey-ken.com\nALTERNATE_DOMAIN=heyken.io" "Dodanie konfiguracji domen"
    add_file_to_repo "heyken-config" "config/system.conf" "ACTIVE_CORE=${ACTIVE_CORE}\nLOGGING_LEVEL=INFO\nFEATURE_TESTING_ENABLED=true" "Dodanie konfiguracji systemu"
    
    # Dodawanie README do repozytorium dokumentacji
    add_file_to_repo "heyken-docs" "README.md" "# System Heyken - Dokumentacja

## O projekcie
Heyken to autonomiczny system z dwoma redundantnymi rdzeniami, zaprojektowany do samorozwoju i uczenia się.

## Domeny
- Główna domena: hey-ken.com
- Alternatywna domena: heyken.io

## Architektura
System składa się z następujących komponentów:
- Dwa redundantne rdzenie (active/standby)
- Piaskownica do testowania nowych funkcji
- Rejestr komponentów
- System monitorowania
- API logowania

## Zarządzanie systemem
- Przełączanie aktywnego rdzenia: `./scripts/switch_core.sh [1|2]`
- Monitorowanie stanu: `./scripts/status.sh`
- Utworzenie nowej funkcji: `./scripts/create_feature.sh [nazwa_funkcji]`
- Sprawdzanie logów: `./scripts/logs.sh [komponent]`
" "Dodanie podstawowej dokumentacji"
    
    echo -e "${GREEN}Inicjalizacja repozytoriów GitLab zakończona pomyślnie!${NC}"
}

# Uruchomienie głównej funkcji
init_gitlab
