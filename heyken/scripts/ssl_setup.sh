#!/bin/bash

# Skrypt konfiguracyjny SSL dla domen heyken.io i hey-ken.com

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
echo "  Konfiguracja certyfikatów SSL                  "
echo "================================================="
echo -e "${NC}"

# Sprawdzenie czy certbot jest zainstalowany
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}Certbot nie jest zainstalowany. Instalowanie...${NC}"
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Wczytanie konfiguracji domen
source ../config/domains.conf

echo -e "${YELLOW}Pobieranie certyfikatów SSL dla głównej domeny (${PRIMARY_DOMAIN})...${NC}"
certbot certonly --nginx --agree-tos --email admin@${PRIMARY_DOMAIN} -d ${PRIMARY_DOMAIN} -d www.${PRIMARY_DOMAIN}

echo -e "${YELLOW}Pobieranie certyfikatów SSL dla alternatywnej domeny (${ALTERNATE_DOMAIN})...${NC}"
certbot certonly --nginx --agree-tos --email admin@${PRIMARY_DOMAIN} -d ${ALTERNATE_DOMAIN} -d www.${ALTERNATE_DOMAIN}

# Pobieranie certyfikatów dla subdomen
echo -e "${YELLOW}Pobieranie certyfikatów SSL dla subdomen...${NC}"
certbot certonly --nginx --agree-tos --email admin@${PRIMARY_DOMAIN} -d ${API_SUBDOMAIN}.${PRIMARY_DOMAIN}
certbot certonly --nginx --agree-tos --email admin@${PRIMARY_DOMAIN} -d ${DOCS_SUBDOMAIN}.${PRIMARY_DOMAIN}
certbot certonly --nginx --agree-tos --email admin@${PRIMARY_DOMAIN} -d ${DASHBOARD_SUBDOMAIN}.${PRIMARY_DOMAIN}
certbot certonly --nginx --agree-tos --email admin@${PRIMARY_DOMAIN} -d ${SANDBOX_SUBDOMAIN}.${PRIMARY_DOMAIN}

# Konfiguracja auto-odnowienia
echo -e "${YELLOW}Konfiguracja automatycznego odnowienia certyfikatów...${NC}"
echo "0 3 * * * root certbot renew --quiet" > /etc/cron.d/certbot-renew

echo -e "${GREEN}Certyfikaty SSL zostały pomyślnie skonfigurowane dla wszystkich domen Heyken.${NC}"
echo -e "${GREEN}Automatyczne odnawianie certyfikatów zostało skonfigurowane.${NC}"

# Restart Nginx aby zastosować zmiany
echo -e "${YELLOW}Restartowanie Nginx...${NC}"
systemctl restart nginx

echo -e "${GREEN}Konfiguracja SSL zakończona pomyślnie!${NC}"
