#!/bin/bash

# Skrypt wdrażania systemu z dwoma rdzeniami

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
echo "  Wdrażanie Infrastruktury                       "
echo "================================================="
echo -e "${NC}"

# Wczytanie zmiennych środowiskowych
if [ -f .env ]; then
    source .env
else
    echo -e "${RED}Brak pliku .env! Uruchom najpierw ./scripts/init.sh${NC}"
    exit 1
fi

# Sprawdzenie czy wszystkie wymagane zmienne są ustawione
if [ -z "$ACTIVE_CORE_ID" ] || [ -z "$GITLAB_ROOT_PASSWORD" ] || [ -z "$GITLAB_API_TOKEN" ]; then
    echo -e "${RED}Brak wymaganych zmiennych w pliku .env!${NC}"
    exit 1
fi

# Wdrożenie infrastruktury przez Terraform
echo -e "${YELLOW}Wdrażanie infrastruktury przez Terraform...${NC}"

cd terraform
terraform apply -var="active_core_id=${ACTIVE_CORE_ID}" -auto-approve
if [ $? -ne 0 ]; then
    echo -e "${RED}Błąd podczas wdrażania Terraform!${NC}"
    exit 1
fi
cd ..

echo -e "${GREEN}Infrastruktura Terraform wdrożona pomyślnie.${NC}"

# Konfiguracja środowiska przez Ansible
echo -e "${YELLOW}Konfiguracja środowiska przez Ansible...${NC}"

cd ansible
ansible-playbook -i inventory.ini site.yml --extra-vars "active_core_id=${ACTIVE_CORE_ID} gitlab_root_password=${GITLAB_ROOT_PASSWORD} gitlab_api_token=${GITLAB_API_TOKEN}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Błąd podczas konfiguracji Ansible!${NC}"
    exit 1
fi
cd ..

echo -e "${GREEN}Konfiguracja Ansible zakończona pomyślnie.${NC}"

# Oczekiwanie na inicjalizację usług
echo -e "${YELLOW}Oczekiwanie na inicjalizację usług...${NC}"
echo "To może potrwać kilka minut..."

# Sprawdzanie dostępności GitLab
for i in {1..30}; do
    echo -n "."
    curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 | grep -q 200
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}GitLab jest dostępny.${NC}"
        break
    fi
    sleep 10

    if [ $i -eq 30 ]; then
        echo ""
        echo -e "${YELLOW}Upłynął limit czasu oczekiwania na GitLab, ale wdrażanie będzie kontynuowane.${NC}"
    fi
done

# Inicjalizacja repozytoriów
echo -e "${YELLOW}Inicjalizacja repozytoriów GitLab...${NC}"

./scripts/init_gitlab.sh
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Ostrzeżenie: Inicjalizacja repozytoriów GitLab nie powiodła się w pełni.${NC}"
    echo -e "${YELLOW}Możesz uruchomić ./scripts/init_gitlab.sh ręcznie później.${NC}"
fi

# Informacja końcowa
echo -e "${BLUE}"
echo "================================================="
echo "  System wdrożony pomyślnie!                     "
echo "================================================="
echo -e "${NC}"
echo "Dostępne usługi:"
echo "- GitLab: http://localhost:8080 (admin / ${GITLAB_ROOT_PASSWORD})"
echo "- Ollama API: http://localhost:11434"
echo "- Middleware API: http://localhost:5000"
echo "- Rocket.Chat: http://localhost:3000 (admin / ${ROCKETCHAT_ADMIN_PASSWORD})"
echo ""
echo "Zarządzanie systemem:"
echo "- Przełączanie aktywnego rdzenia: ./scripts/switch_core.sh [1|2]"
echo "- Monitorowanie stanu: ./scripts/status.sh"
echo "- Utworzenie nowej funkcji: ./scripts/create_feature.sh [nazwa_funkcji]"
echo "- Sprawdzanie logów: ./scripts/logs.sh [komponent]"