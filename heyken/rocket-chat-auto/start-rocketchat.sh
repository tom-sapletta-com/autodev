#!/bin/bash
# Script to start RocketChat with auto user setup

# Colors for messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Starting RocketChat with Auto User Setup         ${NC}"
echo -e "${GREEN}==================================================${NC}"

# Load environment variables from parent .env file
if [ -f ../.env ]; then
  echo -e "${YELLOW}Loading environment variables from ../.env${NC}"
  # Export all variables from the .env file
  set -a
  source ../.env
  set +a
  echo "Admin username set to: $ROCKETCHAT_ADMIN_USERNAME"
  echo "Bot username set to: $ROCKETCHAT_BOT_USERNAME"
  echo "Human username set to: $ROCKETCHAT_HUMAN_USERNAME"
else
  echo -e "${YELLOW}No ../.env file found, using default values${NC}"
fi

# Create .env file for the setup script
echo -e "${YELLOW}Creating .env file for setup script...${NC}"
cat > .env << EOF
# Admin User Configuration
ROCKETCHAT_ADMIN_USERNAME=${ROCKETCHAT_ADMIN_USERNAME:-heyken_admin}
ROCKETCHAT_ADMIN_PASSWORD=${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}
ROCKETCHAT_ADMIN_EMAIL=${ROCKETCHAT_ADMIN_EMAIL:-admin@heyken.local}

# Bot User Configuration
ROCKETCHAT_BOT_USERNAME=${ROCKETCHAT_BOT_USERNAME:-heyken_bot}
ROCKETCHAT_BOT_PASSWORD=${ROCKETCHAT_BOT_PASSWORD:-heyken123}
ROCKETCHAT_BOT_EMAIL=${ROCKETCHAT_BOT_EMAIL:-bot@heyken.local}

# Human User Configuration
ROCKETCHAT_HUMAN_USERNAME=${ROCKETCHAT_HUMAN_USERNAME:-heyken_user}
ROCKETCHAT_HUMAN_PASSWORD=${ROCKETCHAT_HUMAN_PASSWORD:-user123}
ROCKETCHAT_HUMAN_EMAIL=${ROCKETCHAT_HUMAN_EMAIL:-user@heyken.local}

# RocketChat URL
ROCKETCHAT_URL=http://localhost:3100
EOF

# Create necessary directories
mkdir -p data/db data/dump uploads

# Start RocketChat and MongoDB
echo -e "${YELLOW}Starting RocketChat and MongoDB...${NC}"
docker-compose up -d

# Wait for RocketChat to be ready
echo -e "${YELLOW}Waiting for RocketChat to start (this may take a minute or two)...${NC}"
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  ATTEMPT=$((ATTEMPT+1))
  echo -n "."
  
  # Check if RocketChat is responding
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:3100/api/info | grep -q "200"; then
    echo -e "\n${GREEN}RocketChat is now accessible!${NC}"
    break
  fi
  
  # If we've reached the maximum number of attempts, exit
  if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "\n${RED}Timed out waiting for RocketChat to start.${NC}"
    echo -e "${YELLOW}Check the logs with: docker-compose logs rocketchat${NC}"
    exit 1
  fi
  
  sleep 5
done

# Wait a bit more to ensure RocketChat is fully initialized
echo -e "${YELLOW}Waiting for RocketChat to fully initialize...${NC}"
sleep 20

# Run the setup script
echo -e "${YELLOW}Running user setup script...${NC}"
./setup-rocketchat-users.sh

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  RocketChat Setup Complete                       ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}RocketChat URL: http://localhost:3100${NC}"
echo -e "${GREEN}Webmail URL: http://localhost:8025${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${YELLOW}To view logs:${NC}"
echo -e "${YELLOW}  docker-compose logs -f rocketchat${NC}"
echo -e "${YELLOW}To stop all services:${NC}"
echo -e "${YELLOW}  docker-compose down${NC}"
echo -e "${GREEN}==================================================${NC}"
