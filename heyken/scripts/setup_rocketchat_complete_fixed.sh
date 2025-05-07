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

# Set default credentials with a different admin username
ADMIN_USERNAME="heyken_admin"
ADMIN_PASSWORD=${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}
ADMIN_EMAIL=${ROCKETCHAT_ADMIN_EMAIL:-admin@heyken.local}
BOT_USERNAME=${ROCKETCHAT_BOT_USERNAME:-heyken_bot}
BOT_PASSWORD=${ROCKETCHAT_BOT_PASSWORD:-heyken123}
BOT_EMAIL=${ROCKETCHAT_BOT_EMAIL:-bot@heyken.local}
HUMAN_USERNAME="heyken_user"  # Fixed username that won't be blocked
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
docker-compose -f docker-compose-reliable.yml down -v 2>/dev/null || true
docker-compose -f docker-compose-final.yml down -v 2>/dev/null || true
docker-compose -f docker-compose-logs.yml down -v 2>/dev/null || true
cd ../..

# 2. Clean up data directories
echo -e "${YELLOW}Cleaning up data directories...${NC}"
sudo rm -rf docker/rocketchat/data_auto docker/rocketchat/data_new docker/rocketchat/data docker/rocketchat/data_simple docker/rocketchat/data_custom docker/rocketchat/data_reliable docker/rocketchat/data_final docker/rocketchat/data_logs 2>/dev/null || true

# 3. Create a docker-compose file for RocketChat with proper mail settings
echo -e "${YELLOW}Creating docker-compose file...${NC}"
cat > docker/rocketchat/docker-compose-complete.yml << EOF
version: '3'

services:
  mongodb:
    image: mongo:5.0
    restart: always
    volumes:
      - ./data_complete/db:/data/db
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
      - ./uploads_complete:/app/uploads
    environment:
      - ROOT_URL=http://localhost:3100
      - PORT=3000
      - MONGO_URL=mongodb://mongodb:27017/rocketchat
      - MONGO_OPLOG_URL=mongodb://mongodb:27017/local
      - OVERWRITE_SETTING_Show_Setup_Wizard=completed
      - MAIL_URL=smtp://dummy:dummy@localhost:25
      - OVERWRITE_SETTING_Email_Verification=false
      - OVERWRITE_SETTING_Accounts_EmailVerification=false
      - OVERWRITE_SETTING_Accounts_ManuallyApproveNewUsers=false
      - OVERWRITE_SETTING_Accounts_AllowEmailChange=true
      - OVERWRITE_SETTING_Accounts_AllowPasswordChange=true
      - OVERWRITE_SETTING_Accounts_RequirePasswordConfirmation=false
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
docker-compose -f docker-compose-complete.yml up -d
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
  echo -e "${YELLOW}Please try to complete the setup manually at http://localhost:3100${NC}"
  echo -e "${YELLOW}You can register a new user with these credentials:${NC}"
  echo -e "${YELLOW}Username: $ADMIN_USERNAME${NC}"
  echo -e "${YELLOW}Password: $ADMIN_PASSWORD${NC}"
  echo -e "${YELLOW}Email: $ADMIN_EMAIL${NC}"
  exit 1
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
  -d "{\"name\":\"Heyken Bot\",\"email\":\"$BOT_EMAIL\",\"password\":\"$BOT_PASSWORD\",\"username\":\"$BOT_USERNAME\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false,\"verified\":true}" \
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
  -d "{\"name\":\"Human User\",\"email\":\"$HUMAN_EMAIL\",\"password\":\"$HUMAN_PASSWORD\",\"username\":\"$HUMAN_USERNAME\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false,\"verified\":true}" \
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

# 11. Add users to channels
echo -e "${YELLOW}Adding users to channels...${NC}"

# Get bot user ID
BOT_INFO=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  "http://localhost:3100/api/v1/users.info?username=$BOT_USERNAME")
  
BOT_ID=$(echo "$BOT_INFO" | grep -o '"_id":"[^"]*' | cut -d'"' -f4)

# Get human user ID
HUMAN_INFO=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  "http://localhost:3100/api/v1/users.info?username=$HUMAN_USERNAME")
  
HUMAN_ID=$(echo "$HUMAN_INFO" | grep -o '"_id":"[^"]*' | cut -d'"' -f4)

# Add users to public channels
for CHANNEL in "heyken-system" "heyken-logs"; do
  # Get channel ID
  CHANNEL_INFO=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    "http://localhost:3100/api/v1/channels.info?roomName=$CHANNEL")
    
  CHANNEL_ID=$(echo "$CHANNEL_INFO" | grep -o '"_id":"[^"]*' | cut -d'"' -f4)
  
  # Add bot to channel
  if [ ! -z "$BOT_ID" ] && [ ! -z "$CHANNEL_ID" ]; then
    echo -e "${YELLOW}Adding bot to channel ${CHANNEL}...${NC}"
    curl -s -X POST \
      -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
      -H "Content-Type: application/json" \
      -d "{\"roomId\":\"$CHANNEL_ID\",\"userId\":\"$BOT_ID\"}" \
      "http://localhost:3100/api/v1/channels.invite" > /dev/null
  fi
  
  # Add human to channel
  if [ ! -z "$HUMAN_ID" ] && [ ! -z "$CHANNEL_ID" ]; then
    echo -e "${YELLOW}Adding human user to channel ${CHANNEL}...${NC}"
    curl -s -X POST \
      -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
      -H "Content-Type: application/json" \
      -d "{\"roomId\":\"$CHANNEL_ID\",\"userId\":\"$HUMAN_ID\"}" \
      "http://localhost:3100/api/v1/channels.invite" > /dev/null
  fi
done

# Add users to private channel
CHANNEL="heyken-sandbox"
# Get channel ID
CHANNEL_INFO=$(curl -s -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  "http://localhost:3100/api/v1/groups.info?roomName=$CHANNEL")
  
CHANNEL_ID=$(echo "$CHANNEL_INFO" | grep -o '"_id":"[^"]*' | cut -d'"' -f4)

# Add bot to channel
if [ ! -z "$BOT_ID" ] && [ ! -z "$CHANNEL_ID" ]; then
  echo -e "${YELLOW}Adding bot to channel ${CHANNEL}...${NC}"
  curl -s -X POST \
    -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -d "{\"roomId\":\"$CHANNEL_ID\",\"userId\":\"$BOT_ID\"}" \
    "http://localhost:3100/api/v1/groups.invite" > /dev/null
fi

# Add human to channel
if [ ! -z "$HUMAN_ID" ] && [ ! -z "$CHANNEL_ID" ]; then
  echo -e "${YELLOW}Adding human user to channel ${CHANNEL}...${NC}"
  curl -s -X POST \
    -H "X-Auth-Token: $AUTH_TOKEN" -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -d "{\"roomId\":\"$CHANNEL_ID\",\"userId\":\"$HUMAN_ID\"}" \
    "http://localhost:3100/api/v1/groups.invite" > /dev/null
fi

# 12. Update the run_heyken.sh script to use our complete docker-compose file
echo -e "${YELLOW}Updating run_heyken.sh to use complete RocketChat configuration...${NC}"
if [ -f ../run_heyken.sh ]; then
    sed -i 's/docker-compose-simple.yml/docker-compose-complete.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-custom.yml/docker-compose-complete.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-auto.yml/docker-compose-complete.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-new.yml/docker-compose-complete.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-reliable.yml/docker-compose-complete.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-final.yml/docker-compose-complete.yml/g' ../run_heyken.sh
    sed -i 's/docker-compose-logs.yml/docker-compose-complete.yml/g' ../run_heyken.sh
    echo -e "${GREEN}Updated run_heyken.sh successfully.${NC}"
else
    echo -e "${YELLOW}Could not find run_heyken.sh to update.${NC}"
fi

# 13. Update the stop.sh script to handle the complete docker-compose file
echo -e "${YELLOW}Updating stop.sh to handle complete RocketChat configuration...${NC}"
if [ -f ../stop.sh ]; then
    sed -i 's/docker-compose-simple.yml/docker-compose-complete.yml/g' ../stop.sh
    sed -i 's/docker-compose-custom.yml/docker-compose-complete.yml/g' ../stop.sh
    sed -i 's/docker-compose-auto.yml/docker-compose-complete.yml/g' ../stop.sh
    sed -i 's/docker-compose-new.yml/docker-compose-complete.yml/g' ../stop.sh
    sed -i 's/docker-compose-reliable.yml/docker-compose-complete.yml/g' ../stop.sh
    sed -i 's/docker-compose-final.yml/docker-compose-complete.yml/g' ../stop.sh
    sed -i 's/docker-compose-logs.yml/docker-compose-complete.yml/g' ../stop.sh
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
echo -e "${YELLOW}To view RocketChat logs at any time, run:${NC}"
echo -e "${YELLOW}docker logs rocketchat-rocketchat-1${NC}"
echo -e "${GREEN}==================================================${NC}"
