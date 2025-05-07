#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f ../.env ]; then
  export $(cat ../.env | grep -v '^#' | xargs)
else
  echo -e "${RED}Error: .env file not found!${NC}"
  exit 1
fi

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken - RocketChat Configuration               ${NC}"
echo -e "${GREEN}==================================================${NC}"

# Check if RocketChat is running
echo -e "${YELLOW}Checking if RocketChat is running...${NC}"
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:3100 | grep -q "200"; then
  echo -e "${RED}Error: RocketChat is not running or not accessible at http://localhost:3100${NC}"
  echo -e "${YELLOW}Please start RocketChat first:${NC}"
  echo -e "${YELLOW}cd ../docker/rocketchat && docker-compose -f docker-compose-new.yml up -d${NC}"
  exit 1
fi

echo -e "${GREEN}RocketChat is running.${NC}"
echo -e "${YELLOW}Starting automated setup...${NC}"

# Function to create a user via RocketChat API
create_user() {
  local username=$1
  local password=$2
  local email=$3
  local name=$4
  local is_admin=$5

  echo -e "${YELLOW}Creating user: ${username}...${NC}"
  
  # Check if user already exists
  local user_exists=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    http://localhost:3100/api/v1/users.info?username=$username | grep -c "success\":true")
  
  if [ "$user_exists" -eq 1 ]; then
    echo -e "${YELLOW}User ${username} already exists.${NC}"
    return 0
  fi

  # Create user
  local response=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$name\",\"email\":\"$email\",\"password\":\"$password\",\"username\":\"$username\",\"roles\":[\"user\"$([ "$is_admin" = true ] && echo ",\"admin\"")],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false}" \
    http://localhost:3100/api/v1/users.create)
  
  if echo "$response" | grep -q "success\":true"; then
    echo -e "${GREEN}User ${username} created successfully.${NC}"
    return 0
  else
    echo -e "${RED}Failed to create user ${username}.${NC}"
    echo -e "${RED}Response: ${response}${NC}"
    return 1
  fi
}

# Function to login and get auth token
login() {
  local username=$1
  local password=$2
  
  echo -e "${YELLOW}Logging in as ${username}...${NC}"
  
  local response=$(curl -s -H "Content-Type: application/json" \
    -d "{\"username\":\"$username\",\"password\":\"$password\"}" \
    http://localhost:3100/api/v1/login)
  
  if echo "$response" | grep -q "status\":\"success"; then
    local token=$(echo "$response" | grep -o '"authToken":"[^"]*' | cut -d'"' -f4)
    local user_id=$(echo "$response" | grep -o '"userId":"[^"]*' | cut -d'"' -f4)
    echo "$token:$user_id"
    return 0
  else
    echo -e "${RED}Login failed for ${username}.${NC}"
    echo -e "${RED}Response: ${response}${NC}"
    return 1
  fi
}

# Function to create a channel
create_channel() {
  local name=$1
  local type=$2 # "public" or "private"
  
  echo -e "${YELLOW}Creating ${type} channel: ${name}...${NC}"
  
  local endpoint="channels.create"
  if [ "$type" = "private" ]; then
    endpoint="groups.create"
  fi
  
  local response=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$name\"}" \
    http://localhost:3100/api/v1/$endpoint)
  
  if echo "$response" | grep -q "success\":true"; then
    echo -e "${GREEN}Channel ${name} created successfully.${NC}"
    return 0
  else
    echo -e "${RED}Failed to create channel ${name}.${NC}"
    echo -e "${RED}Response: ${response}${NC}"
    return 1
  fi
}

# Function to add a user to a channel
add_to_channel() {
  local username=$1
  local channel=$2
  local type=$3 # "public" or "private"
  
  echo -e "${YELLOW}Adding ${username} to channel ${channel}...${NC}"
  
  # Get user ID
  local user_info=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    http://localhost:3100/api/v1/users.info?username=$username)
  
  local user_id=$(echo "$user_info" | grep -o '"_id":"[^"]*' | head -1 | cut -d'"' -f4)
  
  if [ -z "$user_id" ]; then
    echo -e "${RED}Could not find user ID for ${username}.${NC}"
    return 1
  fi
  
  # Get channel ID
  local endpoint="channels.info"
  if [ "$type" = "private" ]; then
    endpoint="groups.info"
  fi
  
  local channel_info=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    http://localhost:3100/api/v1/$endpoint?roomName=$channel)
  
  local channel_id=$(echo "$channel_info" | grep -o '"_id":"[^"]*' | head -1 | cut -d'"' -f4)
  
  if [ -z "$channel_id" ]; then
    echo -e "${RED}Could not find channel ID for ${channel}.${NC}"
    return 1
  fi
  
  # Add user to channel
  endpoint="channels.invite"
  if [ "$type" = "private" ]; then
    endpoint="groups.invite"
  fi
  
  local response=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    -H "Content-Type: application/json" \
    -d "{\"roomId\":\"$channel_id\",\"userId\":\"$user_id\"}" \
    http://localhost:3100/api/v1/$endpoint)
  
  if echo "$response" | grep -q "success\":true"; then
    echo -e "${GREEN}Added ${username} to channel ${channel} successfully.${NC}"
    return 0
  else
    echo -e "${RED}Failed to add ${username} to channel ${channel}.${NC}"
    echo -e "${RED}Response: ${response}${NC}"
    return 1
  fi
}

# Step 1: Wait for RocketChat to be ready
echo -e "${YELLOW}Waiting for RocketChat to be fully ready...${NC}"

# Give RocketChat some time to initialize (it needs more time with the environment variables)
MAX_ATTEMPTS=30
ATTEMPT=0
ROCKETCHAT_READY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  echo -n "."
  # Try to connect to RocketChat
  if curl -s http://localhost:3100 > /dev/null; then
    echo -e "\n${GREEN}RocketChat is responding!${NC}"
    ROCKETCHAT_READY=true
    break
  fi
  ATTEMPT=$((ATTEMPT+1))
  sleep 5
done

if [ "$ROCKETCHAT_READY" = false ]; then
  echo -e "${RED}RocketChat is not responding after $(($MAX_ATTEMPTS * 5)) seconds.${NC}"
  echo -e "${RED}Please check the logs and try again.${NC}"
  exit 1
fi

# Wait a bit more to ensure the admin user is fully created
sleep 10

# Try to login with the admin user
echo -e "${YELLOW}Attempting to login with admin credentials...${NC}"
login_response=$(curl -s -H "Content-Type: application/json" \
  -d "{\"username\":\"${ROCKETCHAT_ADMIN_USERNAME}\",\"password\":\"${ROCKETCHAT_ADMIN_PASSWORD}\"}" \
  http://localhost:3100/api/v1/login)

if ! echo "$login_response" | grep -q "status\":\"success"; then
  echo -e "${RED}Admin login failed. RocketChat might not be properly configured.${NC}"
  echo -e "${RED}Response: ${login_response}${NC}"
  echo -e "${RED}Please check the RocketChat logs and try again.${NC}"
  echo -e "${RED}You may need to manually configure RocketChat at http://localhost:3100${NC}"
  exit 1
fi

echo -e "${GREEN}RocketChat is ready and admin login successful.${NC}"

# Step 2: Login as admin
auth_info=$(login "${ROCKETCHAT_ADMIN_USERNAME}" "${ROCKETCHAT_ADMIN_PASSWORD}")
if [ $? -ne 0 ]; then
  exit 1
fi

ADMIN_TOKEN=$(echo "$auth_info" | cut -d':' -f1)
ADMIN_ID=$(echo "$auth_info" | cut -d':' -f2)

if [ -z "$ADMIN_TOKEN" ] || [ -z "$ADMIN_ID" ]; then
  echo -e "${RED}Failed to get admin authentication information.${NC}"
  exit 1
fi

echo -e "${GREEN}Admin login successful.${NC}"

# Step 3: Create users
create_user "${ROCKETCHAT_BOT_USERNAME}" "${ROCKETCHAT_BOT_PASSWORD}" "${ROCKETCHAT_BOT_EMAIL}" "Heyken Bot" false
create_user "${ROCKETCHAT_HUMAN_USERNAME}" "${ROCKETCHAT_HUMAN_PASSWORD}" "${ROCKETCHAT_HUMAN_EMAIL}" "Human User" false

# Step 4: Create channels
create_channel "general" "public"
create_channel "heyken-system" "public"
create_channel "heyken-logs" "public"
create_channel "heyken-sandbox" "private"

# Step 5: Add users to channels
add_to_channel "${ROCKETCHAT_BOT_USERNAME}" "general" "public"
add_to_channel "${ROCKETCHAT_BOT_USERNAME}" "heyken-system" "public"
add_to_channel "${ROCKETCHAT_BOT_USERNAME}" "heyken-logs" "public"
add_to_channel "${ROCKETCHAT_BOT_USERNAME}" "heyken-sandbox" "private"

add_to_channel "${ROCKETCHAT_HUMAN_USERNAME}" "general" "public"
add_to_channel "${ROCKETCHAT_HUMAN_USERNAME}" "heyken-system" "public"
add_to_channel "${ROCKETCHAT_HUMAN_USERNAME}" "heyken-logs" "public"
add_to_channel "${ROCKETCHAT_HUMAN_USERNAME}" "heyken-sandbox" "private"

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  RocketChat configuration completed!             ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}Admin user: ${ROCKETCHAT_ADMIN_USERNAME} / ${ROCKETCHAT_ADMIN_PASSWORD}${NC}"
echo -e "${GREEN}Bot user: ${ROCKETCHAT_BOT_USERNAME} / ${ROCKETCHAT_BOT_PASSWORD}${NC}"
echo -e "${GREEN}Human user: ${ROCKETCHAT_HUMAN_USERNAME} / ${ROCKETCHAT_HUMAN_PASSWORD}${NC}"
echo -e "${GREEN}Created channels: general, heyken-system, heyken-logs, heyken-sandbox${NC}"
echo -e "${GREEN}You can now access RocketChat at: http://localhost:3100${NC}"
echo -e "${GREEN}Login with: ${ROCKETCHAT_HUMAN_USERNAME} / ${ROCKETCHAT_HUMAN_PASSWORD}${NC}"
