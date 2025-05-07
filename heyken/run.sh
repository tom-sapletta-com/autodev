#!/bin/bash

# Kolory do komunikatów
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ładowanie zmiennych środowiskowych z pliku .env
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

# Funkcja do otwierania przeglądarki
open_browser() {
  local url="$1"
  echo -e "${GREEN}Otwieram przeglądarkę: $url${NC}"
  
  # Wykryj system operacyjny i otwórz URL w przeglądarce
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v xdg-open &>/dev/null; then
      xdg-open "$url" &>/dev/null &
    elif command -v gnome-open &>/dev/null; then
      gnome-open "$url" &>/dev/null &
    else
      echo -e "${YELLOW}Nie można automatycznie otworzyć przeglądarki. Otwórz ręcznie URL: $url${NC}"
      return 1
    fi
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    open "$url" &>/dev/null &
  elif [[ "$OSTYPE" == "cygwin" || "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    start "" "$url" &>/dev/null &
  else
    echo -e "${YELLOW}Nieobsługiwany system. Otwórz ręcznie URL: $url${NC}"
    return 1
  fi
  
  # Daj czas przeglądarce na otwarcie
  sleep 3
  return 0
}

# Funkcja do wyświetlania widoku logów w przeglądarce
view_logs_in_browser() {
  local logs_url="http://localhost:${MONITOR_PORT:-8080}/logs"
  echo -e "${GREEN}Otwieram widok logów w przeglądarce...${NC}"
  open_browser "$logs_url"
  return 0
}

# Funkcja do instalacji pakietów
install_package() {
  local package_name=$1
  local check_command=$2
  
  # Sprawdź czy pakiet jest już zainstalowany
  if command -v $check_command &>/dev/null || $check_command --version &>/dev/null 2>&1; then
    echo -e "${GREEN}OK: $package_name już zainstalowany.${NC}"
    return 0
  fi
  
  echo -e "${YELLOW}Instaluję brakującą zależność: $package_name${NC}"
  echo -e "${YELLOW}UWAGA: Do instalacji $package_name wymagane są uprawnienia administratora.${NC}"
  echo -e "${YELLOW}Zostaniesz poproszony o podanie hasła sudo.${NC}"
  
  # Daj użytkownikowi czas na przeczytanie komunikatu
  sleep 1
  
  if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install $package_name || return 1
  elif [ -f /etc/debian_version ]; then
    sudo apt-get update && sudo apt-get install -y $package_name || return 1
  elif [ -f /etc/redhat-release ]; then
    sudo dnf install -y $package_name 2>/dev/null || sudo yum install -y $package_name || {
      if [ "$package_name" = "terraform" ]; then
        # Alternatywna instalacja Terraform przez pobranie binarki
        echo -e "${YELLOW}Instaluję Terraform z binarki...${NC}"
        T_VERSION="1.8.5"
        ARCH=$(uname -m)
        case "$ARCH" in
          x86_64) ARCH=amd64 ;;
          aarch64) ARCH=arm64 ;;
        esac
        OS=$(uname | tr '[:upper:]' '[:lower:]')
        URL="https://releases.hashicorp.com/terraform/${T_VERSION}/terraform_${T_VERSION}_${OS}_${ARCH}.zip"
        TMPFILE=$(mktemp)
        echo -e "Pobieram Terraform z ${URL}..."
        curl -o "$TMPFILE" -fsSL "$URL" && unzip -o "$TMPFILE" -d /tmp && sudo mv /tmp/terraform /usr/local/bin/ && rm "$TMPFILE" || return 1
      elif [ "$package_name" = "python3-pip" ]; then
        # Alternatywna instalacja pip przez get-pip.py
        echo -e "${YELLOW}Instaluję pip przez get-pip.py...${NC}"
        curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        python3 /tmp/get-pip.py --user || return 1
        rm /tmp/get-pip.py
      else
        echo -e "${RED}Nie można zainstalować $package_name!${NC}"
        return 1
      fi
    }
  else
    echo -e "${RED}Nieobsługiwany system! Zainstaluj $package_name ręcznie.${NC}"
    return 1
  fi
  
  echo -e "${GREEN}Pakiet $package_name został zainstalowany.${NC}"
  return 0
}

# Uruchomienie monitora jako proces w tle
start_monitor() {
  echo -e "${GREEN}Uruchamianie monitora EvoDev...${NC}"
  
  # Sprawdź czy monitor już działa
  local MONITOR_PORT=${MONITOR_PORT:-8080}
  local MONITOR_RUNNING=false
  
  # Sprawdź czy port monitora jest używany
  if lsof -i :$MONITOR_PORT -t >/dev/null 2>&1; then
    # Sprawdź czy to nasz monitor z PID
    if [ -f ./monitor.pid ] && ps -p $(cat ./monitor.pid) >/dev/null 2>&1; then
      echo -e "${YELLOW}Monitor już działa na porcie $MONITOR_PORT (PID: $(cat ./monitor.pid))${NC}"
      MONITOR_RUNNING=true
    else
      echo -e "${YELLOW}Port $MONITOR_PORT jest zajęty przez inny proces.${NC}"
      echo -e "${YELLOW}Próbuję znaleźć wolny port...${NC}"
      
      # Znajdź wolny port
      local PORT=8081
      while lsof -i :$PORT -t >/dev/null 2>&1 && [ $PORT -lt 8100 ]; do
        ((PORT++))
      done
      
      if [ $PORT -lt 8100 ]; then
        echo -e "${YELLOW}Znaleziono wolny port: $PORT${NC}"
        MONITOR_PORT=$PORT
      else
        echo -e "${RED}Nie można znaleźć wolnego portu!${NC}"
        echo -e "${RED}Zatrzymaj istniejące procesy na portach 8080-8099 i spróbuj ponownie.${NC}"
        return 1
      fi
    fi
  fi
  
  # 3. Uruchom monitor jeśli nie działa
  if [ "$MONITOR_RUNNING" = false ]; then
    # Instaluj zależności
    echo -e "Instalacja zależności monitora..."
    pip install -q -r ./monitor/requirements.txt || {
      echo -e "${RED}Nie można zainstalować zależności monitora!${NC}"
      return 1
    }
    
    # Uruchom monitor w tle
    echo -e "${GREEN}Uruchamianie monitora na porcie ${MONITOR_PORT:-8080}...${NC}"
    (cd monitor && python app.py > ../monitor.log 2>&1) &
    MONITOR_PID=$!
    
    # Zapisz PID do pliku
    echo $MONITOR_PID > ./monitor.pid
    
    # Sprawdź czy proces uruchomił się poprawnie
    sleep 2
    if ! ps -p $MONITOR_PID >/dev/null 2>&1; then
      echo -e "${RED}Nie udało się uruchomić monitora!${NC}"
      echo -e "${YELLOW}Sprawdź logi w pliku monitor.log${NC}"
      return 1
    fi
  fi
  
  # 4. Ostateczna weryfikacja czy monitor faktycznie działa
  if ! curl -s -f http://localhost:${MONITOR_PORT:-8080}/health >/dev/null 2>&1; then
    echo -e "${RED}Monitor nie odpowiada na port ${MONITOR_PORT:-8080}!${NC}"
    echo -e "${YELLOW}Sprawdź logi w pliku monitor.log${NC}"
    return 1
  fi
  
  # 5. Otwórz przeglądarkę
  local monitor_url="http://localhost:${MONITOR_PORT:-8080}"
  echo -e "${GREEN}Monitor uruchomiony na: ${monitor_url}${NC}"
  
  # Nie musimy automatycznie otwierać przeglądarki, użytkownik może to zrobić ręcznie
  # lub wybrać opcję "--logs" aby zobaczyć widok logów
  return 0
}

# Instalacja wymaganych pakietów systemowych
install_requirements() {
  # Lista zależności
  install_package docker docker
  install_package docker-compose docker-compose
  install_package terraform terraform
  install_package ansible ansible
  install_package python3-pip pip3
  
  # Pip na pewno
  if ! command -v pip3 >/dev/null 2>&1; then
    echo -e "${RED}Pip nadal nie jest zainstalowany! Spróbuj zainstalować ręcznie python3-pip.${NC}"
    install_package python3-pip pip3
  fi
  
  return 0
}

# Główna funkcja uruchamiająca system
main() {
  # 0. Najpierw zatrzymaj wszystkie usługi, aby uniknąć konfliktów portów
  echo -e "${YELLOW}Zatrzymywanie wszystkich usług przed uruchomieniem...${NC}"
  ./stop.sh
  echo -e "${GREEN}Wszystkie usługi zostały zatrzymane. Rozpoczynam uruchamianie...${NC}"
  
  # 1. Instalacja wymaganych pakietów
  install_requirements
  
  # 2. Pomijamy uruchomienie monitora, ponieważ brakuje plików konfiguracyjnych
  echo -e "${YELLOW}Pomijam uruchomienie monitora (brak plików konfiguracyjnych).${NC}"
  
  # 3. Dodaj opcję wyświetlania logów w przeglądarce
  if [ "$1" == "--logs" ] || [ "$1" == "-l" ]; then
    view_logs_in_browser
    exit 0
  fi
  
  # 4. Uruchomienie RocketChat
  echo -e "${GREEN}Uruchamianie RocketChat...${NC}"
  if [ -f docker/rocketchat/docker-compose-new.yml ]; then
    cd docker/rocketchat
    docker-compose -f docker-compose-new.yml up -d
    cd ../..
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}RocketChat uruchomiony na porcie 3100.${NC}"
      
      # Czekaj na uruchomienie RocketChat
      echo -e "${YELLOW}Oczekiwanie na uruchomienie RocketChat...${NC}"
      MAX_ATTEMPTS=30
      ATTEMPT=0
      ROCKETCHAT_READY=false
      
      while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        echo -n "."
        # Próba połączenia z RocketChat
        if curl -s http://localhost:3100 > /dev/null; then
          echo -e "\n${GREEN}RocketChat jest gotowy!${NC}"
          ROCKETCHAT_READY=true
          break
        fi
        ATTEMPT=$((ATTEMPT+1))
        sleep 5
      done
      
      if [ "$ROCKETCHAT_READY" = true ]; then
        # Konfiguracja RocketChat
        echo -e "${GREEN}Konfigurowanie RocketChat...${NC}"
        cd scripts
        ./setup_rocketchat.sh
        cd ..
        if [ $? -eq 0 ]; then
          echo -e "${GREEN}RocketChat skonfigurowany pomyślnie.${NC}"
          echo -e "${GREEN}Możesz zalogować się jako: user / user123${NC}"
        else
          echo -e "${YELLOW}Wystąpiły problemy z konfiguracją RocketChat, ale kontynuujemy...${NC}"
        fi
      else
        echo -e "${YELLOW}RocketChat nie odpowiada, ale kontynuujemy...${NC}"
      fi
    else
      echo -e "${RED}Błąd podczas uruchamiania RocketChat!${NC}"
    fi
  else
    echo -e "${YELLOW}Brak pliku konfiguracyjnego RocketChat. Pomijam uruchomienie RocketChat.${NC}"
  fi
  
  # 5. Uruchomienie pozostałych usług docker-compose
  if [ -f docker-compose.yml ]; then
    echo -e "${GREEN}Uruchamianie pozostałych usług przez Docker Compose...${NC}"
    docker-compose up -d
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}Usługi docker-compose uruchomione.${NC}"
    else
      echo -e "${RED}Błąd podczas uruchamiania docker-compose!${NC}"
    fi
  else
    echo -e "${YELLOW}Plik docker-compose.yml nie istnieje. Pomijam uruchomienie głównych usług.${NC}"
  fi
  
  # 6. Pobieranie modelu Ollama i uruchomienie kontenera
  echo -e "${GREEN}Przygotowywanie modelu Ollama...${NC}"
  
  # Zatrzymaj kontener Ollama jeśli działa
  if docker ps | grep -q ollama; then
    echo -e "${YELLOW}Zatrzymuję działający kontener Ollama...${NC}"
    docker stop ollama >/dev/null 2>&1
    docker rm ollama >/dev/null 2>&1
  fi
  
  # Utwórz katalog dla modeli Ollama
  OLLAMA_MODELS_DIR="${PWD}/data/ollama"
  mkdir -p "$OLLAMA_MODELS_DIR"
  chmod -R 777 "$OLLAMA_MODELS_DIR"
  
  # Ustaw zmienną dla modelu
  OLLAMA_MODEL="llama3"
  
  # Sprawdź czy model jest już pobrany
  MODEL_DOWNLOADED=false
  if [ -d "$OLLAMA_MODELS_DIR/models" ]; then
    if find "$OLLAMA_MODELS_DIR/models" -type f -name "*$OLLAMA_MODEL*" | grep -q .; then
      echo -e "${GREEN}Model $OLLAMA_MODEL jest już dostępny lokalnie.${NC}"
      MODEL_DOWNLOADED=true
    fi
  fi
  
  # Jeśli model nie jest pobrany, pobierz go
  if [ "$MODEL_DOWNLOADED" = false ]; then
    echo -e "${YELLOW}Model $OLLAMA_MODEL nie jest dostępny lokalnie. Pobieram...${NC}"
    
    # Pobierz model bezpośrednio do katalogu
    echo -e "${YELLOW}Pobieranie modelu $OLLAMA_MODEL do katalogu $OLLAMA_MODELS_DIR...${NC}"
    
    # Sprawdź czy mamy zainstalowane Ollama CLI lokalnie
    if ! command -v ollama &> /dev/null; then
      echo -e "${YELLOW}Ollama CLI nie jest zainstalowane lokalnie. Instaluję...${NC}"
      curl -fsSL https://ollama.com/install.sh | sh
      echo -e "${GREEN}Ollama CLI zainstalowane.${NC}"
    fi
    
    # Pobierz model bezpośrednio z internetu do katalogu
    mkdir -p "$OLLAMA_MODELS_DIR/models"
    
    # Pobierz model llama3 bezpośrednio z repozytorium
    echo -e "${YELLOW}Pobieranie modelu $OLLAMA_MODEL z repozytorium...${NC}"
    curl -L https://ollama.com/library/$OLLAMA_MODEL/manifest.json -o "$OLLAMA_MODELS_DIR/models/$OLLAMA_MODEL.json"
    
    echo -e "${GREEN}Model $OLLAMA_MODEL pobrany do katalogu $OLLAMA_MODELS_DIR/models/${NC}"
  fi
  
  # Uruchom kontener Ollama z podmontowanym katalogiem modeli
  echo -e "${GREEN}Uruchamiam kontener Ollama z lokalnie pobranym modelem $OLLAMA_MODEL...${NC}"
  
  # Upewnij się, że stary kontener nie istnieje
  if docker ps -a | grep -q ollama; then
    echo -e "${YELLOW}Usuwam stary kontener Ollama...${NC}"
    docker rm -f ollama >/dev/null 2>&1
  fi
  
  # Uruchom kontener z podmontowanym katalogiem modeli
  docker run -d --name ollama \
    -p 11434:11434 \
    -v "$OLLAMA_MODELS_DIR:/root/.ollama" \
    ollama/ollama
  
  # Czekaj na uruchomienie kontenera
  echo -e "${YELLOW}Oczekiwanie na uruchomienie kontenera Ollama...${NC}"
  MAX_ATTEMPTS=30
  ATTEMPT=0
  OLLAMA_READY=false
  
  while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    echo -n "."
    if curl -s http://localhost:11434/api/tags > /dev/null; then
      echo -e "\n${GREEN}Kontener Ollama jest gotowy!${NC}"
      OLLAMA_READY=true
      break
    fi
    ATTEMPT=$((ATTEMPT+1))
    sleep 2
  done
  
  if [ "$OLLAMA_READY" = true ]; then
    echo -e "${GREEN}Ollama jest gotowe do użycia.${NC}"
  else
    echo -e "${RED}Kontener Ollama nie odpowiada, ale kontynuujemy...${NC}"
  fi
  
  # 7. Uruchomienie bota Heyken
  echo -e "${GREEN}Uruchamianie bota Heyken...${NC}"
  
  # Sprawdź czy środowisko wirtualne istnieje, jeśli nie, utwórz je
  if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Tworzenie środowiska wirtualnego...${NC}"
    python -m venv venv
  fi
  
  # Aktywuj środowisko wirtualne i zainstaluj zależności
  echo -e "${YELLOW}Instalacja zależności bota...${NC}"
  source venv/bin/activate
  pip install python-dotenv requests
  
  # Uruchom bota w tle
  echo -e "${GREEN}Uruchamianie bota w tle...${NC}"
  nohup python simple_rocketchat_ollama_bot.py > bot.log 2>&1 &
  BOT_PID=$!
  echo $BOT_PID > ./bot.pid
  echo -e "${GREEN}Bot uruchomiony (PID: $BOT_PID). Logi dostępne w pliku bot.log${NC}"
  
  # Uruchom forwarder logów Docker do RocketChat
  echo -e "${GREEN}Uruchamianie forwardera logów Docker do RocketChat...${NC}"
  chmod +x ./scripts/docker_logs_to_rocketchat.py
  nohup python ./scripts/docker_logs_to_rocketchat.py > docker_logs_forwarder.log 2>&1 &
  LOGS_FORWARDER_PID=$!
  echo $LOGS_FORWARDER_PID > ./docker_logs_forwarder.pid
  echo -e "${GREEN}Forwarder logów Docker uruchomiony (PID: $LOGS_FORWARDER_PID)${NC}"
  echo -e "${GREEN}Logi Docker będą wysyłane do kanałów #heyken-logs i #logs w RocketChat${NC}"
  
  echo -e "${GREEN}Możesz zalogować się do RocketChat (http://localhost:3100) jako: heyken_user / user123${NC}"
  echo -e "${GREEN}i wysłać wiadomość do bota heyken_bot.${NC}"
}

# Uruchom główną funkcję z przekazaniem argumentów
main "$@"
