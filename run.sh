#!/bin/bash
# Uniwersalny skrypt do uruchamiania systemu evodev na Linux/Mac/WSL
set -e

# Kolory do statusów
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Załaduj zmienne środowiskowe
if [ -f .env ]; then
  source .env
else
  echo -e "${RED}Plik .env nie istnieje, używam wartości domyślnych.${NC}"
  MONITOR_PORT=8080
fi

# Funkcja do otwierania przeglądarki (multi-platformowa)
open_browser() {
  URL=$1
  echo -e "${GREEN}Próba otwarcia przeglądarki pod adresem: $URL${NC}"
  
  # Sprawdź system operacyjny
  case "$(uname -s)" in
    Linux*)
      # Linux - sprawdź środowisko graficzne i dostępne programy
      if command -v xdg-open > /dev/null; then
        xdg-open "$URL" &>/dev/null &
      elif command -v gio > /dev/null; then
        gio open "$URL" &>/dev/null &
      elif command -v gnome-open > /dev/null; then
        gnome-open "$URL" &>/dev/null &
      else
        echo -e "${YELLOW}Nie znaleziono standardowej komendy do otwarcia przeglądarki.${NC}"
        echo -e "${GREEN}Otwórz przeglądarkę ręcznie pod adresem: $URL${NC}"
        return 1
      fi
      ;;
    Darwin*)
      # macOS
      open "$URL" &>/dev/null &
      ;;
    MINGW*|CYGWIN*|MSYS*)
      # Windows (Git Bash lub podobne)
      start "$URL" &>/dev/null &
      ;;
    *)
      # Sprawdź czy to WSL (Windows Subsystem for Linux)
      if grep -qi microsoft /proc/version 2>/dev/null; then
        # WSL
        cmd.exe /c start "$URL" &>/dev/null &
      else
        echo -e "${YELLOW}Nieznany system operacyjny. Otwórz przeglądarkę ręcznie pod adresem: $URL${NC}"
        return 1
      fi
      ;;
  esac
  
  echo -e "${GREEN}Przeglądarka została otwarta (lub spróbowaliśmy ją otworzyć).${NC}"
  return 0
}

# Uruchomienie monitora jako proces w tle
start_monitor() {
  echo -e "${GREEN}Uruchamianie monitora EvoDev...${NC}"
  
  # Sprawdź czy katalog monitora istnieje
  if [ ! -d "./monitor" ]; then
    echo -e "${RED}Katalog monitora nie istnieje!${NC}"
    return 1
  fi
  
  # 1. Sprawdź czy proces monitora już działa z dowolnego PID
  MONITOR_RUNNING=false
  MONITOR_PID=""
  
  # Znajdź wszystkie procesy Python uruchamiające monitor/app.py
  # To najbardziej niezawodny sposób identyfikacji procesu niezależnie od PID
  MONITOR_PROCESS=$(ps aux | grep -i "python.*monitor/app.py" | grep -v grep)
  if [ ! -z "$MONITOR_PROCESS" ]; then
    MONITOR_RUNNING=true
    MONITOR_PID=$(echo "$MONITOR_PROCESS" | awk '{print $2}')
    echo -e "${GREEN}Monitor już działa (PID: $MONITOR_PID)${NC}"
    
    # Upewnij się że PID jest zapisany poprawnie
    echo $MONITOR_PID > ./monitor.pid
  else
    # Jeśli nie znaleziono procesu, ale istnieje plik PID, usuń go
    if [ -f ./monitor.pid ]; then
      rm ./monitor.pid
    fi
  fi
  
  # 2. Sprawdź czy port jest zajęty (jeśli monitor nie działa)
  if [ "$MONITOR_RUNNING" = false ]; then
    PORT_PID=$(lsof -ti:${MONITOR_PORT:-8080} 2>/dev/null | head -n1)
    if [ ! -z "$PORT_PID" ]; then
      echo -e "${YELLOW}Port ${MONITOR_PORT:-8080} jest zajęty przez proces PID: $PORT_PID${NC}"
      echo -e "${YELLOW}Automatyczne zwalnianie portu...${NC}"
      
      # Spróbuj zakończyć proces łagodnie
      kill $PORT_PID 2>/dev/null || sudo kill $PORT_PID 2>/dev/null
      sleep 1
      
      # Sprawdź czy proces nadal działa
      if lsof -ti:${MONITOR_PORT:-8080} >/dev/null 2>&1; then
        # Wymuś zakończenie jeśli łagodne nie zadziałało
        echo -e "${YELLOW}Wymuszam zakończenie procesu...${NC}"
        kill -9 $PORT_PID 2>/dev/null || sudo kill -9 $PORT_PID 2>/dev/null
        sleep 1
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
    nohup python ./monitor/app.py > ./monitor.log 2>&1 &
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
  
  # 5. Powiadom i otwórz przeglądarkę
  echo -e "${GREEN}Monitor działa i jest dostępny pod adresem: http://localhost:${MONITOR_PORT:-8080}${NC}"
  open_browser "http://localhost:${MONITOR_PORT:-8080}"
  
  return 0
}

# Funkcja do wyświetlania logów w przeglądarce
view_logs_in_browser() {
  echo -e "${GREEN}Otwieranie logów w przeglądarce...${NC}"
  
  # Sprawdź czy monitor jest uruchomiony
  if [ ! -f ./monitor.pid ]; then
    echo -e "${RED}Monitor nie jest uruchomiony. Uruchom najpierw skrypt.${NC}"
    return 1
  fi
  
  # Otwórz stronę z logami w przeglądarce
  open_browser "http://localhost:${MONITOR_PORT:-8080}/logs"
  
  return $?
}

# Automatyczna instalacja zależności systemowych
function install_dep() {
  PKG=$1
  if command -v $PKG >/dev/null 2>&1; then
    echo -e "${GREEN}OK:${NC} $PKG już zainstalowany."
    return
  fi
  echo -e "${GREEN}Instaluję brakującą zależność: $PKG${NC}"
  if [ "$PKG" = "terraform" ]; then
    # Instaluj od razu binarkę Terraform - to zawsze działa na każdym systemie
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
    curl -o "$TMPFILE" -fsSL "$URL" && unzip -o "$TMPFILE" -d /tmp && sudo mv /tmp/terraform /usr/local/bin/ && rm "$TMPFILE"
    if command -v terraform >/dev/null 2>&1; then
      echo -e "${GREEN}Terraform zainstalowany binarnie.${NC}"
    else
      echo -e "${RED}Instalacja Terraform nie powiodła się!${NC}"
      exit 1
    fi
    return
  fi
  if [ "$PKG" = "python3-pip" ]; then
    # Instalacja pip może się różnić w zależności od systemu
    if [ -f /etc/debian_version ]; then
      sudo apt-get update && sudo apt-get install -y python3-pip
    elif [ -f /etc/redhat-release ]; then
      sudo yum install -y python3-pip || {
        # Alternatywna instalacja via get-pip.py
        echo -e "Instaluję pip ręcznie przez get-pip.py"
        curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        python3 /tmp/get-pip.py --user
        rm /tmp/get-pip.py
      }
    elif command -v brew >/dev/null 2>&1; then
      brew install python3
    else
      echo -e "${RED}Nieobsługiwany system dla pip. Spróbuj ręcznie zainstalować python3-pip.${NC}"
      return
    fi
    return
  fi
  # Standardowa instalacja innych zależności
  if [ -f /etc/debian_version ]; then
    sudo apt-get update && sudo apt-get install -y $PKG
  elif [ -f /etc/redhat-release ]; then
    sudo yum install -y $PKG
  elif command -v brew >/dev/null 2>&1; then
    brew install $PKG
  else
    echo -e "${RED}Nieobsługiwany system! Zainstaluj $PKG ręcznie.${NC}"
    exit 1
  fi
}

# Lista zależności
install_dep docker
install_dep docker-compose
install_dep terraform
install_dep ansible
install_dep python3-pip

# Pip na pewno
if ! command -v pip3 >/dev/null 2>&1; then
  echo -e "${RED}pip3 nie został znaleziony. Instaluję...${NC}"
  install_dep python3-pip
fi

# Uruchom monitor przed innymi usługami
start_monitor

# Dodaj opcję wyświetlania logów w przeglądarce
if [ "$1" == "--logs" ] || [ "$1" == "-l" ]; then
  view_logs_in_browser
  exit 0
fi

# Uruchomienie usług docker-compose
if [ ! -s docker-compose.yml ]; then
  echo -e "${RED}Plik docker-compose.yml jest pusty lub nie istnieje!${NC}"
  exit 1
fi

echo -e "${GREEN}Uruchamianie usług przez Docker Compose...${NC}"
docker-compose up -d
if [ $? -eq 0 ]; then
  echo -e "${GREEN}Usługi docker-compose uruchomione.${NC}"
else
  echo -e "${RED}Błąd podczas uruchamiania docker-compose!${NC}"
  exit 1
fi

# Sprawdzanie statusu kontenerów
sleep 3
echo -e "\n${GREEN}Status kontenerów:${NC}"
docker-compose ps

# Sprawdź czy Rocket.Chat działa
ROCKETCHAT_URL="http://localhost:3000"
echo -e "\n${GREEN}Sprawdzanie dostępności Rocket.Chat...${NC}"
if curl -s --head "$ROCKETCHAT_URL" | grep '200 OK' > /dev/null; then
  echo -e "${GREEN}Rocket.Chat jest dostępny pod: $ROCKETCHAT_URL${NC}"
else
  echo -e "${RED}Rocket.Chat nie odpowiada pod: $ROCKETCHAT_URL${NC}"
fi

# Inicjalizacja infrastruktury
terraform init
terraform apply -auto-approve

# Deployment przez Ansible (przykład)
# ansible-playbook -i inventory.ini playbook.yml

# Uruchomienie warstwy middleware
pip3 install -r requirements.txt
nohup uvicorn middleware-api.app:app --host 0.0.0.0 --port 5000 &

# Komunikat powitalny i instrukcja
cat <<EOF

${GREEN}System EvoDev uruchomiony!${NC}

1. Otwórz przeglądarkę i przejdź do:  ${ROCKETCHAT_URL}
2. W pierwszym widoku dostępny jest tylko chat przeglądarkowy.
3. Połączony jest backend Ollama.
4. Zostaniesz poproszony o podanie API tokena (np. do LLM).

Kolejne funkcje (voice, automatyczne skille) będą aktywowane po konfiguracji tokena.
EOF
