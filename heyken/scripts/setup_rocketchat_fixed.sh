#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken - Complete RocketChat Setup              ${NC}"
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
docker-compose -f docker-compose-auto.yml down -v 2>/dev/null || true
docker-compose -f docker-compose-new.yml down -v 2>/dev/null || true
docker-compose -f docker-compose-simple.yml down -v 2>/dev/null || true
docker-compose down -v 2>/dev/null || true
cd ../..

# 2. Clean up data directories
echo -e "${YELLOW}Cleaning up data directories...${NC}"
sudo rm -rf docker/rocketchat/data_auto docker/rocketchat/data_new docker/rocketchat/data docker/rocketchat/data_simple 2>/dev/null || true

# 3. Build the custom RocketChat image with auto-configuration
echo -e "${YELLOW}Building custom RocketChat image...${NC}"
cd docker/rocketchat
docker build -t heyken/rocketchat:auto .
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to build custom RocketChat image!${NC}"
  cd ../..
  exit 1
fi
cd ../..

# 4. Create a docker-compose file that uses the custom image
echo -e "${YELLOW}Creating docker-compose file with custom image...${NC}"
cat > docker/rocketchat/docker-compose-custom.yml << 'EOF'
version: '3'

services:
  mongodb:
    image: mongo:5.0
    restart: always
    volumes:
      - ./data_custom/db:/data/db
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
    image: heyken/rocketchat:auto
    restart: always
    volumes:
      - ./uploads_custom:/app/uploads
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

# 5. Start RocketChat with the custom configuration
echo -e "${YELLOW}Starting RocketChat with custom configuration...${NC}"
cd docker/rocketchat
docker-compose -f docker-compose-custom.yml up -d
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to start RocketChat with custom configuration!${NC}"
  cd ../..
  exit 1
fi
cd ../..

# 6. Wait for RocketChat to be ready
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

# 7. Wait a bit more to ensure RocketChat is fully initialized
echo -e "${YELLOW}Waiting for RocketChat to fully initialize...${NC}"
sleep 15

# 8. Create bot and human users using the RocketChat API
echo -e "${YELLOW}Creating users and channels...${NC}"

# Login as admin
echo -e "${YELLOW}Logging in as admin...${NC}"
LOGIN_RESPONSE=$(curl -s -H "Content-Type: application/json" \
  -d "{\"username\":\"${ROCKETCHAT_ADMIN_USERNAME:-admin}\",\"password\":\"${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}\"}" \
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
BOT_USERNAME=${ROCKETCHAT_BOT_USERNAME:-heyken_bot}

# Check if the bot user already exists
BOT_INFO_RESPONSE=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  "http://localhost:3100/api/v1/users.info?username=$BOT_USERNAME")

if echo "$BOT_INFO_RESPONSE" | grep -q "success":true; then
  echo -e "${YELLOW}Bot user $BOT_USERNAME already exists.${NC}"
else
  # Create the bot user
  BOT_RESPONSE=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"Heyken Bot\",\"email\":\"${ROCKETCHAT_BOT_EMAIL:-bot@heyken.local}\",\"password\":\"${ROCKETCHAT_BOT_PASSWORD:-heyken123}\",\"username\":\"$BOT_USERNAME\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false}" \
    http://localhost:3100/api/v1/users.create")
  
  if echo "$BOT_RESPONSE" | grep -q "success":true; then
    echo -e "${GREEN}Bot user created successfully.${NC}"
  elif echo "$BOT_RESPONSE" | grep -q "already in use"; then
    echo -e "${YELLOW}Bot user already exists.${NC}"
  else
    echo -e "${RED}Failed to create bot user. Response: ${BOT_RESPONSE}${NC}"
  fi
fi

# Create human user (use heyken_user instead of user as it's a reserved name)
echo -e "${YELLOW}Creating human user...${NC}"
HUMAN_USERNAME=${ROCKETCHAT_HUMAN_USERNAME:-heyken_user}

# Check if the human user already exists
USER_INFO_RESPONSE=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  "http://localhost:3100/api/v1/users.info?username=$HUMAN_USERNAME")

if echo "$USER_INFO_RESPONSE" | grep -q "success":true; then
  echo -e "${YELLOW}Human user $HUMAN_USERNAME already exists.${NC}"
else
  # Create the human user
  HUMAN_RESPONSE=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"Human User\",\"email\":\"${ROCKETCHAT_HUMAN_EMAIL:-user@heyken.local}\",\"password\":\"${ROCKETCHAT_HUMAN_PASSWORD:-user123}\",\"username\":\"$HUMAN_USERNAME\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false}" \
    http://localhost:3100/api/v1/users.create")
  
  if echo "$HUMAN_RESPONSE" | grep -q "success":true; then
    echo -e "${GREEN}Human user created successfully.${NC}"
  elif echo "$HUMAN_RESPONSE" | grep -q "already in use"; then
    echo -e "${YELLOW}Human user already exists.${NC}"
  elif echo "$HUMAN_RESPONSE" | grep -q "blocked and can't be used"; then
    # If 'user' is blocked, try with 'heyken_human'
    echo -e "${YELLOW}Username $HUMAN_USERNAME is blocked. Trying with heyken_human...${NC}"
    HUMAN_USERNAME="heyken_human"
    HUMAN_RESPONSE=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"Human User\",\"email\":\"${ROCKETCHAT_HUMAN_EMAIL:-user@heyken.local}\",\"password\":\"${ROCKETCHAT_HUMAN_PASSWORD:-user123}\",\"username\":\"$HUMAN_USERNAME\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false}" \
      http://localhost:3100/api/v1/users.create")
    
    if echo "$HUMAN_RESPONSE" | grep -q "success":true; then
      echo -e "${GREEN}Human user created successfully with username $HUMAN_USERNAME.${NC}"
    else
      echo -e "${RED}Failed to create human user. Response: ${HUMAN_RESPONSE}${NC}"
    fi
  else
    echo -e "${RED}Failed to create human user. Response: ${HUMAN_RESPONSE}${NC}"
  fi
fi

# Create channels
echo -e "${YELLOW}Creating channels...${NC}"
CHANNELS=("heyken-system" "heyken-logs" "heyken-sandbox")
CHANNEL_TYPES=("public" "public" "private")

for i in "${!CHANNELS[@]}"; do
  CHANNEL="${CHANNELS[$i]}"
  TYPE="${CHANNEL_TYPES[$i]}"
  
  # First check if the channel already exists
  if [ "$TYPE" = "private" ]; then
    # For private channels, use groups.info
    INFO_ENDPOINT="groups.info"
    CREATE_ENDPOINT="groups.create"
  else
    # For public channels, use channels.info
    INFO_ENDPOINT="channels.info"
    CREATE_ENDPOINT="channels.create"
  fi
  
  # Try to get channel info
  echo -e "${YELLOW}Checking if ${TYPE} channel ${CHANNEL} exists...${NC}"
  CHANNEL_INFO=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    "http://localhost:3100/api/v1/$INFO_ENDPOINT?roomName=$CHANNEL")
  
  if echo "$CHANNEL_INFO" | grep -q "success":true; then
    echo -e "${YELLOW}Channel ${CHANNEL} already exists.${NC}"
  else
    # Create the channel if it doesn't exist
    echo -e "${YELLOW}Creating ${TYPE} channel: ${CHANNEL}...${NC}"
    CHANNEL_RESPONSE=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"$CHANNEL\"}" \
      "http://localhost:3100/api/v1/$CREATE_ENDPOINT")
    
    if echo "$CHANNEL_RESPONSE" | grep -q "success":true; then
      echo -e "${GREEN}Channel ${CHANNEL} created successfully.${NC}"
    elif echo "$CHANNEL_RESPONSE" | grep -q "already in use"; then
      echo -e "${YELLOW}Channel ${CHANNEL} already exists.${NC}"
    else
      echo -e "${RED}Failed to create channel ${CHANNEL}. Response: ${CHANNEL_RESPONSE}${NC}"
    fi
  fi
done

# 9. Update the run_heyken.sh script to use our custom docker-compose file
echo -e "${YELLOW}Updating run_heyken.sh to use custom RocketChat configuration...${NC}"
if [ -f ../../run_heyken.sh ]; then
    sed -i 's/docker-compose-auto.yml/docker-compose-custom.yml/g' ../../run_heyken.sh
    sed -i 's/docker-compose-new.yml/docker-compose-custom.yml/g' ../../run_heyken.sh
    echo -e "${GREEN}Updated run_heyken.sh successfully.${NC}"
else
    echo -e "${YELLOW}Could not find run_heyken.sh to update.${NC}"
fi

# 10. Update the stop.sh script to handle the custom docker-compose file
echo -e "${YELLOW}Updating stop.sh to handle custom RocketChat configuration...${NC}"
if [ -f ../../stop.sh ]; then
    sed -i 's/docker-compose-auto.yml/docker-compose-custom.yml/g' ../../stop.sh
    echo -e "${GREEN}Updated stop.sh successfully.${NC}"
else
    echo -e "${YELLOW}Could not find stop.sh to update.${NC}"
fi

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  RocketChat setup completed!                     ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}Admin user: ${ROCKETCHAT_ADMIN_USERNAME:-admin} / ${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}${NC}"
echo -e "${GREEN}Bot user: ${ROCKETCHAT_BOT_USERNAME:-heyken_bot} / ${ROCKETCHAT_BOT_PASSWORD:-heyken123}${NC}"
echo -e "${GREEN}Human user: ${HUMAN_USERNAME} / ${ROCKETCHAT_HUMAN_PASSWORD:-user123}${NC}"
echo -e "${GREEN}Created channels: heyken-system, heyken-logs, heyken-sandbox${NC}"
echo -e "${GREEN}You can now access RocketChat at: http://localhost:3100${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}After verifying RocketChat is properly configured,${NC}"
echo -e "${GREEN}you can continue with the Heyken deployment by running:${NC}"
echo -e "${GREEN}./continue_heyken_deployment.sh                   ${NC}"
echo -e "${GREEN}==================================================${NC}"
