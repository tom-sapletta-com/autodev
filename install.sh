#!/bin/bash
# Kompletny instalator środowiska autodev (Linux/macOS/Fedora)
set -e

# Wykrywanie platformy
OS="$(uname -s)"
PM=""
INSTALL=""

if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ $ID == "ubuntu" || $ID == "debian" ]]; then
        PM="apt"
        INSTALL="apt install -y"
    elif [[ $ID == "fedora" || $ID == "rhel" || $ID == "centos" ]]; then
        PM="dnf"
        INSTALL="dnf install -y"
    elif [[ $ID == "arch" ]]; then
        PM="pacman"
        INSTALL="pacman -Syu --noconfirm"
    fi
fi

if [[ $PM == "" ]]; then
    echo "Nieobsługiwana platforma. Zainstaluj wymagane pakiety ręcznie: curl, wget, git, python3, python3-pip, unzip, docker, docker-compose, terraform, ansible, code-server"; exit 1
fi

# Aktualizacja systemu
if [[ $PM == "apt" ]]; then
    apt update && apt upgrade -y
elif [[ $PM == "dnf" ]]; then
    dnf upgrade -y
elif [[ $PM == "pacman" ]]; then
    pacman -Syu --noconfirm
fi

# Instalacja narzędzi systemowych
$INSTALL curl wget git python3 python3-pip unzip

# Instalacja Docker
if ! command -v docker &> /dev/null; then
    if [[ $PM == "apt" ]]; then
        $INSTALL docker.io
    elif [[ $PM == "dnf" ]]; then
        $INSTALL docker
        systemctl enable --now docker
    elif [[ $PM == "pacman" ]]; then
        $INSTALL docker
        systemctl enable --now docker
    fi
fi

# Instalacja Docker Compose
if ! command -v docker-compose &> /dev/null; then
    if [[ $PM == "apt" ]]; then
        $INSTALL docker-compose
    elif [[ $PM == "dnf" ]]; then
        $INSTALL docker-compose
    elif [[ $PM == "pacman" ]]; then
        $INSTALL docker-compose
    else
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
fi

# Instalacja Terraform
if ! command -v terraform &> /dev/null; then
    if [[ $PM == "dnf" ]]; then
        $INSTALL dnf-plugins-core || true
        dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
        $INSTALL terraform
    else
        wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
        unzip terraform_1.6.6_linux_amd64.zip
        mv terraform /usr/local/bin/
        rm terraform_1.6.6_linux_amd64.zip
    fi
fi

# Instalacja Ansible
if ! command -v ansible &> /dev/null; then
    $INSTALL ansible
fi

# Instalacja VS Code Server (code-server)
if ! command -v code-server &> /dev/null; then
    curl -fsSL https://code-server.dev/install.sh | sh
fi

# Instalacja zależności Pythona
pip3 install -r requirements.txt

# Inicjalizacja struktury projektu
bash scripts/setup.sh

echo "\nŚrodowisko autodev zainstalowane. Użyj ./run.sh lub ./run.ps1 do uruchomienia systemu."
