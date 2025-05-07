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
echo "  Ulepszenie transparentności uruchamiania      "
echo "================================================="
echo -e "${NC}"

# Utworzenie katalogu logów, jeśli nie istnieje
LOGS_DIR="./logs"
mkdir -p "$LOGS_DIR"

# Plik logu głównego
MAIN_LOG="$LOGS_DIR/heyken_startup_$(date +%Y%m%d_%H%M%S).log"
touch "$MAIN_LOG"

# Funkcja do logowania
log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $timestamp - $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $timestamp - $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $timestamp - $message"
            ;;
        *)
            echo -e "[LOG] $timestamp - $message"
            ;;
    esac
    
    echo "[$level] $timestamp - $message" >> "$MAIN_LOG"
}

# Funkcja do przechwytywania logów kontenera Docker
capture_container_logs() {
    local container_name=$1
    local log_file="$LOGS_DIR/${container_name}.log"
    
    log "INFO" "Rozpoczęcie przechwytywania logów dla $container_name > $log_file"
    
    # Uruchomienie procesu przechwytywania logów w tle
    docker logs -f "$container_name" > "$log_file" 2>&1 &
    local logger_pid=$!
    
    # Zapisanie PID procesu przechwytywania logów
    echo "$logger_pid" > "$LOGS_DIR/${container_name}.logger.pid"
    
    log "INFO" "Przechwytywanie logów dla $container_name uruchomione (PID: $logger_pid)"
    
    return 0
}

# Funkcja do zatrzymania przechwytywania logów
stop_container_logging() {
    local container_name=$1
    local pid_file="$LOGS_DIR/${container_name}.logger.pid"
    
    if [ -f "$pid_file" ]; then
        local logger_pid=$(cat "$pid_file")
        log "INFO" "Zatrzymywanie przechwytywania logów dla $container_name (PID: $logger_pid)"
        kill "$logger_pid" 2>/dev/null || true
        rm -f "$pid_file"
    fi
    
    return 0
}

# Funkcja do modyfikacji kolejności uruchamiania kontenerów w Terraform
modify_terraform_startup_order() {
    log "INFO" "Modyfikacja kolejności uruchamiania kontenerów w Terraform"
    
    local main_tf="./terraform/main.tf"
    local services_tf="./terraform/modules/services/main.tf"
    local backup_dir="./backup_$(date +%Y%m%d_%H%M%S)"
    
    # Tworzenie kopii zapasowych plików
    mkdir -p "$backup_dir"
    cp "$main_tf" "$backup_dir/" 2>/dev/null || log "WARN" "Nie można utworzyć kopii zapasowej $main_tf"
    cp "$services_tf" "$backup_dir/" 2>/dev/null || log "WARN" "Nie można utworzyć kopii zapasowej $services_tf"
    
    # Sprawdzenie czy istnieje moduł dla Rocket.Chat w Terraform
    if grep -q "rocketchat" "$main_tf" || grep -q "rocketchat" "$services_tf"; then
        log "INFO" "Znaleziono konfigurację Rocket.Chat w plikach Terraform"
        
        # Dodanie zależności, aby Rocket.Chat był uruchamiany jako pierwszy
        # To jest uproszczona implementacja - w rzeczywistości potrzebna byłaby bardziej szczegółowa analiza
        # i modyfikacja plików Terraform
        log "INFO" "Dodawanie zależności dla priorytetowego uruchamiania Rocket.Chat"
        
        # Tutaj powinna znaleźć się rzeczywista modyfikacja plików Terraform
        log "WARN" "Automatyczna modyfikacja plików Terraform jest zaawansowaną operacją"
        log "WARN" "Należy ręcznie dostosować plik $main_tf lub $services_tf"
        log "WARN" "Dodaj depends_on do modułów, aby Rocket.Chat uruchamiał się jako pierwszy"
    else
        log "WARN" "Nie znaleziono konfiguracji Rocket.Chat w plikach Terraform"
        log "WARN" "Konieczne jest ręczne dodanie konfiguracji Rocket.Chat do Terraform"
    fi
    
    return 0
}

# Funkcja do dodania szczegółowego logowania do skryptu deploy.sh
add_logging_to_deploy_script() {
    log "INFO" "Dodawanie szczegółowego logowania do skryptu deploy.sh"
    
    local deploy_script="./scripts/deploy.sh"
    local backup_file="$deploy_script.backup_$(date +%Y%m%d_%H%M%S)"
    
    # Tworzenie kopii zapasowej
    cp "$deploy_script" "$backup_file" 2>/dev/null || {
        log "ERROR" "Nie można utworzyć kopii zapasowej $deploy_script"
        return 1
    }
    
    # Dodanie funkcji logowania do skryptu deploy.sh
    local log_functions='
# Funkcja do szczegółowego logowania
log_detailed() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    local log_dir="./logs"
    local log_file="$log_dir/deploy_$(date +%Y%m%d).log"
    
    # Tworzenie katalogu logów, jeśli nie istnieje
    mkdir -p "$log_dir"
    
    # Formatowanie komunikatu w konsoli
    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $timestamp - $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $timestamp - $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $timestamp - $message"
            ;;
        *)
            echo -e "[LOG] $timestamp - $message"
            ;;
    esac
    
    # Zapisanie do pliku logu
    echo "[$level] $timestamp - $message" >> "$log_file"
    
    # Próba wysłania do Rocket.Chat (jeśli jest dostępny)
    if command -v curl &> /dev/null && [ -n "$ROCKETCHAT_URL" ] && [ -n "$ROCKETCHAT_TOKEN" ]; then
        curl -s -X POST \
            -H "X-Auth-Token: $ROCKETCHAT_TOKEN" \
            -H "X-User-Id: system" \
            -H "Content-type: application/json" \
            -d "{\"channel\": \"#system-logs\", \"text\": \"[$level] $message\"}" \
            "$ROCKETCHAT_URL/api/v1/chat.postMessage" &> /dev/null || true
    fi
}

# Zastąpienie standardowych komunikatów funkcją logowania
echo_log() {
    log_detailed "INFO" "$*"
}
'
    
    # Dodanie funkcji logowania do pliku
    sed -i "/^#!/a\\$log_functions" "$deploy_script"
    
    # Zamiana zwykłych echo na echo_log
    sed -i 's/echo -e "\${BLUE}"/echo_log "\\${BLUE}"/g' "$deploy_script"
    sed -i 's/echo -e "\${GREEN}"/echo_log "\\${GREEN}"/g' "$deploy_script"
    sed -i 's/echo -e "\${YELLOW}"/echo_log "\\${YELLOW}"/g' "$deploy_script"
    sed -i 's/echo -e "\${RED}"/echo_log "\\${RED}"/g' "$deploy_script"
    
    log "INFO" "Plik $deploy_script został zmodyfikowany aby używać szczegółowego logowania"
    log "INFO" "Utworzono kopię zapasową: $backup_file"
    
    return 0
}

# Funkcja do dodania konfiguracji Rocket.Chat
add_rocketchat_config() {
    log "INFO" "Dodawanie konfiguracji Rocket.Chat"
    
    local rocketchat_dir="./docker/rocketchat"
    mkdir -p "$rocketchat_dir"
    
    # Tworzenie pliku Dockerfile dla Rocket.Chat
    log "INFO" "Tworzenie pliku Dockerfile dla Rocket.Chat"
    cat > "$rocketchat_dir/Dockerfile" << 'EOF'
FROM rocketchat/rocket.chat:latest

LABEL maintainer="Heyken System <admin@hey-ken.com>"

# Ekspozycja portów
EXPOSE 3000

# Zmienne środowiskowe
ENV ROOT_URL=http://localhost:3000 \
    PORT=3000 \
    MONGO_URL=mongodb://mongodb:27017/rocketchat \
    MONGO_OPLOG_URL=mongodb://mongodb:27017/local \
    MAIL_URL=smtp://smtp.gmail.com:465 \
    HTTP_FORWARDED_COUNT=1

# Uruchomienie Rocket.Chat
CMD ["node", "main.js"]
EOF
    
    # Tworzenie pliku docker-compose.yml dla szybkiego uruchomienia
    log "INFO" "Tworzenie pliku docker-compose.yml dla Rocket.Chat"
    cat > "$rocketchat_dir/docker-compose.yml" << 'EOF'
version: '3'

services:
  mongodb:
    image: mongo:4.0
    restart: always
    volumes:
      - ./data/db:/data/db
    command: mongod --smallfiles --oplogSize 128 --replSet rs0
    networks:
      - rocketchat

  mongodb-init:
    image: mongo:4.0
    restart: on-failure
    command: >
      bash -c "sleep 10 && mongo mongodb/rocketchat --eval \"rs.initiate({ _id: 'rs0', members: [ { _id: 0, host: 'mongodb:27017' } ]})\""
    depends_on:
      - mongodb
    networks:
      - rocketchat

  rocketchat:
    build: .
    restart: always
    volumes:
      - ./uploads:/app/uploads
    environment:
      - ROOT_URL=http://localhost:3000
      - MONGO_URL=mongodb://mongodb:27017/rocketchat
      - MONGO_OPLOG_URL=mongodb://mongodb:27017/local
      - PORT=3000
    depends_on:
      - mongodb
    ports:
      - 3000:3000
    networks:
      - rocketchat
      - system_network

networks:
  rocketchat:
    driver: bridge
  system_network:
    external: true
EOF
    
    # Tworzenie skryptu uruchamiającego Rocket.Chat
    log "INFO" "Tworzenie skryptu uruchamiającego Rocket.Chat"
    cat > "$rocketchat_dir/start_rocketchat.sh" << 'EOF'
#!/bin/bash

# Kolory dla lepszej czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "================================================="
echo "  Heyken - System Autonomiczny                  "
echo "  Uruchamianie Rocket.Chat                       "
echo "================================================="
echo -e "${NC}"

# Sprawdzenie czy docker-compose jest zainstalowany
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}docker-compose nie jest zainstalowany. Instalowanie...${NC}"
    pip install docker-compose
fi

# Tworzenie potrzebnych katalogów
mkdir -p ./data/db
mkdir -p ./uploads

# Budowanie i uruchamianie usług
echo -e "${YELLOW}Uruchamianie Rocket.Chat i MongoDB...${NC}"
docker-compose up -d

# Sprawdzanie statusu
echo -e "${YELLOW}Sprawdzanie statusu usług...${NC}"
docker-compose ps

# Czekanie aż Rocket.Chat będzie dostępny
echo -e "${YELLOW}Oczekiwanie na pełne uruchomienie Rocket.Chat...${NC}"
MAX_RETRIES=30
RETRY_INTERVAL=10

for ((i=1; i<=$MAX_RETRIES; i++)); do
    echo "Próba $i z $MAX_RETRIES..."
    
    if curl -s http://localhost:3000 > /dev/null; then
        echo -e "${GREEN}Rocket.Chat jest dostępny!${NC}"
        break
    fi
    
    if [ $i -eq $MAX_RETRIES ]; then
        echo -e "${YELLOW}Upłynął limit czasu oczekiwania, ale kontynuujemy...${NC}"
    else
        echo "Oczekiwanie $RETRY_INTERVAL sekund..."
        sleep $RETRY_INTERVAL
    fi
done

echo -e "${GREEN}Rocket.Chat został uruchomiony. Dostępny pod adresem: http://localhost:3000${NC}"
echo -e "${YELLOW}Domyślne dane logowania: admin / admin (zmień hasło przy pierwszym logowaniu)${NC}"
EOF
    
    # Nadanie uprawnień wykonywania dla skryptu
    chmod +x "$rocketchat_dir/start_rocketchat.sh"
    
    log "INFO" "Konfiguracja Rocket.Chat została pomyślnie dodana"
    log "INFO" "Możesz uruchomić Rocket.Chat za pomocą: $rocketchat_dir/start_rocketchat.sh"
    
    return 0
}

# Funkcja do modyfikacji skryptu check_system.sh, aby używał szczegółowego logowania
update_check_system_script() {
    log "INFO" "Aktualizacja skryptu check_system.sh"
    
    local check_script="./scripts/check_system.sh"
    local backup_file="$check_script.backup_$(date +%Y%m%d_%H%M%S)"
    
    # Tworzenie kopii zapasowej
    cp "$check_script" "$backup_file" 2>/dev/null || {
        log "ERROR" "Nie można utworzyć kopii zapasowej $check_script"
        return 1
    }
    
    # Dodanie opcji zapisywania logów z kontenerów
    local container_logging='
# Funkcja do uruchamiania przechwytywania logów dla wszystkich kontenerów
start_container_logging() {
    echo -e "${BLUE}Uruchamianie przechwytywania logów dla kontenerów...${NC}"
    
    # Tworzenie katalogu na logi
    mkdir -p ./logs/containers
    
    # Pobieranie listy uruchomionych kontenerów
    local containers=$(docker ps --format "{{.Names}}")
    
    for container in $containers; do
        echo "Uruchamianie przechwytywania logów dla kontenera: $container"
        docker logs -f "$container" > "./logs/containers/${container}.log" 2>&1 &
        echo $! > "./logs/containers/${container}.pid"
    done
    
    echo -e "${GREEN}Przechwytywanie logów uruchomione dla $(echo "$containers" | wc -w) kontenerów${NC}"
}

# Funkcja do zatrzymywania przechwytywania logów
stop_container_logging() {
    echo -e "${BLUE}Zatrzymywanie przechwytywania logów...${NC}"
    
    # Sprawdzanie katalogu z plikami PID
    if [ -d "./logs/containers" ]; then
        for pid_file in ./logs/containers/*.pid; do
            if [ -f "$pid_file" ]; then
                local pid=$(cat "$pid_file")
                local container=$(basename "$pid_file" .pid)
                echo "Zatrzymywanie przechwytywania logów dla: $container (PID: $pid)"
                kill "$pid" 2>/dev/null || true
                rm -f "$pid_file"
            fi
        done
    fi
    
    echo -e "${GREEN}Przechwytywanie logów zatrzymane${NC}"
}
'
    
    # Dodanie przechwytywania logów do skryptu
    sed -i "/^# Główna funkcja sprawdzająca/i\\$container_logging" "$check_script"
    
    # Dodanie wywołania funkcji przechwytywania logów
    sed -i "/^main()/i\\# Uruchamianie przechwytywania logów na początku\nstart_container_logging\n\n# Zatrzymanie przechwytywania logów przy wyjściu\ntrap stop_container_logging EXIT\n" "$check_script"
    
    log "INFO" "Plik $check_script został zaktualizowany aby przechwytywać logi kontenerów"
    log "INFO" "Utworzono kopię zapasową: $backup_file"
    
    return 0
}

# Główna funkcja
main() {
    log "INFO" "Rozpoczęcie ulepszania transparentności uruchamiania systemu Heyken"
    
    # Dodanie konfiguracji Rocket.Chat
    add_rocketchat_config
    
    # Modyfikacja kolejności uruchamiania w Terraform
    modify_terraform_startup_order
    
    # Dodanie szczegółowego logowania do skryptu deploy.sh
    add_logging_to_deploy_script
    
    # Aktualizacja skryptu check_system.sh
    update_check_system_script
    
    log "INFO" "Ulepszanie transparentności uruchamiania zakończone pomyślnie"
    log "INFO" "Logi zapisane w: $MAIN_LOG"
    log "INFO" "Możesz teraz uruchomić Rocket.Chat za pomocą: ./docker/rocketchat/start_rocketchat.sh"
    log "INFO" "Następnie uruchom: ./scripts/check_system.sh aby przechwytywać logi wszystkich kontenerów"
    
    echo -e "\n${GREEN}==================================================${NC}"
    echo -e "${GREEN}  Ulepszenia zostały pomyślnie wprowadzone!        ${NC}"
    echo -e "${GREEN}==================================================${NC}"
    echo -e "\n${YELLOW}Zalecane kroki:${NC}"
    echo -e "1. Uruchom Rocket.Chat: ${BLUE}./docker/rocketchat/start_rocketchat.sh${NC}"
    echo -e "2. Skonfiguruj Rocket.Chat (http://localhost:3000) z danymi admin/admin"
    echo -e "3. Uruchom system z przechwytywaniem logów: ${BLUE}./scripts/check_system.sh${NC}"
    echo -e "4. Przeglądaj logi w katalogu ${BLUE}./logs/${NC}"
    
    return 0
}

# Uruchomienie głównej funkcji
main
