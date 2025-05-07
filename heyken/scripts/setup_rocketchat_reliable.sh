#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken - Reliable RocketChat Setup              ${NC}"
echo -e "${GREEN}==================================================${NC}"

# Load environment variables
if [ -f ../.env ]; then
  export $(cat ../.env | grep -v '^#' | xargs)
else
  echo -e "${RED}Error: .env file not found!${NC}"
  exit 1
fi

# Set default credentials if not provided in .env
ADMIN_USERNAME=${ROCKETCHAT_ADMIN_USERNAME:-admin}
ADMIN_PASSWORD=${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}
ADMIN_EMAIL=${ROCKETCHAT_ADMIN_EMAIL:-admin@heyken.local}
BOT_USERNAME=${ROCKETCHAT_BOT_USERNAME:-heyken_bot}
BOT_PASSWORD=${ROCKETCHAT_BOT_PASSWORD:-heyken123}
BOT_EMAIL=${ROCKETCHAT_BOT_EMAIL:-bot@heyken.local}
HUMAN_USERNAME=${ROCKETCHAT_HUMAN_USERNAME:-heyken_user}
HUMAN_PASSWORD=${ROCKETCHAT_HUMAN_PASSWORD:-user123}
HUMAN_EMAIL=${ROCKETCHAT_HUMAN_EMAIL:-user@heyken.local}

# 1. Stop any running RocketChat instances
echo -e "${YELLOW}Stopping any running RocketChat instances...${NC}"
cd ../docker/rocketchat
docker-compose down -v 2>/dev/null || true
docker-compose -f docker-compose-auto.yml down -v 2>/dev/null || true
docker-compose -f docker-compose-new.yml down -v 2>/dev/null || true
docker-compose -f docker-compose-simple.yml down -v 2>/dev/null || true
docker-compose -f docker-compose-custom.yml down -v 2>/dev/null || true
cd ../..

# 2. Clean up data directories
echo -e "${YELLOW}Cleaning up data directories...${NC}"
sudo rm -rf docker/rocketchat/data_auto docker/rocketchat/data_new docker/rocketchat/data docker/rocketchat/data_simple docker/rocketchat/data_custom 2>/dev/null || true

# 3. Create a docker-compose file for RocketChat
echo -e "${YELLOW}Creating docker-compose file...${NC}"
cat > docker/rocketchat/docker-compose-reliable.yml << EOF
version: '3'

services:
  mongodb:
    image: mongo:5.0
    restart: always
    volumes:
      - ./data_reliable/db:/data/db
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
    image: registry.rocket.chat/rocketchat/rocket.chat:7.5.1
    restart: always
    volumes:
      - ./uploads_reliable:/app/uploads
    environment:
      - ROOT_URL=http://localhost:3100
      - PORT=3000
      - MONGO_URL=mongodb://mongodb:27017/rocketchat
      - MONGO_OPLOG_URL=mongodb://mongodb:27017/local
      - OVERWRITE_SETTING_Show_Setup_Wizard=completed
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

# 4. Start RocketChat
echo -e "${YELLOW}Starting RocketChat...${NC}"
cd docker/rocketchat
docker-compose -f docker-compose-reliable.yml up -d
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to start RocketChat!${NC}"
  cd ../..
  exit 1
fi
cd ../..

# 5. Wait for RocketChat to be ready
echo -e "${YELLOW}Waiting for RocketChat to be ready...${NC}"
MAX_ATTEMPTS=60
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
sleep 30

# 7. Complete the setup wizard using the API
echo -e "${YELLOW}Completing setup wizard...${NC}"

# Register the admin user
echo -e "${YELLOW}Registering admin user...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$ADMIN_USERNAME\",\"email\":\"$ADMIN_EMAIL\",\"pass\":\"$ADMIN_PASSWORD\",\"name\":\"Administrator\"}" \
  http://localhost:3100/api/v1/users.register)

if echo "$REGISTER_RESPONSE" | grep -q "success\":true"; then
  echo -e "${GREEN}Admin user registered successfully.${NC}"
else
  echo -e "${YELLOW}Admin user registration response: ${REGISTER_RESPONSE}${NC}"
  echo -e "${YELLOW}Continuing anyway as the user might already exist...${NC}"
fi

# Try to login as admin
echo -e "${YELLOW}Logging in as admin...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$ADMIN_USERNAME\",\"password\":\"$ADMIN_PASSWORD\"}" \
  http://localhost:3100/api/v1/login)

if ! echo "$LOGIN_RESPONSE" | grep -q "status\":\"success"; then
  echo -e "${RED}Failed to login as admin. Response: ${LOGIN_RESPONSE}${NC}"
  echo -e "${YELLOW}Trying to login with default admin credentials...${NC}"
  
  # Try with default admin credentials
  LOGIN_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin"}' \
    http://localhost:3100/api/v1/login)
    
  if ! echo "$LOGIN_RESPONSE" | grep -q "status\":\"success"; then
    echo -e "${RED}Failed to login with default admin credentials.${NC}"
    echo -e "${YELLOW}Please try to complete the setup manually at http://localhost:3100${NC}"
    exit 1
  else
    echo -e "${GREEN}Logged in with default admin credentials.${NC}"
    echo -e "${YELLOW}Changing default admin password...${NC}"
    
    # Extract auth token and user ID
    AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"authToken":"[^"]*' | cut -d'"' -f4)
    USER_ID=$(echo "$LOGIN_RESPONSE" | grep -o '"userId":"[^"]*' | cut -d'"' -f4)
    
    # Change admin password
    CHANGE_PASSWORD_RESPONSE=$(curl -s -X POST \
      -H "X-Auth-Token: $AUTH_TOKEN" \
      -H "X-User-Id: $USER_ID" \
      -H "Content-Type: application/json" \
      -d "{\"currentPassword\":\"admin\",\"newPassword\":\"$ADMIN_PASSWORD\"}" \
      http://localhost:3100/api/v1/users.update-own-password)
      
    if echo "$CHANGE_PASSWORD_RESPONSE" | grep -q "success\":true"; then
      echo -e "${GREEN}Admin password changed successfully.${NC}"
    else
      echo -e "${RED}Failed to change admin password. Response: ${CHANGE_PASSWORD_RESPONSE}${NC}"
    fi
  fi
else
  echo -e "${GREEN}Logged in as admin successfully.${NC}"
  
  # Extract auth token and user ID
  AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"authToken":"[^"]*' | cut -d'"' -f4)
  USER_ID=$(echo "$LOGIN_RESPONSE" | grep -o '"userId":"[^"]*' | cut -d'"' -f4)
fi

# 8. Create bot user
echo -e "${YELLOW}Creating bot user...${NC}"
BOT_RESPONSE=$(curl -s -X POST \
  -H "X-Auth-Token: $AUTH_TOKEN" \
  -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Heyken Bot\",\"email\":\"$BOT_EMAIL\",\"password\":\"$BOT_PASSWORD\",\"username\":\"$BOT_USERNAME\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false}" \
  http://localhost:3100/api/v1/users.create)

if echo "$BOT_RESPONSE" | grep -q "success\":true"; then
  echo -e "${GREEN}Bot user created successfully.${NC}"
elif echo "$BOT_RESPONSE" | grep -q "already in use"; then
  echo -e "${YELLOW}Bot user already exists.${NC}"
else
  echo -e "${RED}Failed to create bot user. Response: ${BOT_RESPONSE}${NC}"
fi

# 9. Create human user
echo -e "${YELLOW}Creating human user...${NC}"
HUMAN_RESPONSE=$(curl -s -X POST \
  -H "X-Auth-Token: $AUTH_TOKEN" \
  -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Human User\",\"email\":\"$HUMAN_EMAIL\",\"password\":\"$HUMAN_PASSWORD\",\"username\":\"$HUMAN_USERNAME\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false}" \
  http://localhost:3100/api/v1/users.create)

if echo "$HUMAN_RESPONSE" | grep -q "success\":true"; then
  echo -e "${GREEN}Human user created successfully.${NC}"
elif echo "$HUMAN_RESPONSE" | grep -q "already in use"; then
  echo -e "${YELLOW}Human user already exists.${NC}"
else
  echo -e "${RED}Failed to create human user. Response: ${HUMAN_RESPONSE}${NC}"
fi

# 10. Create channels
echo -e "${YELLOW}Creating channels...${NC}"
CHANNELS=("heyken-system" "heyken-logs" "heyken-sandbox")
CHANNEL_TYPES=("public" "public" "private")

for i in "${!CHANNELS[@]}"; do
  CHANNEL="${CHANNELS[$i]}"
  TYPE="${CHANNEL_TYPES[$i]}"
  
  ENDPOINT="channels.create"
  if [ "$TYPE" = "private" ]; then
    ENDPOINT="groups.create"
  fi
  
  echo -e "${YELLOW}Creating ${TYPE} channel: ${CHANNEL}...${NC}"
  CHANNEL_RESPONSE=$(curl -s -X POST \
    -H "X-Auth-Token: $AUTH_TOKEN" \
    -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$CHANNEL\"}" \
    "http://localhost:3100/api/v1/$ENDPOINT")
  
  if echo "$CHANNEL_RESPONSE" | grep -q "success\":true"; then
    echo -e "${GREEN}Channel ${CHANNEL} created successfully.${NC}"
  elif echo "$CHANNEL_RESPONSE" | grep -q "name-already-exists\|already in use"; then
    echo -e "${YELLOW}Channel ${CHANNEL} already exists.${NC}"
  else
    echo -e "${RED}Failed to create channel ${CHANNEL}. Response: ${CHANNEL_RESPONSE}${NC}"
  fi
done

# 11. Update the run_heyken.sh script to use our reliable docker-compose file
echo -e "${YELLOW}Updating run_heyken.sh to use reliable RocketChat configuration...${NC}"
if [ -f ../run_heyken.sh ]; then
    sed -i 's/docker-compose-simple.yml/docker-compose-reliable.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-custom.yml/docker-compose-reliable.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-auto.yml/docker-compose-reliable.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-new.yml/docker-compose-reliable.yml/g' ../run_heyken.sh
    echo -e "${GREEN}Updated run_heyken.sh successfully.${NC}"
else
    echo -e "${YELLOW}Could not find run_heyken.sh to update.${NC}"
fi

# 12. Update the stop.sh script to handle the reliable docker-compose file
echo -e "${YELLOW}Updating stop.sh to handle reliable RocketChat configuration...${NC}"
if [ -f ../stop.sh ]; then
    sed -i 's/docker-compose-simple.yml/docker-compose-reliable.yml/g' ../stop.sh
    sed -i 's/docker-compose-custom.yml/docker-compose-reliable.yml/g' ../stop.sh
    sed -i 's/docker-compose-auto.yml/docker-compose-reliable.yml/g' ../stop.sh
    sed -i 's/docker-compose-new.yml/docker-compose-reliable.yml/g' ../stop.sh
    echo -e "${GREEN}Updated stop.sh successfully.${NC}"
else
    echo -e "${YELLOW}Could not find stop.sh to update.${NC}"
fi

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  RocketChat setup completed!                     ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}Admin user: $ADMIN_USERNAME / $ADMIN_PASSWORD${NC}"
echo -e "${GREEN}Bot user: $BOT_USERNAME / $BOT_PASSWORD${NC}"
echo -e "${GREEN}Human user: $HUMAN_USERNAME / $HUMAN_PASSWORD${NC}"
echo -e "${GREEN}Created channels: heyken-system, heyken-logs, heyken-sandbox${NC}"
echo -e "${GREEN}You can now access RocketChat at: http://localhost:3100${NC}"
echo -e "${GREEN}==================================================${NC}"
