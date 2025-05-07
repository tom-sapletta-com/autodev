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

# Configuration
ROCKETCHAT_URL="http://localhost:3100"
ADMIN_USERNAME="${ROCKETCHAT_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}"
ADMIN_EMAIL="${ROCKETCHAT_ADMIN_EMAIL:-admin@heyken.local}"
BOT_USERNAME="${ROCKETCHAT_BOT_USERNAME:-heyken_bot}"
BOT_PASSWORD="${ROCKETCHAT_BOT_PASSWORD:-heyken123}"
BOT_EMAIL="${ROCKETCHAT_BOT_EMAIL:-bot@heyken.local}"
HUMAN_USERNAME="${ROCKETCHAT_HUMAN_USERNAME:-user}"
HUMAN_PASSWORD="${ROCKETCHAT_HUMAN_PASSWORD:-user123}"
HUMAN_EMAIL="${ROCKETCHAT_HUMAN_EMAIL:-user@heyken.local}"

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken - RocketChat API Setup                   ${NC}"
echo -e "${GREEN}==================================================${NC}"

# Function to check if RocketChat is accessible
check_rocketchat() {
  echo -e "${YELLOW}Checking if RocketChat is accessible...${NC}"
  if ! curl -s "$ROCKETCHAT_URL/api/info" > /dev/null; then
    echo -e "${RED}Error: RocketChat is not accessible at $ROCKETCHAT_URL${NC}"
    echo -e "${YELLOW}Please make sure RocketChat is running.${NC}"
    exit 1
  fi
  echo -e "${GREEN}RocketChat is accessible.${NC}"
}

# Function to complete the setup wizard
complete_setup_wizard() {
  echo -e "${YELLOW}Completing setup wizard...${NC}"
  
  # Step 1: Organization info
  echo -e "${YELLOW}Setting up organization info...${NC}"
  curl -s -X POST -H "Content-Type: application/json" \
    -d "{\"organizationType\":\"community\",\"organizationName\":\"Heyken\",\"organizationIndustry\":\"technology\",\"organizationSize\":\"1-10\",\"country\":\"worldwide\",\"language\":\"en\",\"serverType\":\"on-premise\",\"registrationOptIn\":false,\"agreePrivacyTerms\":true,\"agreeTerms\":true}" \
    "$ROCKETCHAT_URL/api/v1/setupWizard" > /dev/null
  
  # Step 2: Admin user
  echo -e "${YELLOW}Creating admin user...${NC}"
  curl -s -X POST -H "Content-Type: application/json" \
    -d "{\"username\":\"$ADMIN_USERNAME\",\"password\":\"$ADMIN_PASSWORD\",\"email\":\"$ADMIN_EMAIL\",\"name\":\"Administrator\"}" \
    "$ROCKETCHAT_URL/api/v1/setupWizard/admin-user" > /dev/null
  
  echo -e "${GREEN}Setup wizard completed.${NC}"
  
  # Wait for setup to complete
  echo -e "${YELLOW}Waiting for setup to complete...${NC}"
  sleep 5
}

# Function to login and get auth token
login() {
  echo -e "${YELLOW}Logging in as $1...${NC}"
  
  local username=$1
  local password=$2
  
  local response=$(curl -s -H "Content-Type: application/json" \
    -d "{\"username\":\"$username\",\"password\":\"$password\"}" \
    "$ROCKETCHAT_URL/api/v1/login")
  
  if echo "$response" | grep -q "status\":\"success"; then
    local token=$(echo "$response" | grep -o '"authToken":"[^"]*' | cut -d'"' -f4)
    local user_id=$(echo "$response" | grep -o '"userId":"[^"]*' | cut -d'"' -f4)
    echo "$token:$user_id"
    return 0
  else
    echo -e "${RED}Login failed for $username.${NC}"
    echo -e "${RED}Response: $response${NC}"
    return 1
  fi
}

# Function to create a user
create_user() {
  local username=$1
  local password=$2
  local email=$3
  local name=$4
  
  echo -e "${YELLOW}Creating user: $username...${NC}"
  
  local response=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$name\",\"email\":\"$email\",\"password\":\"$password\",\"username\":\"$username\",\"roles\":[\"user\"],\"joinDefaultChannels\":true,\"requirePasswordChange\":false,\"sendWelcomeEmail\":false}" \
    "$ROCKETCHAT_URL/api/v1/users.create")
  
  if echo "$response" | grep -q "success\":true"; then
    echo -e "${GREEN}User $username created successfully.${NC}"
    return 0
  else
    # Check if user already exists
    if echo "$response" | grep -q "Username is already in use"; then
      echo -e "${YELLOW}User $username already exists.${NC}"
      return 0
    else
      echo -e "${RED}Failed to create user $username.${NC}"
      echo -e "${RED}Response: $response${NC}"
      return 1
    fi
  fi
}

# Function to create a channel
create_channel() {
  local name=$1
  local type=$2 # "public" or "private"
  
  echo -e "${YELLOW}Creating $type channel: $name...${NC}"
  
  local endpoint="channels.create"
  if [ "$type" = "private" ]; then
    endpoint="groups.create"
  fi
  
  local response=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$name\"}" \
    "$ROCKETCHAT_URL/api/v1/$endpoint")
  
  if echo "$response" | grep -q "success\":true"; then
    echo -e "${GREEN}Channel $name created successfully.${NC}"
    return 0
  else
    # Check if channel already exists
    if echo "$response" | grep -q "Channel name is already in use"; then
      echo -e "${YELLOW}Channel $name already exists.${NC}"
      return 0
    else
      echo -e "${RED}Failed to create channel $name.${NC}"
      echo -e "${RED}Response: $response${NC}"
      return 1
    fi
  fi
}

# Function to add a user to a channel
add_to_channel() {
  local username=$1
  local channel=$2
  local type=$3 # "public" or "private"
  
  echo -e "${YELLOW}Adding $username to channel $channel...${NC}"
  
  # Get user ID
  local user_response=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    "$ROCKETCHAT_URL/api/v1/users.info?username=$username")
  
  if ! echo "$user_response" | grep -q "success\":true"; then
    echo -e "${RED}Failed to get user info for $username.${NC}"
    echo -e "${RED}Response: $user_response${NC}"
    return 1
  fi
  
  local user_id=$(echo "$user_response" | grep -o '"_id":"[^"]*' | head -1 | cut -d'"' -f4)
  
  # Get channel/room ID
  local room_endpoint="channels.info"
  if [ "$type" = "private" ]; then
    room_endpoint="groups.info"
  fi
  
  local room_response=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    "$ROCKETCHAT_URL/api/v1/$room_endpoint?roomName=$channel")
  
  if ! echo "$room_response" | grep -q "success\":true"; then
    echo -e "${RED}Failed to get channel info for $channel.${NC}"
    echo -e "${RED}Response: $room_response${NC}"
    return 1
  fi
  
  local room_id=""
  if [ "$type" = "private" ]; then
    room_id=$(echo "$room_response" | grep -o '"_id":"[^"]*' | head -1 | cut -d'"' -f4)
  else
    room_id=$(echo "$room_response" | grep -o '"_id":"[^"]*' | head -1 | cut -d'"' -f4)
  fi
  
  # Add user to channel
  local endpoint="channels.invite"
  if [ "$type" = "private" ]; then
    endpoint="groups.invite"
  fi
  
  local response=$(curl -s -H "X-Auth-Token: $ADMIN_TOKEN" -H "X-User-Id: $ADMIN_ID" \
    -H "Content-Type: application/json" \
    -d "{\"roomId\":\"$room_id\",\"userId\":\"$user_id\"}" \
    "$ROCKETCHAT_URL/api/v1/$endpoint")
  
  if echo "$response" | grep -q "success\":true"; then
    echo -e "${GREEN}Added $username to channel $channel successfully.${NC}"
    return 0
  else
    echo -e "${RED}Failed to add $username to channel $channel.${NC}"
    echo -e "${RED}Response: $response${NC}"
    return 1
  fi
}

# Main execution flow
check_rocketchat

# Try to complete the setup wizard (this may fail if already completed)
complete_setup_wizard

# Try to login with admin credentials
auth_info=$(login "$ADMIN_USERNAME" "$ADMIN_PASSWORD")
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to login as admin. Manual setup may be required.${NC}"
  echo -e "${YELLOW}Please visit $ROCKETCHAT_URL and complete the setup manually.${NC}"
  exit 1
fi

ADMIN_TOKEN=$(echo "$auth_info" | cut -d':' -f1)
ADMIN_ID=$(echo "$auth_info" | cut -d':' -f2)

echo -e "${GREEN}Successfully logged in as admin.${NC}"

# Create users
create_user "$BOT_USERNAME" "$BOT_PASSWORD" "$BOT_EMAIL" "Heyken Bot"
create_user "$HUMAN_USERNAME" "$HUMAN_PASSWORD" "$HUMAN_EMAIL" "Human User"

# Create channels
create_channel "heyken-system" "public"
create_channel "heyken-logs" "public"
create_channel "heyken-sandbox" "private"

# Add users to channels
add_to_channel "$BOT_USERNAME" "heyken-system" "public"
add_to_channel "$BOT_USERNAME" "heyken-logs" "public"
add_to_channel "$BOT_USERNAME" "heyken-sandbox" "private"

add_to_channel "$HUMAN_USERNAME" "heyken-system" "public"
add_to_channel "$HUMAN_USERNAME" "heyken-logs" "public"
add_to_channel "$HUMAN_USERNAME" "heyken-sandbox" "private"

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  RocketChat setup completed!                     ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}Admin user: $ADMIN_USERNAME / $ADMIN_PASSWORD${NC}"
echo -e "${GREEN}Bot user: $BOT_USERNAME / $BOT_PASSWORD${NC}"
echo -e "${GREEN}Human user: $HUMAN_USERNAME / $HUMAN_PASSWORD${NC}"
echo -e "${GREEN}Created channels: heyken-system, heyken-logs, heyken-sandbox${NC}"
echo -e "${GREEN}You can now access RocketChat at: $ROCKETCHAT_URL${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}After verifying RocketChat is properly configured,${NC}"
echo -e "${GREEN}you can continue with the Heyken deployment by running:${NC}"
echo -e "${GREEN}./continue_heyken_deployment.sh                   ${NC}"
echo -e "${GREEN}==================================================${NC}"
