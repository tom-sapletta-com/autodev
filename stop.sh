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
APP_PORTS=(${MONITOR_PORT:-8080} ${OLLAMA_PORT:-11434} ${ROCKETCHAT_PORT:-3000} ${MIDDLEWARE_PORT:-5000} ${MONGO_PORT:-27017})

echo -e "${YELLOW}Zatrzymywanie wszystkich usług EvoDev...${NC}"

# 1. Zatrzymaj monitor jeśli działa
if [ -f ./monitor.pid ]; then
    MONITOR_PID=$(cat ./monitor.pid)
    if ps -p $MONITOR_PID > /dev/null; then
        echo -e "${GREEN}Zatrzymywanie monitora (PID: $MONITOR_PID)...${NC}"
        kill $MONITOR_PID 2>/dev/null || sudo kill $MONITOR_PID 2>/dev/null || sudo kill -9 $MONITOR_PID 2>/dev/null
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
        kill $MONITOR_PID 2>/dev/null || sudo kill $MONITOR_PID 2>/dev/null || sudo kill -9 $MONITOR_PID 2>/dev/null
        echo -e "${GREEN}Monitor zatrzymany.${NC}"
    fi
fi

# 2. Zatrzymaj middleware API jeśli działa
UVICORN_PROCESS=$(ps aux | grep "uvicorn middleware-api.app:app" | grep -v grep)
if [ ! -z "$UVICORN_PROCESS" ]; then
    UVICORN_PID=$(echo "$UVICORN_PROCESS" | awk '{print $2}')
    echo -e "${GREEN}Zatrzymywanie middleware API (PID: $UVICORN_PID)...${NC}"
    kill $UVICORN_PID 2>/dev/null || sudo kill $UVICORN_PID 2>/dev/null || sudo kill -9 $UVICORN_PID 2>/dev/null
    echo -e "${GREEN}Middleware API zatrzymane.${NC}"
fi

# 3. Zatrzymaj kontenery Docker jeśli działają
if command -v docker-compose >/dev/null 2>&1; then
    if [ -f docker-compose.yml ]; then
        echo -e "${GREEN}Zatrzymywanie kontenerów Docker...${NC}"
        docker-compose down -v || sudo docker-compose down -v
        echo -e "${GREEN}Kontenery Docker zatrzymane.${NC}"
    else
        echo -e "${YELLOW}Plik docker-compose.yml nie istnieje.${NC}"
    fi
else
    echo -e "${RED}Docker Compose nie jest zainstalowany.${NC}"
fi

# 4. Sprawdź i zabij wszystkie instancje Ollama (uruchomione poza dockerem)
echo -e "${YELLOW}Sprawdzanie procesów Ollama...${NC}"

# Najpierw spróbuj znaleźć bezpośrednio procesy zajmujące port Ollamy
OLLAMA_PORT_PIDS=$(sudo lsof -t -i:${OLLAMA_PORT:-11434} 2>/dev/null || echo "")
if [ ! -z "$OLLAMA_PORT_PIDS" ]; then
    for PID in $OLLAMA_PORT_PIDS; do
        PROCESS_NAME=$(ps -p $PID -o comm= 2>/dev/null || echo "nieznany")
        echo -e "${YELLOW}Zatrzymywanie procesu $PROCESS_NAME (PID: $PID) używającego portu Ollama...${NC}"
        sudo kill $PID 2>/dev/null
        sleep 1
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}Wymuszanie zatrzymania procesu $PROCESS_NAME...${NC}"
            sudo kill -9 $PID 2>/dev/null
            sleep 1
        fi
    done
fi

# Dodatkowo szukanie po nazwie procesu (na wypadek różnych nazw)
for PROCESS_PATTERN in "ollama" "/usr/local/bin/ollama" "/usr/bin/ollama"; do
    OLLAMA_PROCESSES=$(ps aux | grep "$PROCESS_PATTERN" | grep -v grep | awk '{print $2}')
    if [ ! -z "$OLLAMA_PROCESSES" ]; then
        echo -e "${YELLOW}Znaleziono procesy Ollama. Zatrzymywanie...${NC}"
        for PID in $OLLAMA_PROCESSES; do
            echo -e "${GREEN}Zatrzymywanie procesu Ollama (PID: $PID)...${NC}"
            sudo kill $PID 2>/dev/null
            sleep 1
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "${YELLOW}Wymuszanie zatrzymania procesu Ollama...${NC}"
                sudo kill -9 $PID 2>/dev/null
            fi
        done
    fi
done

# Ostateczna próba ze specjalną obsługą dla użytkownika "ollama"
if sudo lsof -i:${OLLAMA_PORT:-11434} > /dev/null 2>&1; then
    echo -e "${RED}Port Ollama nadal zajęty! Próba zatrzymania usługi Ollama...${NC}"
    sudo systemctl stop ollama 2>/dev/null || true
    sudo service ollama stop 2>/dev/null || true
    
    # Ostateczne rozwiązanie
    echo -e "${RED}Wymuszam zwolnienie portu ${OLLAMA_PORT:-11434}...${NC}"
    sudo fuser -k ${OLLAMA_PORT:-11434}/tcp 2>/dev/null || true
    sleep 2
fi

# Weryfikacja czy port został zwolniony
if sudo lsof -i:${OLLAMA_PORT:-11434} > /dev/null 2>&1; then
    echo -e "${RED}UWAGA: Port ${OLLAMA_PORT:-11434} nadal zajęty! Uruchomienie Dockera może nie być możliwe.${NC}"
else
    echo -e "${GREEN}Port ${OLLAMA_PORT:-11434} został zwolniony.${NC}"
fi

# 5. Sprawdź i zabij procesy używające określonych portów
for PORT in "${APP_PORTS[@]}"; do
    echo -e "${YELLOW}Sprawdzanie procesów używających port $PORT...${NC}"
    
    # Spróbuj znaleźć procesy nasłuchujące na danym porcie
    PORT_PIDS=$(lsof -i :$PORT -t 2>/dev/null || echo "")
    
    if [ ! -z "$PORT_PIDS" ]; then
        for PID in $PORT_PIDS; do
            PROCESS_NAME=$(ps -p $PID -o comm= 2>/dev/null || echo "nieznany")
            echo -e "${GREEN}Znaleziono proces $PROCESS_NAME (PID: $PID) używający portu $PORT, zatrzymywanie...${NC}"
            
            # Próbuj zatrzymać proces z różnym poziomem drastyczności
            kill $PID 2>/dev/null || sudo kill $PID 2>/dev/null
            
            # Poczekaj chwilę i sprawdź czy proces nadal działa
            sleep 1
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "${YELLOW}Wymuszenie zatrzymania procesu $PROCESS_NAME (PID: $PID)...${NC}"
                kill -9 $PID 2>/dev/null || sudo kill -9 $PID 2>/dev/null
            fi
            
            echo -e "${GREEN}Port $PORT zwolniony.${NC}"
        done
    else
        echo -e "${GREEN}Nie znaleziono procesów używających portu $PORT.${NC}"
    fi
done

# 6. Usuń pliki tymczasowe
echo -e "${GREEN}Usuwanie plików tymczasowych...${NC}"
rm -f nohup.out monitor.log 2>/dev/null

echo -e "\n${GREEN}Wszystkie usługi EvoDev zostały zatrzymane i porty zwolnione.${NC}"
echo -e "${GREEN}Możesz bezpiecznie uruchomić aplikację ponownie.${NC}"
