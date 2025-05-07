#!/bin/bash
# Script to stop all services and free up ports used by EvoDev

# Kolory do komunikatów
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Załaduj zmienne środowiskowe
if [ -f .env ]; then
  source .env
else
  echo -e "${RED}Plik .env nie istnieje, używam wartości domyślnych.${NC}"
fi

# Lista portów używanych przez aplikację
APP_PORTS=(
  ${MONITOR_PORT:-8080}
  ${OLLAMA_PORT:-11434}
  ${ROCKETCHAT_PORT:-3100}
  ${MIDDLEWARE_PORT:-5000}
  ${MONGO_PORT:-27017}
  ${GITLAB_PORT:-8080}
  ${MAILHOG_SMTP_PORT:-1025}
  ${MAILHOG_WEB_PORT:-8025}
  ${MINIO_PORT:-9000}
  ${MINIO_CONSOLE_PORT:-9001}
  ${POSTGRES_PORT:-5432}
  ${REDIS_PORT:-6379}
  ${KEYCLOAK_PORT:-8180}
  ${ELASTICSEARCH_PORT:-9200}
  ${KIBANA_PORT:-5601}
  ${INFLUXDB_PORT:-8086}
  ${GRAFANA_PORT:-3000}
)

echo -e "${YELLOW}Zatrzymywanie wszystkich usług EvoDev...${NC}"

# Funkcja pomocnicza do zatrzymywania procesów
kill_process() {
  local pid=$1
  local name=$2
  echo -e "${GREEN}Zatrzymywanie procesu $name (PID: $pid)...${NC}"
  kill $pid 2>/dev/null || sudo kill $pid 2>/dev/null
  sleep 1
  if ps -p $pid > /dev/null 2>&1; then
    echo -e "${YELLOW}Wymuszanie zatrzymania procesu $name...${NC}"
    kill -9 $pid 2>/dev/null || sudo kill -9 $pid 2>/dev/null
  fi
}

# Funkcja do zatrzymywania Docker Compose w określonym katalogu
stop_docker_compose() {
  local dir=$1
  local file=$2
  local service_name=$3
  
  if [ ! -d "$dir" ]; then
    echo -e "${YELLOW}Katalog $dir nie istnieje, pomijam zatrzymywanie $service_name.${NC}"
    return
  fi
  
  if [ ! -f "$dir/$file" ]; then
    echo -e "${YELLOW}Plik $dir/$file nie istnieje, pomijam zatrzymywanie $service_name.${NC}"
    return
  fi
  
  echo -e "${GREEN}Zatrzymywanie kontenerów $service_name...${NC}"
  cd "$dir"
  docker-compose -f "$file" down -v || sudo docker-compose -f "$file" down -v
  cd - > /dev/null
  echo -e "${GREEN}Kontenery $service_name zatrzymane.${NC}"
}

# 1. Zatrzymaj bota Heyken jeśli działa
if [ -f ./bot.pid ]; then
  BOT_PID=$(cat ./bot.pid)
  if ps -p $BOT_PID > /dev/null; then
    echo -e "${GREEN}Zatrzymywanie bota Heyken (PID: $BOT_PID)...${NC}"
    kill_process "$BOT_PID" "Bot Heyken"
    rm ./bot.pid
    echo -e "${GREEN}Bot Heyken zatrzymany.${NC}"
  else
    echo -e "${YELLOW}Bot Heyken nie jest uruchomiony (ale plik PID istnieje).${NC}"
    rm ./bot.pid
  fi
else
  echo -e "${YELLOW}Plik bot.pid nie istnieje, sprawdzanie czy proces działa...${NC}"
  BOT_PROCESS=$(ps aux | grep "python.*simple_rocketchat_ollama_bot.py" | grep -v grep)
  if [ ! -z "$BOT_PROCESS" ]; then
    BOT_PID=$(echo "$BOT_PROCESS" | awk '{print $2}')
    echo -e "${GREEN}Znaleziono proces bota Heyken (PID: $BOT_PID), zatrzymywanie...${NC}"
    kill_process "$BOT_PID" "Bot Heyken"
    echo -e "${GREEN}Bot Heyken zatrzymany.${NC}"
  fi
fi

# 2. Zatrzymaj monitor jeśli działa
if [ -f ./monitor.pid ]; then
  MONITOR_PID=$(cat ./monitor.pid)
  if ps -p $MONITOR_PID > /dev/null; then
    echo -e "${GREEN}Zatrzymywanie monitora (PID: $MONITOR_PID)...${NC}"
    kill_process "$MONITOR_PID" "Monitor"
    rm ./monitor.pid
    echo -e "${GREEN}Monitor zatrzymany.${NC}"
  else
    echo -e "${YELLOW}Monitor nie jest uruchomiony (ale plik PID istnieje).${NC}"
    rm ./monitor.pid
  fi
else
  echo -e "${YELLOW}Plik monitora.pid nie istnieje, sprawdzanie czy proces działa...${NC}"
  MONITOR_PROCESS=$(ps aux | grep "python.*monitor/app.py" | grep -v grep)
  if [ ! -z "$MONITOR_PROCESS" ]; then
    MONITOR_PID=$(echo "$MONITOR_PROCESS" | awk '{print $2}')
    echo -e "${GREEN}Znaleziono proces monitora (PID: $MONITOR_PID), zatrzymywanie...${NC}"
    kill_process "$MONITOR_PID" "Monitor"
    echo -e "${GREEN}Monitor zatrzymany.${NC}"
  fi
fi

# 2. Zatrzymaj middleware API jeśli działa
UVICORN_PROCESS=$(ps aux | grep "uvicorn middleware-api.app:app" | grep -v grep)
if [ ! -z "$UVICORN_PROCESS" ]; then
  UVICORN_PID=$(echo "$UVICORN_PROCESS" | awk '{print $2}')
  echo -e "${GREEN}Zatrzymywanie middleware API (PID: $UVICORN_PID)...${NC}"
  kill_process "$UVICORN_PID" "Middleware API"
  echo -e "${GREEN}Middleware API zatrzymane.${NC}"
fi

# Sprawdź czy Docker i Docker Compose są dostępne
if ! command -v docker >/dev/null 2>&1; then
  echo -e "${RED}Docker nie jest zainstalowany. Pomijam zatrzymywanie kontenerów.${NC}"
  DOCKER_AVAILABLE=false
else
  DOCKER_AVAILABLE=true
  
  # Sprawdź czy Docker działa
  if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Docker nie jest uruchomiony. Próbuję uruchomić...${NC}"
    sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null
    sleep 3
    
    if ! docker info >/dev/null 2>&1; then
      echo -e "${RED}Nie można uruchomić Dockera. Pomijam zatrzymywanie kontenerów.${NC}"
      DOCKER_AVAILABLE=false
    fi
  fi
  
  # Sprawdź czy Docker Compose jest dostępny
  if ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "${RED}Docker Compose nie jest zainstalowany. Pomijam zatrzymywanie kontenerów.${NC}"
    DOCKER_AVAILABLE=false
  fi
fi

# 3. NAJPIERW zatrzymujemy wszystkie kontenery Ollama (dodane na początku aby uniknąć konfliktów)
if [ "$DOCKER_AVAILABLE" = true ]; then
  OLLAMA_CONTAINERS=$(docker ps -a --filter "name=ollama" -q)
  if [ ! -z "$OLLAMA_CONTAINERS" ]; then
    echo -e "${YELLOW}Znaleziono kontenery Ollama. Zatrzymywanie...${NC}"
    docker stop $OLLAMA_CONTAINERS 2>/dev/null || sudo docker stop $OLLAMA_CONTAINERS 2>/dev/null
    docker rm $OLLAMA_CONTAINERS 2>/dev/null || sudo docker rm $OLLAMA_CONTAINERS 2>/dev/null
    echo -e "${GREEN}Kontenery Ollama zatrzymane.${NC}"
  fi
  
  # Dodatkowo szukamy kontenerów z obrazem ollama/ollama
  OLLAMA_IMAGE_CONTAINERS=$(docker ps -a --filter "ancestor=ollama/ollama" -q)
  if [ ! -z "$OLLAMA_IMAGE_CONTAINERS" ]; then
    echo -e "${YELLOW}Znaleziono kontenery z obrazem Ollama. Zatrzymywanie...${NC}"
    docker stop $OLLAMA_IMAGE_CONTAINERS 2>/dev/null || sudo docker stop $OLLAMA_IMAGE_CONTAINERS 2>/dev/null
    docker rm $OLLAMA_IMAGE_CONTAINERS 2>/dev/null || sudo docker rm $OLLAMA_IMAGE_CONTAINERS 2>/dev/null
    echo -e "${GREEN}Kontenery z obrazem Ollama zatrzymane.${NC}"
  fi
  
  # Sprawdź czy porty Ollama są nadal używane przez jakiekolwiek kontenery
  OLLAMA_PORT=${OLLAMA_PORT:-11434}
  OLLAMA_PORT_CONTAINERS=$(docker ps -a --filter "publish=$OLLAMA_PORT" -q)
  if [ ! -z "$OLLAMA_PORT_CONTAINERS" ]; then
    echo -e "${YELLOW}Znaleziono kontenery używające portu $OLLAMA_PORT. Zatrzymywanie...${NC}"
    docker stop $OLLAMA_PORT_CONTAINERS 2>/dev/null || sudo docker stop $OLLAMA_PORT_CONTAINERS 2>/dev/null
    docker rm $OLLAMA_PORT_CONTAINERS 2>/dev/null || sudo docker rm $OLLAMA_PORT_CONTAINERS 2>/dev/null
    echo -e "${GREEN}Kontenery używające portu $OLLAMA_PORT zatrzymane.${NC}"
  fi
fi

# 4. Zatrzymaj pozostałe kontenery Docker jeśli Docker jest dostępny
if [ "$DOCKER_AVAILABLE" = true ]; then
  # Lista wszystkich znanych serwisów i ich plików konfiguracyjnych
  declare -A services=(
    ["mailserver"]="docker/mailserver:docker-compose.yml:Email Server"
    ["rocketchat-email"]="docker/rocketchat:docker-compose-email.yml:RocketChat z email"
    ["rocketchat-new"]="docker/rocketchat:docker-compose-new.yml:RocketChat nowy"
    ["rocketchat"]="docker/rocketchat:docker-compose.yml:RocketChat"
    ["gitlab"]="docker/gitlab:docker-compose.yml:GitLab"
    ["keycloak"]="docker/keycloak:docker-compose.yml:Keycloak"
    ["elastic"]="docker/elastic:docker-compose.yml:Elasticsearch/Kibana"
    ["influxdb"]="docker/influxdb:docker-compose.yml:InfluxDB"
    ["grafana"]="docker/grafana:docker-compose.yml:Grafana"
    ["redis"]="docker/redis:docker-compose.yml:Redis"
    ["postgres"]="docker/postgres:docker-compose.yml:PostgreSQL"
    ["minio"]="docker/minio:docker-compose.yml:MinIO"
    ["ollama"]="docker/ollama:docker-compose.yml:Ollama Docker"
  )
  
  # Zatrzymaj każdy serwis, jeśli istnieje
  for service_key in "${!services[@]}"; do
    IFS=':' read -r dir file name <<< "${services[$service_key]}"
    stop_docker_compose "$dir" "$file" "$name"
  done
  
  # Na końcu zatrzymaj główne kontenery
  if [ -f docker-compose.yml ]; then
    echo -e "${GREEN}Zatrzymywanie głównych kontenerów Docker...${NC}"
    docker-compose down -v || sudo docker-compose down -v
    echo -e "${GREEN}Główne kontenery Docker zatrzymane.${NC}"
  else
    echo -e "${YELLOW}Plik docker-compose.yml nie istnieje, pomijam główne kontenery.${NC}"
  fi
  
  # Sprawdź czy są jakieś kontenery związane z projektem
  PROJECT_CONTAINERS=$(docker ps -a --filter "name=evodev" -q)
  if [ ! -z "$PROJECT_CONTAINERS" ]; then
    echo -e "${YELLOW}Znaleziono kontenery związane z projektem, które mogą nie być zatrzymane...${NC}"
    echo -e "${GREEN}Zatrzymuję pozostałe kontenery związane z projektem...${NC}"
    docker stop $PROJECT_CONTAINERS 2>/dev/null || sudo docker stop $PROJECT_CONTAINERS 2>/dev/null
    docker rm $PROJECT_CONTAINERS 2>/dev/null || sudo docker rm $PROJECT_CONTAINERS 2>/dev/null
    echo -e "${GREEN}Kontenery związane z projektem zatrzymane.${NC}"
  fi
fi

# 5. Sprawdź i zabij wszystkie instancje Ollama (uruchomione poza dockerem)
echo -e "${YELLOW}Sprawdzanie procesów Ollama...${NC}"

# Zmienne
OLLAMA_PORT=${OLLAMA_PORT:-11434}

# Znajdź wszystkie procesy Ollama
OLLAMA_PROCESSES=$(ps aux | grep -E "ollama|/usr/local/bin/ollama|/usr/bin/ollama" | grep -v grep)
if [ ! -z "$OLLAMA_PROCESSES" ]; then
  echo -e "${YELLOW}Znaleziono procesy Ollama. Zatrzymywanie...${NC}"
  echo "$OLLAMA_PROCESSES" | while read line; do
    PID=$(echo "$line" | awk '{print $2}')
    PROCESS_NAME=$(echo "$line" | awk '{print $11}')
    kill_process "$PID" "$PROCESS_NAME"
  done
fi

# Sprawdź czy port Ollama jest nadal zajęty
OLLAMA_PORT_PIDS=$(lsof -i:$OLLAMA_PORT -t 2>/dev/null || echo "")
if [ ! -z "$OLLAMA_PORT_PIDS" ]; then
  for PID in $OLLAMA_PORT_PIDS; do
    PROCESS_NAME=$(ps -p $PID -o comm= 2>/dev/null || echo "nieznany")
    kill_process "$PID" "$PROCESS_NAME"
  done
fi

# Ostateczna próba dla usługi systemowej
if lsof -i:$OLLAMA_PORT -t >/dev/null 2>&1; then
  echo -e "${RED}Port Ollama nadal zajęty! Próba zatrzymania usługi Ollama...${NC}"
  sudo systemctl stop ollama 2>/dev/null || true
  sudo service ollama stop 2>/dev/null || true
  sleep 2
  
  # Ostateczne rozwiązanie
  if lsof -i:$OLLAMA_PORT -t >/dev/null 2>&1; then
    echo -e "${RED}Wymuszam zwolnienie portu $OLLAMA_PORT...${NC}"
    sudo fuser -k $OLLAMA_PORT/tcp 2>/dev/null || true
    sleep 2
  fi
fi

# Weryfikacja czy port został zwolniony
if lsof -i:$OLLAMA_PORT -t >/dev/null 2>&1; then
  echo -e "${RED}UWAGA: Port $OLLAMA_PORT nadal zajęty! Uruchomienie Dockera może nie być możliwe.${NC}"
else
  echo -e "${GREEN}Port $OLLAMA_PORT został zwolniony.${NC}"
fi

# 6. Sprawdź czy nie ma żadnych kontenerów Docker Proxy blokujących porty
if [ "$DOCKER_AVAILABLE" = true ]; then
  for PORT in "${APP_PORTS[@]}"; do
    PROXY_PIDS=$(ps aux | grep -E "docker-proxy.*:$PORT" | grep -v grep | awk '{print $2}')
    if [ ! -z "$PROXY_PIDS" ]; then
      echo -e "${YELLOW}Znaleziono procesy docker-proxy na porcie $PORT. Zatrzymywanie...${NC}"
      for PID in $PROXY_PIDS; do
        kill_process "$PID" "docker-proxy"
      done
    fi
  done
fi

# 7. Sprawdź i zabij procesy używające określonych portów
for PORT in "${APP_PORTS[@]}"; do
  # Pomijamy Ollama, bo już się tym zajęliśmy
  if [ "$PORT" = "$OLLAMA_PORT" ]; then
    continue
  fi
  
  echo -e "${YELLOW}Sprawdzanie procesów używających port $PORT...${NC}"
  
  # Spróbuj znaleźć procesy nasłuchujące na danym porcie
  PORT_PIDS=$(lsof -i :$PORT -t 2>/dev/null || echo "")
  
  if [ ! -z "$PORT_PIDS" ]; then
    for PID in $PORT_PIDS; do
      PROCESS_NAME=$(ps -p $PID -o comm= 2>/dev/null || echo "nieznany")
      echo -e "${GREEN}Znaleziono proces $PROCESS_NAME (PID: $PID) używający portu $PORT, zatrzymywanie...${NC}"
      
      # Używamy naszej funkcji do zabijania procesu
      kill_process "$PID" "$PROCESS_NAME"
      
      echo -e "${GREEN}Port $PORT zwolniony.${NC}"
    done
  else
    echo -e "${GREEN}Nie znaleziono procesów używających portu $PORT.${NC}"
  fi
done

# 8. Cleanup sieci Docker
if [ "$DOCKER_AVAILABLE" = true ]; then
  echo -e "${YELLOW}Czyszczenie nieużywanych sieci Docker...${NC}"
  docker network prune -f >/dev/null 2>&1
  
  # Dodatkowe sprzątanie Docker
  echo -e "${YELLOW}Czyszczenie nieużywanych wolumenów Docker...${NC}"
  docker volume prune -f >/dev/null 2>&1
fi

# 9. Usuń pliki tymczasowe
echo -e "${GREEN}Usuwanie plików tymczasowych...${NC}"
rm -f nohup.out monitor.log 2>/dev/null

echo -e "\n${GREEN}Wszystkie usługi EvoDev zostały zatrzymane i porty zwolnione.${NC}"
echo -e "${GREEN}Możesz bezpiecznie uruchomić aplikację ponownie.${NC}"

# 10. Dodatkowa weryfikacja czy wszystkie porty są faktycznie zwolnione
echo -e "\n${YELLOW}Weryfikacja zwolnienia portów:${NC}"
BUSY_PORTS=""
for PORT in "${APP_PORTS[@]}"; do
  if lsof -i:$PORT -t >/dev/null 2>&1; then
    BUSY_PORTS="$BUSY_PORTS $PORT"
  fi
done

if [ ! -z "$BUSY_PORTS" ]; then
  echo -e "${RED}UWAGA: Następujące porty są nadal zajęte:$BUSY_PORTS${NC}"
  echo -e "${YELLOW}Może to powodować problemy przy ponownym uruchomieniu usług.${NC}"
  echo -e "${YELLOW}Spróbuj uruchomić ten skrypt ponownie lub ręcznie zwolnić te porty.${NC}"
else
  echo -e "${GREEN}Wszystkie porty zostały pomyślnie zwolnione!${NC}"
fi