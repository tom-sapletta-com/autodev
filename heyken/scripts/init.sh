#!/bin/bash

# Skrypt inicjalizacyjny dla systemu z dwoma rdzeniami

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
echo "  Inicjalizacja Infrastruktury                   "
echo "================================================="
echo -e "${NC}"

# Sprawdzenie wymagań
echo -e "${YELLOW}Sprawdzanie wymagań...${NC}"

# Terraform
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Terraform nie jest zainstalowany. Proszę zainstalować Terraform przed kontynuacją.${NC}"
    exit 1
fi

# Ansible
if ! command -v ansible &> /dev/null; then
    echo -e "${RED}Ansible nie jest zainstalowany. Proszę zainstalować Ansible przed kontynuacją.${NC}"
    exit 1
fi

# Docker i Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker nie jest zainstalowany. Proszę zainstalować Docker przed kontynuacją.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose nie jest zainstalowany. Proszę zainstalować Docker Compose przed kontynuacją.${NC}"
    exit 1
fi

echo -e "${GREEN}Wszystkie wymagania spełnione.${NC}"

# Tworzenie struktury katalogów
echo -e "${YELLOW}Tworzenie struktury katalogów...${NC}"

mkdir -p terraform
mkdir -p terraform/modules/{core,sandbox,services,database}
mkdir -p ansible/playbooks
mkdir -p ansible/roles/{core,sandbox,database,common}
mkdir -p data/{shared,logs,backups}
mkdir -p scripts

echo -e "${GREEN}Struktura katalogów utworzona.${NC}"

# Kopiowanie plików Terraform
echo -e "${YELLOW}Kopiowanie plików Terraform...${NC}"

# Tutaj kopiowanie plików konfiguracyjnych Terraform
cp -v templates/terraform/main.tf terraform/
cp -v templates/terraform/modules/core/main.tf terraform/modules/core/
cp -v templates/terraform/modules/sandbox/main.tf terraform/modules/sandbox/
cp -v templates/terraform/modules/services/main.tf terraform/modules/services/
cp -v templates/terraform/modules/database/main.tf terraform/modules/database/

echo -e "${GREEN}Pliki Terraform skopiowane.${NC}"

# Kopiowanie playbooks Ansible
echo -e "${YELLOW}Kopiowanie playbooks Ansible...${NC}"

# Tutaj kopiowanie playbooks Ansible
cp -v templates/ansible/site.yml ansible/
cp -v templates/ansible/playbooks/* ansible/playbooks/
cp -rv templates/ansible/roles/* ansible/roles/

echo -e "${GREEN}Playbooks Ansible skopiowane.${NC}"

# Generowanie zmiennych środowiskowych
echo -e "${YELLOW}Tworzenie pliku zmiennych środowiskowych...${NC}"

cat > .env << EOF
# Konfiguracja rdzeni
ACTIVE_CORE_ID=1
GITLAB_ROOT_PASSWORD=$(openssl rand -base64 12)
GITLAB_API_TOKEN=$(openssl rand -hex 16)

# Konfiguracja zewnętrznych API (tylko do nauki)
GEMINI_API_KEY=
CLAUDE_API_KEY=

# Konfiguracja bazy danych
POSTGRES_PASSWORD=$(openssl rand -base64 12)

# Konfiguracja Rocket.Chat
ROCKETCHAT_ADMIN_PASSWORD=$(openssl rand -base64 12)
EOF

echo -e "${GREEN}Plik zmiennych środowiskowych utworzony.${NC}"

# Inicjalizacja Terraform
echo -e "${YELLOW}Inicjalizacja Terraform...${NC}"

cd terraform
terraform init
cd ..

echo -e "${GREEN}Terraform zainicjalizowany.${NC}"

# Informacja końcowa
echo -e "${BLUE}"
echo "================================================="
echo "  System zainicjalizowany pomyślnie!             "
echo "================================================="
echo -e "${NC}"
echo "Aby wdrożyć system:"
echo "1. Uzupełnij brakujące dane w pliku .env"
echo "2. Uruchom './scripts/deploy.sh' aby wdrożyć infrastrukturę"
echo ""
echo "Domyślnie aktywny jest rdzeń 1. Aby zmienić aktywny rdzeń,"
echo "użyj './scripts/switch_core.sh [1|2]'"