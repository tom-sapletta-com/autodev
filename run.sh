#!/bin/bash
# Uniwersalny skrypt do uruchamiania systemu evodev na Linux/Mac/WSL
set -e

# Kolory do statusów
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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
