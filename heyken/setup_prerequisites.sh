#!/bin/bash

# Kolory do komunikatów
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Konfiguracja wymaganych zależności dla projektu Heyken ===${NC}"
echo ""

# 1. Sprawdzenie i dodanie użytkownika do grupy docker
echo -e "${YELLOW}Sprawdzanie członkostwa w grupie docker...${NC}"
if groups | grep -q docker; then
  echo -e "${GREEN}Użytkownik już należy do grupy docker.${NC}"
else
  echo -e "${YELLOW}Dodawanie użytkownika do grupy docker...${NC}"
  echo -e "${RED}Wymagane hasło sudo:${NC}"
  sudo usermod -aG docker $USER
  echo -e "${GREEN}Użytkownik dodany do grupy docker.${NC}"
  echo -e "${YELLOW}UWAGA: Zmiany będą aktywne po ponownym zalogowaniu lub wykonaniu polecenia: newgrp docker${NC}"
  echo -e "${YELLOW}Zalecane jest wylogowanie i ponowne zalogowanie.${NC}"
fi

# 2. Tworzenie sieci Docker
echo -e "${YELLOW}Tworzenie sieci Docker 'system_network'...${NC}"
if sudo docker network ls | grep -q "system_network"; then
  echo -e "${GREEN}Sieć 'system_network' już istnieje.${NC}"
else
  echo -e "${YELLOW}Tworzenie sieci 'system_network'...${NC}"
  echo -e "${RED}Wymagane hasło sudo:${NC}"
  sudo docker network create system_network
  echo -e "${GREEN}Sieć Docker 'system_network' utworzona pomyślnie.${NC}"
fi

# 3. Instalacja Terraform
if command -v terraform &>/dev/null; then
  echo -e "${GREEN}Terraform już zainstalowany.${NC}"
else
  echo -e "${YELLOW}Instalacja Terraform z binarki...${NC}"
  
  # Określ wersję i architekturę
  T_VERSION="1.8.5"
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64) ARCH=amd64 ;;
    aarch64) ARCH=arm64 ;;
    *) echo -e "${RED}Nieobsługiwana architektura: $ARCH${NC}"; exit 1 ;;
  esac
  
  # Pobierz i zainstaluj Terraform
  TMP_DIR=$(mktemp -d)
  cd "$TMP_DIR" || exit 1
  
  echo -e "${YELLOW}Pobieranie Terraform v${T_VERSION}...${NC}"
  curl -s -o terraform.zip "https://releases.hashicorp.com/terraform/${T_VERSION}/terraform_${T_VERSION}_linux_${ARCH}.zip"
  
  echo -e "${YELLOW}Rozpakowywanie...${NC}"
  unzip -q terraform.zip
  
  echo -e "${YELLOW}Instalacja Terraform...${NC}"
  echo -e "${RED}Wymagane hasło sudo:${NC}"
  sudo mv terraform /usr/local/bin/
  
  # Sprzątanie
  cd - > /dev/null || exit 1
  rm -rf "$TMP_DIR"
  
  # Sprawdź instalację
  if command -v terraform &>/dev/null; then
    echo -e "${GREEN}Terraform zainstalowany pomyślnie.${NC}"
  else
    echo -e "${RED}Błąd: Nie można zainstalować Terraform.${NC}"
  fi
fi

echo ""
echo -e "${GREEN}=== Konfiguracja zakończona ===${NC}"
echo -e "${YELLOW}Możesz teraz uruchomić ponownie skrypt run.sh${NC}"
echo -e "${YELLOW}Jeśli dodano Cię do grupy docker, pamiętaj o ponownym zalogowaniu lub wykonaniu: newgrp docker${NC}"
