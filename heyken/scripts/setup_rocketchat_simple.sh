#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken - Simple RocketChat Setup                ${NC}"
echo -e "${GREEN}==================================================${NC}"

# Load environment variables
if [ -f ../.env ]; then
  export $(cat ../.env | grep -v '^#' | xargs)
else
  echo -e "${RED}Error: .env file not found!${NC}"
  exit 1
fi

# 1. Stop any running RocketChat instances
echo -e "${YELLOW}Stopping any running RocketChat instances...${NC}"
cd ../docker/rocketchat
docker-compose down -v 2>/dev/null || true
cd ../..

# 2. Create a custom Dockerfile with auto-configuration
echo -e "${YELLOW}Creating custom Dockerfile...${NC}"
cat > docker/rocketchat/Dockerfile << 'EOF'
FROM registry.rocket.chat/rocketchat/rocket.chat:7.5.1

LABEL maintainer="Heyken System <admin@hey-ken.com>"

# Ekspozycja portów
EXPOSE 3000

# Zmienne środowiskowe
ENV ROOT_URL=http://localhost:3100 \
    PORT=3000 \
    MONGO_URL=mongodb://mongodb:27017/rocketchat \
    MONGO_OPLOG_URL=mongodb://mongodb:27017/local \
    MAIL_URL=smtp://smtp.gmail.com:465 \
    HTTP_FORWARDED_COUNT=1 \
    # Skip setup wizard
    OVERWRITE_SETTING_Show_Setup_Wizard=completed \
    # Admin user configuration
    ADMIN_USERNAME=admin \
    ADMIN_PASS=dxIsDLnhiqKfDt5J \
    ADMIN_EMAIL=admin@heyken.local \
    # Disable registration and require admin for new users
    OVERWRITE_SETTING_Accounts_RegistrationForm=disabled \
    OVERWRITE_SETTING_Accounts_ManuallyApproveNewUsers=true

# Uruchomienie Rocket.Chat
CMD ["node", "main.js"]
EOF

# 3. Create a docker-compose file
echo -e "${YELLOW}Creating docker-compose file...${NC}"
cat > docker/rocketchat/docker-compose-simple.yml << 'EOF'
version: '3'

services:
  mongodb:
    image: mongo:5.0
    restart: always
    volumes:
      - ./data_simple/db:/data/db
    command: mongod --oplogSize 128 --replSet rs0
    networks:
      - rocketchat

  mongodb-init:
    image: mongo:5.0
    restart: on-failure
    command: >
      bash -c "sleep 10 && mongosh mongodb/rocketchat --eval \"rs.initiate({ _id: 'rs0', members: [ { _id: 0, host: 'mongodb:27017' } ]})\""
    depends_on:
      - mongodb
    networks:
      - rocketchat

  rocketchat:
    build: 
      context: .
      dockerfile: Dockerfile
    restart: always
    volumes:
      - ./uploads:/app/uploads
    depends_on:
      - mongodb
    ports:
      - 3100:3000
    networks:
      - rocketchat
      - system_network

networks:
  rocketchat:
    driver: bridge
  system_network:
    external: true
EOF

# 4. Build and start RocketChat
echo -e "${YELLOW}Building and starting RocketChat...${NC}"
cd docker/rocketchat
docker-compose -f docker-compose-simple.yml up -d --build
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to start RocketChat!${NC}"
  cd ../..
  exit 1
fi
cd ../..

# 5. Wait for RocketChat to be ready
echo -e "${YELLOW}Waiting for RocketChat to be ready...${NC}"
MAX_ATTEMPTS=30
ATTEMPT=0
ROCKETCHAT_READY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  echo -n "."
  # Try to connect to RocketChat
  if curl -s http://localhost:3100 > /dev/null; then
    echo -e "\n${GREEN}RocketChat is now accessible!${NC}"
    ROCKETCHAT_READY=true
    break
  fi
  ATTEMPT=$((ATTEMPT+1))
  sleep 5
done

if [ "$ROCKETCHAT_READY" = false ]; then
  echo -e "${RED}RocketChat failed to start properly after $(($MAX_ATTEMPTS * 5)) seconds.${NC}"
  exit 1
fi

# 6. Wait a bit more to ensure RocketChat is fully initialized
echo -e "${YELLOW}Waiting for RocketChat to fully initialize...${NC}"
sleep 15

# 7. Create users and channels using the RocketChat API
echo -e "${YELLOW}Creating users and channels...${NC}"

# Login as admin
echo -e "${YELLOW}Logging in as admin...${NC}"
LOGIN_RESPONSE=$(curl -s -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"dxIsDLnhiqKfDt5J\"}" \
  http://localhost:3100/api/v1/login)

if ! echo "$LOGIN_RESPONSE" | grep -q "status\":\"success"; then
  echo -e "${RED}Failed to login as admin. Response: ${LOGIN_RESPONSE}${NC}"
  echo -e "${YELLOW}RocketChat might need more time to initialize. Please wait and try again.${NC}"
  echo -e "${YELLOW}You can manually access RocketChat at http://localhost:3100${NC}"
  echo -e "${YELLOW}Login with: admin / dxIsDLnhiqKfDt5J${NC}"
  exit 1
fi

# Extract auth token and user ID
AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"authToken":"[^"]*' | cut -d'"' -f4)
USER_ID=$(echo "$LOGIN_RESPONSE" | grep -o '"userId":"[^"]*' | cut -d'"' -f4)

echo -e "${GREEN}Successfully logged in as admin.${NC}"

# Create bot user
echo -e "${YELLOW}Creating bot user...${NC}"
curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Heyken Bot\",\"email\":\"bot@heyken.local\",\"password\":\"heyken123\",\"username\":\"heyken_bot\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false}" \
  http://localhost:3100/api/v1/users.create > /dev/null

echo -e "${GREEN}Bot user created (or already exists).${NC}"

# Create human user
echo -e "${YELLOW}Creating human user...${NC}"
curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Human User\",\"email\":\"user@heyken.local\",\"password\":\"user123\",\"username\":\"heyken_user\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false}" \
  http://localhost:3100/api/v1/users.create > /dev/null

echo -e "${GREEN}Human user created (or already exists).${NC}"

# Create channels
echo -e "${YELLOW}Creating channels...${NC}"

# Create public channels
curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"heyken-system\"}" \
  http://localhost:3100/api/v1/channels.create > /dev/null

curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"heyken-logs\"}" \
  http://localhost:3100/api/v1/channels.create > /dev/null

# Create private channel
curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"heyken-sandbox\"}" \
  http://localhost:3100/api/v1/groups.create > /dev/null

echo -e "${GREEN}Channels created (or already exist).${NC}"

# 8. Update the run_heyken.sh script to use our custom docker-compose file
echo -e "${YELLOW}Updating run_heyken.sh to use custom RocketChat configuration...${NC}"
if [ -f ../run_heyken.sh ]; then
    sed -i 's/docker-compose-auto.yml/docker-compose-simple.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-new.yml/docker-compose-simple.yml/g' ../run_heyken.sh
    echo -e "${GREEN}Updated run_heyken.sh successfully.${NC}"
else
    echo -e "${YELLOW}Could not find run_heyken.sh to update.${NC}"
fi

# 9. Update the stop.sh script to handle the custom docker-compose file
echo -e "${YELLOW}Updating stop.sh to handle custom RocketChat configuration...${NC}"
if [ -f ../stop.sh ]; then
    sed -i 's/docker-compose-auto.yml/docker-compose-simple.yml/g' ../stop.sh
    echo -e "${GREEN}Updated stop.sh successfully.${NC}"
else
    echo -e "${YELLOW}Could not find stop.sh to update.${NC}"
fi

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  RocketChat setup completed!                     ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}Admin user: admin / dxIsDLnhiqKfDt5J${NC}"
echo -e "${GREEN}Bot user: heyken_bot / heyken123${NC}"
echo -e "${GREEN}Human user: heyken_user / user123${NC}"
echo -e "${GREEN}Created channels: heyken-system, heyken-logs, heyken-sandbox${NC}"
echo -e "${GREEN}You can now access RocketChat at: http://localhost:3100${NC}"
echo -e "${GREEN}==================================================${NC}"
