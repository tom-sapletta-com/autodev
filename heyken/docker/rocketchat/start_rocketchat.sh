#!/bin/bash

# Kolory dla lepszej czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Przygotowanie katalogu na logi
LOG_DIR="../../logs/rocketchat"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/startup_$TIMESTAMP.log"
mkdir -p "$LOG_DIR"

# Funkcja do logowania - zapisuje do pliku i wyświetla na ekranie
log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO] $timestamp - $message${NC}" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN] $timestamp - $message${NC}" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR] $timestamp - $message${NC}" | tee -a "$LOG_FILE"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS] $timestamp - $message${NC}" | tee -a "$LOG_FILE"
            ;;
        *)
            echo -e "$message" | tee -a "$LOG_FILE"
            ;;
    esac
}

log "" "${BLUE}"
log "" "================================================="
log "" "  Heyken - System Autonomiczny                  "
log "" "  Uruchamianie Rocket.Chat                       "
log "" "================================================="
log "" "${NC}"

log "INFO" "Rozpoczynam uruchamianie Rocket.Chat. Logi zapisywane do: $LOG_FILE"

# Pobierz uprawnienia sudo na początku, żeby później nie pytać o hasło
log "INFO" "Uzyskiwanie uprawnień administratora do zatrzymania procesów blokujących porty..."
sudo -v
if [ $? -ne 0 ]; then
    log "ERROR" "Nie można uzyskać uprawnień administratora. Niektóre operacje mogą się nie powieść."
    log "WARN" "Spróbuj uruchomić ponownie skrypt z uprawnieniami root: sudo $0"
    exit 1
fi

# Funkcja do sprawdzania, czy port jest otwarty
check_port() {
    local port=$1
    if ss -tuln | grep -q ":$port "; then
        return 0 # Port jest zajęty
    else
        return 1 # Port jest wolny
    fi
}

# Funkcja do zatrzymywania kontenera korzystającego z danego portu
stop_container_using_port() {
    local port=$1
    local containers=$(docker ps -q)
    
    if [ -z "$containers" ]; then
        return 1 # Brak działających kontenerów
    fi
    
    for container in $containers; do
        # Sprawdzenie, czy kontener korzysta z danego portu
        if docker port $container | grep -q ":$port->"; then
            echo -e "${YELLOW}Zatrzymywanie kontenera korzystającego z portu $port: $(docker ps --format "{{.Names}}" -f "id=$container")${NC}"
            docker stop $container
            return 0
        fi
    done
    
    return 1 # Nie znaleziono kontenera używającego tego portu
}

# Funkcja do zatrzymywania procesu korzystającego z danego portu
stop_process_using_port() {
    local port=$1
    
    # Zatrzymywanie przy użyciu sudo, aby obejść ograniczenia uprawnień
    echo -e "${YELLOW}Zatrzymywanie procesów na porcie $port...${NC}"
    
    # Próba użycia różnych metod, aby znaleźć i zatrzymać proces
    if command -v lsof &>/dev/null; then
        # Użyj lsof do znalezienia PID
        local pids=$(sudo lsof -i :$port -t 2>/dev/null)
        if [ -n "$pids" ]; then
            echo -e "${YELLOW}Zatrzymywanie procesów (PID: $pids) korzystających z portu $port${NC}"
            for pid in $pids; do
                sudo kill -15 $pid 2>/dev/null || sudo kill -9 $pid 2>/dev/null
            done
            sleep 2
            return 0
        fi
    fi
    
    # Alternatywna metoda z użyciem fuser
    if command -v fuser &>/dev/null; then
        echo -e "${YELLOW}Próba użycia fuser do zatrzymania procesu na porcie $port${NC}"
        sudo fuser -k -n tcp $port 2>/dev/null
        sleep 2
        if ! check_port $port; then
            return 0
        fi
    fi
    
    # Próba zatrzymania bezpośrednio dockera, jeśli powyższe metody zawiodły
    echo -e "${YELLOW}Próba zatrzymania wszystkich kontenerów Docker...${NC}"
    sudo docker stop $(sudo docker ps -q) 2>/dev/null
    sleep 2
    
    return 1
}

# Funkcja do zwalniania zajętego portu
free_port() {
    local port=$1
    local max_attempts=3
    local attempt=1
    
    echo -e "${YELLOW}Sprawdzanie portu $port...${NC}"
    
    while check_port $port && [ $attempt -le $max_attempts ]; do
        echo -e "${YELLOW}Port $port jest zajęty. Próba zwolnienia... ($attempt/$max_attempts)${NC}"
        
        # Spróbuj zatrzymać kontener Docker korzystający z portu
        if stop_container_using_port $port; then
            echo -e "${GREEN}Zatrzymano kontener korzystający z portu $port${NC}"
        # Jeśli nie znaleziono kontenera, spróbuj zatrzymać proces
        elif stop_process_using_port $port; then
            echo -e "${GREEN}Zatrzymano proces korzystający z portu $port${NC}"
        else
            echo -e "${RED}Nie można zidentyfikować procesu korzystającego z portu $port${NC}"
        fi
        
        # Sprawdź, czy port został zwolniony
        if ! check_port $port; then
            echo -e "${GREEN}Port $port został zwolniony${NC}"
            break
        fi
        
        attempt=$((attempt + 1))
        sleep 1
    done
    
    if check_port $port; then
        echo -e "${RED}Nie udało się zwolnić portu $port po $max_attempts próbach${NC}"
        return 1
    fi
    
    return 0
}

# Sprawdzenie, czy docker-compose jest zainstalowany
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}docker-compose nie jest zainstalowany. Instalowanie...${NC}"
    pip install docker-compose
fi

# Tworzenie potrzebnych katalogów
mkdir -p ./data/db
mkdir -p ./uploads

# Sprawdzenie i zwolnienie potencjalnie zajętych portów
log "INFO" "Sprawdzanie i zwalnianie zajętych portów..."
free_port 3100  # Nowy port Rocket.Chat
free_port 27017 # Port MongoDB (wewnętrzny)
free_port 11434 # Port Ollama (jeśli jest w docker-compose)

# Budowanie i uruchamianie usług
log "INFO" "Uruchamianie Rocket.Chat i MongoDB..."

# Tworzymy oddzielny plik logów dla kontenerów
CONTAINER_LOG_FILE="$LOG_DIR/container_logs_$TIMESTAMP.log"
touch "$CONTAINER_LOG_FILE"
log "INFO" "Logi kontenerów będą zapisywane do: $CONTAINER_LOG_FILE"

# Uruchamiamy najpierw MongoDB, aby mieć pewność, że będzie gotowa dla RocketChat
log "INFO" "Uruchamianie MongoDB i inicjalizacja repliki..."
docker-compose up -d mongodb mongodb-init 2>&1 | tee -a "$CONTAINER_LOG_FILE"

# Wyświetlamy logi z inicjalizacji MongoDB w czasie rzeczywistym
log "INFO" "Logi inicjalizacji MongoDB:"
(docker-compose logs -f mongodb-init 2>&1 | tee -a "$CONTAINER_LOG_FILE") &
MONGO_LOGS_PID=$!

# Czekamy na inicjalizację MongoDB
log "INFO" "Oczekiwanie na inicjalizację MongoDB..."
sleep 15

# Zatrzymujemy wyświetlanie logów MongoDB
kill $MONGO_LOGS_PID 2>/dev/null

# Uruchamiamy RocketChat i pokazujemy jego logi w czasie rzeczywistym
log "INFO" "Uruchamianie Rocket.Chat..."
docker-compose up -d rocketchat 2>&1 | tee -a "$CONTAINER_LOG_FILE"
log "INFO" "Logi Rocket.Chat:"

# Zapisujemy logi RocketChat do pliku i wyświetlamy w konsoli
(docker-compose logs -f rocketchat 2>&1 | tee -a "$CONTAINER_LOG_FILE") &
ROCKETCHAT_LOGS_PID=$!

# Informacja o lokalizacji logów
log "INFO" "Logi Rocket.Chat są wyświetlane w czasie rzeczywistym i zapisywane do pliku."
log "INFO" "Naciśnij Ctrl+C, aby przerwać wyświetlanie logów, ale nie zatrzyma to usługi."

# Dajemy czas na przeglądanie logów (30 sekund) a potem kontynuujemy
sleep 30
kill $ROCKETCHAT_LOGS_PID 2>/dev/null

# Sprawdzanie statusu usług
log "INFO" "Sprawdzanie statusu usług..."
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Command}}\t{{.Service}}\t{{.CreatedAt}}\t{{.Status}}\t{{.Ports}}" 2>&1 | tee -a "$LOG_FILE"

# Oczekiwanie na pełne uruchomienie Rocket.Chat
log "INFO" "Oczekiwanie na pełne uruchomienie Rocket.Chat (port 3100)..."
MAX_RETRIES=30
RETRY=1

# Zapisujemy informacje o próbach połączenia
while ! curl -s http://localhost:3100/api/info > /dev/null; do
    log "INFO" "Próba $RETRY z $MAX_RETRIES..."
    
    # Sprawdzamy status kontenera, aby zobaczyć czy nadal działa
    CONTAINER_STATUS=$(docker-compose ps rocketchat | grep rocketchat | awk '{print $4}')
    if [[ "$CONTAINER_STATUS" != "Up" && "$CONTAINER_STATUS" != *"Up"* ]]; then
        log "ERROR" "Kontener Rocket.Chat nie jest uruchomiony. Status: $CONTAINER_STATUS"
        log "INFO" "Ostatnie logi kontenera:"
        docker-compose logs --tail 50 rocketchat 2>&1 | tee -a "$CONTAINER_LOG_FILE"
        log "ERROR" "Uruchomienie Rocket.Chat zakończyło się niepowodzeniem."
        exit 1
    fi
    
    if [ $RETRY -eq $MAX_RETRIES ]; then
        log "ERROR" "Nie można połączyć się z Rocket.Chat po $MAX_RETRIES próbach."
        log "WARN" "Sprawdź pełne logi: $CONTAINER_LOG_FILE"
        log "INFO" "Ostatnie logi kontenera:"
        docker-compose logs --tail 50 rocketchat 2>&1 | tee -a "$CONTAINER_LOG_FILE"
        log "WARN" "Możesz spróbować uruchomić Rocket.Chat ręcznie:"
        log "WARN" "cd $(pwd) && docker-compose down && docker-compose up -d"
        exit 1
    fi
    
    RETRY=$((RETRY+1))
    log "INFO" "Oczekiwanie 10 sekund..."
    sleep 10
done

# Dodaj informacje o portach dla innych usług korzystających z Rocket.Chat
log "INFO" "Zapisuję informacje o konfiguracji Rocket.Chat do pliku..."
echo "ROCKETCHAT_URL=http://localhost:3100" > "../../.env.rocketchat"
chmod 644 "../../.env.rocketchat"

# Podsumowanie uruchomienia
log "SUCCESS" "Rocket.Chat został pomyślnie uruchomiony!"
log "INFO" "URL: http://localhost:3100"
log "INFO" "Login: admin"
log "INFO" "Hasło: admin"
log "WARN" "Pamiętaj, aby zmienić domyślne hasło przy pierwszym logowaniu!"
log "INFO" "Do wiadomości:"
log "INFO" "Rocket.Chat używa teraz portu 3100 zamiast standardowego 3000"
log "INFO" "Wszystkie odniesienia do Rocket.Chat powinny używać nowego portu"
log "INFO" "Logi uruchomienia zapisane w: $LOG_FILE"
log "INFO" "Logi kontenerów zapisane w: $CONTAINER_LOG_FILE"
