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
echo "  Sprawdzanie i naprawa systemu                 "
echo "================================================="
echo -e "${NC}"

# Tablica komponentów z oczekiwanymi statusami
# Format: "nazwa_kontenera:port:endpoint"
COMPONENTS=(
    "core_manager_core1:5000:/health"
    "ollama_core1:11434:/api/version"
    "gitlab_core1:80/health"
    "middleware_core1:5000/health"
    "component_registry_core1:5000/components"
    "feature_runner:5000/status"
    "sandbox_manager:5000/status"
    "test_ollama:11434/api/version"
    "system_db:5432:"
    "system_monitor:5000/health"
    "logger_api:5000/logs?limit=1"
)

# Ładowanie zmiennych środowiskowych
if [ -f .env ]; then
    source .env
else
    echo -e "${YELLOW}Brak pliku .env - tworzenie domyślnego pliku...${NC}"
    cat > .env <<EOL
ACTIVE_CORE_ID=1
GITLAB_ROOT_PASSWORD=HIPfQL+Zi4Pztt7P
GITLAB_API_TOKEN=glpat-random-token
GEMINI_API_KEY=
CLAUDE_API_KEY=
POSTGRES_PASSWORD=postgres
ROCKETCHAT_ADMIN_PASSWORD=+1iMwT9zoFpJySql
EOL
    source .env
    echo -e "${GREEN}Utworzono domyślny plik .env${NC}"
fi

# Funkcja do sprawdzania, czy kontener Docker jest uruchomiony
check_container() {
    local container_name=$1
    local status=$(docker ps --filter "name=$container_name" --format "{{.Status}}" 2>/dev/null)
    
    if [[ -z "$status" ]]; then
        echo -e "${RED}[ERROR] Kontener $container_name nie jest uruchomiony${NC}"
        return 1
    else
        echo -e "${GREEN}[OK] Kontener $container_name jest uruchomiony ($status)${NC}"
        return 0
    fi
}

# Funkcja do naprawiania kontenera (restart lub recreate jeśli potrzeba)
fix_container() {
    local container_name=$1
    echo -e "${YELLOW}Próba naprawy kontenera $container_name...${NC}"
    
    # Sprawdź, czy kontener istnieje
    if docker ps -a --filter "name=$container_name" --format "{{.Names}}" | grep -q "$container_name"; then
        # Kontener istnieje, spróbuj go uruchomić
        echo "Uruchamianie kontenera $container_name..."
        docker start "$container_name" >/dev/null 2>&1
        
        # Sprawdź, czy kontener działa poprawnie po uruchomieniu
        sleep 3
        if check_container "$container_name"; then
            echo -e "${GREEN}Kontener $container_name pomyślnie uruchomiony${NC}"
            return 0
        else
            # Kontener nadal nie działa, spróbuj go zrestartować
            echo "Restart kontenera $container_name..."
            docker restart "$container_name" >/dev/null 2>&1
            sleep 5
            
            if check_container "$container_name"; then
                echo -e "${GREEN}Kontener $container_name pomyślnie zrestartowany${NC}"
                return 0
            else
                echo -e "${RED}Restart kontenera $container_name nie pomógł. Próba ponownego wdrożenia...${NC}"
                return 1
            fi
        fi
    else
        echo -e "${RED}Kontener $container_name nie istnieje. Konieczne ponowne wdrożenie.${NC}"
        return 1
    fi
}

# Funkcja do sprawdzania dostępności endpointu API
check_endpoint() {
    local container=$1
    local port=$2
    local endpoint=$3
    
    # Jeśli endpoint jest pusty, pomijamy sprawdzenie API
    if [[ -z "$endpoint" ]]; then
        return 0
    fi
    
    # Określenie pełnego URL
    local url="http://localhost:$port$endpoint"
    echo "Sprawdzanie endpointu: $url"
    
    # Sprawdzenie, czy endpoint odpowiada
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
    
    if [[ "$response" -ge 200 && "$response" -lt 300 ]]; then
        echo -e "${GREEN}[OK] Endpoint $url jest dostępny (kod $response)${NC}"
        return 0
    else
        echo -e "${RED}[ERROR] Endpoint $url nie jest dostępny (kod $response)${NC}"
        return 1
    fi
}

# Funkcja sprawdzająca dostępność portu
check_port() {
    local port=$1
    
    # Sprawdzenie, czy port jest otwarty
    if nc -z localhost "$port" >/dev/null 2>&1; then
        echo -e "${GREEN}[OK] Port $port jest otwarty${NC}"
        return 0
    else
        echo -e "${RED}[ERROR] Port $port nie jest otwarty${NC}"
        return 1
    fi
}

# Funkcja sprawdzająca kolizje portów
check_port_conflicts() {
    echo -e "${BLUE}Sprawdzanie kolizji portów...${NC}"
    
    local ports=(5000 5001 5002 5003 8080 8081 11434 11435 5432 3000 9090)
    local conflicts=0
    
    for port in "${ports[@]}"; do
        # Sprawdź, ile procesów używa tego portu
        local count=$(ss -tulpn | grep ":$port " | wc -l)
        
        if [[ $count -gt 1 ]]; then
            echo -e "${RED}[ERROR] Wykryto kolizję na porcie $port - $count procesów używa tego portu${NC}"
            echo "Procesy używające portu $port:"
            ss -tulpn | grep ":$port "
            conflicts=$((conflicts + 1))
        fi
    done
    
    if [[ $conflicts -eq 0 ]]; then
        echo -e "${GREEN}Nie wykryto kolizji portów${NC}"
        return 0
    else
        echo -e "${RED}Wykryto $conflicts kolizji portów${NC}"
        return 1
    fi
}

# Funkcja zatrzymująca konfliktowe procesy Ollama
fix_ollama_conflicts() {
    echo -e "${YELLOW}Naprawa kolizji dla Ollama...${NC}"
    
    # Sprawdź, czy natywny proces Ollama działa
    if pgrep ollama >/dev/null; then
        echo "Zatrzymywanie natywnego procesu Ollama..."
        if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet ollama; then
            echo "Zatrzymywanie usługi Ollama przez systemctl..."
            systemctl stop ollama
        else
            echo "Zatrzymywanie procesu Ollama..."
            pkill ollama
        fi
        sleep 2
    fi
    
    # Sprawdź, czy są uruchomione kontenery z Ollamą, które nie należą do naszego systemu
    local ollama_containers=$(docker ps | grep ollama | grep -v "ollama_core1\|test_ollama" | awk '{print $1}')
    if [[ -n "$ollama_containers" ]]; then
        echo "Zatrzymywanie zewnętrznych kontenerów Ollama..."
        for container_id in $ollama_containers; do
            echo "Zatrzymywanie kontenera $container_id..."
            docker stop "$container_id" >/dev/null 2>&1
        done
        sleep 2
    fi
    
    # Sprawdź, czy porty 11434 i 11435 są teraz wolne
    if nc -z localhost 11434 >/dev/null 2>&1 || nc -z localhost 11435 >/dev/null 2>&1; then
        echo -e "${RED}Nie udało się zwolnić portów Ollama${NC}"
        return 1
    else
        echo -e "${GREEN}Porty Ollama zostały zwolnione${NC}"
        return 0
    fi
}

# Funkcja sprawdzająca i naprawiająca jeden komponent
check_and_fix_component() {
    local component_info=$1
    IFS=':' read -r container_name port endpoint <<< "$component_info"
    
    echo -e "${BLUE}\nSprawdzanie komponentu: $container_name${NC}"
    
    # Sprawdź, czy kontener jest uruchomiony
    if ! check_container "$container_name"; then
        fix_container "$container_name"
        
        # Jeśli naprawa kontenera nie powiodła się, oznacz konieczność ponownego wdrożenia
        if [[ $? -ne 0 ]]; then
            return 1
        fi
    fi
    
    # Sprawdź port (tylko jeśli port jest określony)
    if [[ -n "$port" ]]; then
        if ! check_port "$port"; then
            echo -e "${YELLOW}Port $port nie jest dostępny dla $container_name${NC}"
            return 1
        fi
        
        # Sprawdź endpoint API (tylko jeśli endpoint jest określony)
        if [[ -n "$endpoint" ]]; then
            if ! check_endpoint "$container_name" "$port" "$endpoint"; then
                echo -e "${YELLOW}Endpoint $endpoint nie jest dostępny dla $container_name${NC}"
                return 1
            fi
        fi
    fi
    
    return 0
}

# Główna funkcja sprawdzająca
# Uruchamianie przechwytywania logów na początku
start_container_logging

# Zatrzymanie przechwytywania logów przy wyjściu
trap stop_container_logging EXIT

main() {
    echo -e "${BLUE}Rozpoczęcie sprawdzania systemu Heyken...${NC}"
    
    # Tablica przechowująca komponenty, które wymagają naprawy
    FAILED_COMPONENTS=()
    
    # Sprawdź, czy Docker jest uruchomiony
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}[ERROR] Docker nie jest uruchomiony${NC}"
        echo "Próba uruchomienia Docker..."
        sudo systemctl start docker >/dev/null 2>&1
        sleep 5
        
        if ! docker info >/dev/null 2>&1; then
            echo -e "${RED}Nie udało się uruchomić Dockera. Napraw to ręcznie i uruchom skrypt ponownie.${NC}"
            exit 1
        else
            echo -e "${GREEN}Docker został pomyślnie uruchomiony${NC}"
        fi
    else
        echo -e "${GREEN}[OK] Docker jest uruchomiony${NC}"
    fi
    
    # Sprawdź, czy są kolizje portów
    if ! check_port_conflicts; then
        echo -e "${YELLOW}Wykryto kolizje portów. Próba naprawy...${NC}"
        
        # Napraw kolizje dla Ollama (najczęstszy problem)
        fix_ollama_conflicts
    fi
    
    # Sprawdź każdy komponent
    for component in "${COMPONENTS[@]}"; do
        if ! check_and_fix_component "$component"; then
            # Wyodrębnij nazwę kontenera z informacji o komponencie
            IFS=':' read -r container_name _ _ <<< "$component"
            FAILED_COMPONENTS+=("$container_name")
        fi
    done
    
    # Jeśli są komponenty, które wymagają naprawy, spróbuj ponownie wdrożyć
    if [[ ${#FAILED_COMPONENTS[@]} -gt 0 ]]; then
        echo -e "${RED}\nWykryto problemy z następującymi komponentami:${NC}"
        for component in "${FAILED_COMPONENTS[@]}"; do
            echo "- $component"
        done
        
        echo -e "${YELLOW}\nPróba ponownego wdrożenia systemu...${NC}"
        
        # Zatrzymaj wszystkie kontenery przed ponownym wdrożeniem
        echo "Zatrzymywanie kontenerów Docker..."
        docker stop $(docker ps -q) >/dev/null 2>&1
        
        # Uruchom skrypt wdrożeniowy
        echo "Uruchamianie skryptu deploy.sh..."
        ./scripts/deploy.sh
        
        if [[ $? -eq 0 ]]; then
            echo -e "${GREEN}\nSystem Heyken został pomyślnie ponownie wdrożony${NC}"
            
            # Inicjalizacja repozytoriów GitLab
            echo -e "${YELLOW}\nInicjalizacja repozytoriów GitLab...${NC}"
            if [ -f ./scripts/init_gitlab.sh ]; then
                ./scripts/init_gitlab.sh
                if [[ $? -eq 0 ]]; then
                    echo -e "${GREEN}Repozytoria GitLab zostały pomyślnie zainicjalizowane${NC}"
                else
                    echo -e "${YELLOW}Ostrzeżenie: Inicjalizacja repozytoriów GitLab nie powiodła się w pełni.${NC}"
                    echo "Możliwe, że GitLab nie jest jeszcze w pełni uruchomiony. Możesz spróbować uruchomić ./scripts/init_gitlab.sh później."
                fi
            else
                echo -e "${YELLOW}Skrypt init_gitlab.sh nie został znaleziony. Pomiń inicjalizację GitLab.${NC}"
            fi
        else
            echo -e "${RED}\nPonowne wdrożenie nie powiodło się. Konieczna ręczna interwencja.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}\nWszystkie komponenty systemu Heyken działają poprawnie!${NC}"
    fi
}

# Uruchomienie głównej funkcji
main
