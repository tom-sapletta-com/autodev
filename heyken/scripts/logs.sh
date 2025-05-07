#!/bin/bash

# Skrypt do przeglądania logów komponentów

# Kolory dla lepszej czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Sprawdzenie argumentów
if [ $# -ne 1 ]; then
    echo -e "${RED}Błąd: Podaj nazwę komponentu${NC}"
    echo "Użycie: $0 <komponent>"
    echo ""
    echo "Dostępne komponenty:"
    echo "- core1 - Rdzeń 1"
    echo "- core2 - Rdzeń 2"
    echo "- sandbox - Piaskownica testowa"
    echo "- feature_runner - Runner testów"
    echo "- system - Logi systemowe"
    echo "- all - Wszystkie logi"
    exit 1
fi

COMPONENT=$1

# Banner
echo -e "${BLUE}"
echo "================================================="
echo "  System Autonomiczny z Redundantnymi Rdzeniami  "
echo "  Przeglądanie Logów                             "
echo "================================================="
echo -e "${NC}"

# Wczytanie aktualnego stanu
ACTIVE_CORE=$(grep ACTIVE_CORE_ID .env | cut -d= -f2)

echo -e "${YELLOW}Aktywny rdzeń: $ACTIVE_CORE${NC}"
echo -e "${YELLOW}Wyświetlanie logów dla: $COMPONENT${NC}"
echo ""

case $COMPONENT in
    core1)
        echo -e "${YELLOW}Logi Core Manager 1:${NC}"
        docker logs core_manager_1 2>&1 | tail -n 100
        ;;
    core2)
        echo -e "${YELLOW}Logi Core Manager 2:${NC}"
        docker logs core_manager_2 2>&1 | tail -n 100
        ;;
    sandbox)
        echo -e "${YELLOW}Logi Sandbox Manager:${NC}"
        docker logs sandbox_manager 2>&1 | tail -n 100
        ;;
    feature_runner)
        echo -e "${YELLOW}Logi Feature Runner:${NC}"
        docker logs feature_runner 2>&1 | tail -n 100
        ;;
    system)
        echo -e "${YELLOW}Logi System DB:${NC}"
        docker logs system_db 2>&1 | tail -n 50
        echo ""
        echo -e "${YELLOW}Logi System Monitor:${NC}"
        docker logs system_monitor 2>&1 | tail -n 50
        ;;
    all)
        echo -e "${YELLOW}Wszystkie logi:${NC}"
        for container in $(docker ps --format "{{.Names}}"); do
            echo -e "${BLUE}=== Logi kontenera: $container ===${NC}"
            docker logs $container 2>&1 | tail -n 30
            echo ""
        done
        ;;
    *)
        # Sprawdzamy, czy to jest konkretny kontener
        if docker ps --format "{{.Names}}" | grep -q "^$COMPONENT$"; then
            echo -e "${YELLOW}Logi kontenera $COMPONENT:${NC}"
            docker logs $COMPONENT 2>&1 | tail -n 100
        else
            echo -e "${RED}Nieznany komponent: $COMPONENT${NC}"
            echo "Dostępne komponenty:"
            echo "- core1 - Rdzeń 1"
            echo "- core2 - Rdzeń 2"
            echo "- sandbox - Piaskownica testowa"
            echo "- feature_runner - Runner testów"
            echo "- system - Logi systemowe"
            echo "- all - Wszystkie logi"
            echo ""
            echo "Lub podaj nazwę kontenera:"
            docker ps --format "- {{.Names}}"
            exit 1
        fi
        ;;
esac

echo ""
echo -e "${GREEN}Koniec logów.${NC}"
echo "Aby wyświetlić więcej linii, użyj polecenia: docker logs <kontener> --tail <liczba_linii>"