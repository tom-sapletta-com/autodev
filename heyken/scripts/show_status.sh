#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  Heyken System Status                            ${NC}"
echo -e "${BLUE}==================================================${NC}"

# Load environment variables
if [ -f ../.env ]; then
  source ../.env
else
  echo -e "${RED}Error: .env file not found!${NC}"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Docker is not running or you don't have permission to use it.${NC}"
  exit 1
fi

# Check RocketChat status
echo -e "${YELLOW}RocketChat Status:${NC}"
ROCKETCHAT_CONTAINER=$(docker ps -a --filter "name=rocketchat" --format "{{.Names}} {{.Status}}")
if [ -z "$ROCKETCHAT_CONTAINER" ]; then
  echo -e "  ${RED}No RocketChat containers found${NC}"
else
  echo -e "$ROCKETCHAT_CONTAINER" | while read container; do
    NAME=$(echo $container | awk '{print $1}')
    STATUS=$(echo $container | awk '{$1=""; print $0}' | xargs)
    if [[ $STATUS == *"Up"* ]]; then
      echo -e "  ${GREEN}$NAME: $STATUS${NC}"
    else
      echo -e "  ${RED}$NAME: $STATUS${NC}"
    fi
  done
  
  # Get RocketChat port
  ROCKETCHAT_PORT=$(docker port $(docker ps -q --filter "name=rocketchat") 2>/dev/null | grep 3000/tcp | awk -F':' '{print $2}')
  if [ -z "$ROCKETCHAT_PORT" ]; then
    ROCKETCHAT_PORT=${ROCKETCHAT_PORT:-3100}
  fi
  echo -e "  ${BLUE}URL: http://localhost:$ROCKETCHAT_PORT${NC}"
fi

# Check Email Server status
echo -e "\n${YELLOW}Email Server Status:${NC}"
MAILHOG_CONTAINER=$(docker ps -a --filter "name=mailhog" --format "{{.Names}} {{.Status}}")
if [ -z "$MAILHOG_CONTAINER" ]; then
  echo -e "  ${RED}No Email Server containers found${NC}"
else
  echo -e "$MAILHOG_CONTAINER" | while read container; do
    NAME=$(echo $container | awk '{print $1}')
    STATUS=$(echo $container | awk '{$1=""; print $0}' | xargs)
    if [[ $STATUS == *"Up"* ]]; then
      echo -e "  ${GREEN}$NAME: $STATUS${NC}"
    else
      echo -e "  ${RED}$NAME: $STATUS${NC}"
    fi
  done
  
  # Get Email Server ports
  MAILHOG_SMTP_PORT=$(docker port $(docker ps -q --filter "name=mailhog") 2>/dev/null | grep 1025/tcp | awk -F':' '{print $2}')
  MAILHOG_WEB_PORT=$(docker port $(docker ps -q --filter "name=mailhog") 2>/dev/null | grep 8025/tcp | awk -F':' '{print $2}')
  
  if [ -z "$MAILHOG_SMTP_PORT" ]; then
    MAILHOG_SMTP_PORT=${MAILHOG_SMTP_PORT:-1025}
  fi
  if [ -z "$MAILHOG_WEB_PORT" ]; then
    MAILHOG_WEB_PORT=${MAILHOG_WEB_PORT:-8025}
  fi
  
  echo -e "  ${BLUE}SMTP: localhost:$MAILHOG_SMTP_PORT${NC}"
  echo -e "  ${BLUE}Webmail: http://localhost:$MAILHOG_WEB_PORT${NC}"
fi

# Check MongoDB status
echo -e "\n${YELLOW}MongoDB Status:${NC}"
MONGO_CONTAINER=$(docker ps -a --filter "name=mongo" --format "{{.Names}} {{.Status}}")
if [ -z "$MONGO_CONTAINER" ]; then
  echo -e "  ${RED}No MongoDB containers found${NC}"
else
  echo -e "$MONGO_CONTAINER" | while read container; do
    NAME=$(echo $container | awk '{print $1}')
    STATUS=$(echo $container | awk '{$1=""; print $0}' | xargs)
    if [[ $STATUS == *"Up"* ]]; then
      echo -e "  ${GREEN}$NAME: $STATUS${NC}"
    else
      echo -e "  ${RED}$NAME: $STATUS${NC}"
    fi
  done
fi

# Check other Heyken services
echo -e "\n${YELLOW}Other Heyken Services:${NC}"
OTHER_CONTAINERS=$(docker ps -a --filter "name=heyken" --format "{{.Names}} {{.Status}}" | grep -v "rocketchat\|mongo\|mailhog")
if [ -z "$OTHER_CONTAINERS" ]; then
  echo -e "  ${RED}No other Heyken containers found${NC}"
else
  echo -e "$OTHER_CONTAINERS" | while read container; do
    NAME=$(echo $container | awk '{print $1}')
    STATUS=$(echo $container | awk '{$1=""; print $0}' | xargs)
    if [[ $STATUS == *"Up"* ]]; then
      echo -e "  ${GREEN}$NAME: $STATUS${NC}"
    else
      echo -e "  ${RED}$NAME: $STATUS${NC}"
    fi
  done
fi

# Check used ports
echo -e "\n${YELLOW}Used Ports:${NC}"
echo -e "  ${BLUE}RocketChat: ${ROCKETCHAT_PORT:-3100}${NC}"
echo -e "  ${BLUE}Email SMTP: ${MAILHOG_SMTP_PORT:-1025}${NC}"
echo -e "  ${BLUE}Email Webmail: ${MAILHOG_WEB_PORT:-8025}${NC}"
echo -e "  ${BLUE}MongoDB: ${MONGO_PORT:-27017}${NC}"

# Check if services are accessible
echo -e "\n${YELLOW}Service Accessibility:${NC}"

# Check RocketChat
if curl -s http://localhost:${ROCKETCHAT_PORT:-3100} > /dev/null; then
  echo -e "  ${GREEN}RocketChat is accessible at http://localhost:${ROCKETCHAT_PORT:-3100}${NC}"
else
  echo -e "  ${RED}RocketChat is NOT accessible at http://localhost:${ROCKETCHAT_PORT:-3100}${NC}"
fi

# Check Email Webmail
if curl -s http://localhost:${MAILHOG_WEB_PORT:-8025} > /dev/null; then
  echo -e "  ${GREEN}Email Webmail is accessible at http://localhost:${MAILHOG_WEB_PORT:-8025}${NC}"
else
  echo -e "  ${RED}Email Webmail is NOT accessible at http://localhost:${MAILHOG_WEB_PORT:-8025}${NC}"
fi

echo -e "\n${BLUE}==================================================${NC}"
echo -e "${BLUE}  User Credentials                                ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo -e "  ${GREEN}Admin: ${ROCKETCHAT_ADMIN_USERNAME:-heyken_admin} / ${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}${NC}"
echo -e "  ${GREEN}Bot: ${ROCKETCHAT_BOT_USERNAME:-heyken_bot} / ${ROCKETCHAT_BOT_PASSWORD:-heyken123}${NC}"
echo -e "  ${GREEN}User: ${ROCKETCHAT_HUMAN_USERNAME:-heyken_user} / ${ROCKETCHAT_HUMAN_PASSWORD:-user123}${NC}"

echo -e "\n${BLUE}==================================================${NC}"
echo -e "${BLUE}  Management Commands                             ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo -e "  ${YELLOW}Start system:${NC} ./run_heyken.sh"
echo -e "  ${YELLOW}Stop system:${NC} ./stop.sh"
echo -e "  ${YELLOW}Setup email server:${NC} ./scripts/setup_email_server.sh"
echo -e "  ${YELLOW}Show status:${NC} ./scripts/show_status.sh"
echo -e "${BLUE}==================================================${NC}"
