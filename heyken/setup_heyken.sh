#!/bin/bash
# Master script to set up the entire Heyken system
# This script orchestrates the setup of RocketChat, email server, and other components

# Colors for messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Display banner
echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}         HEYKEN SYSTEM SETUP SCRIPT              ${NC}"
echo -e "${GREEN}=================================================${NC}"

# Check if .env file exists
if [ ! -f ./.env ]; then
  echo -e "${RED}Error: .env file not found in the current directory.${NC}"
  echo -e "Please make sure you are running this script from the Heyken root directory."
  exit 1
fi

# Load environment variables
echo -e "${YELLOW}Loading environment variables from .env...${NC}"
set -a
source ./.env
set +a

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check for required dependencies
echo -e "${YELLOW}Checking for required dependencies...${NC}"
MISSING_DEPS=0

if ! command_exists docker; then
  echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
  MISSING_DEPS=1
fi

if ! command_exists docker-compose; then
  echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
  MISSING_DEPS=1
fi

if [ $MISSING_DEPS -eq 1 ]; then
  echo -e "${RED}Missing dependencies. Please install them and try again.${NC}"
  exit 1
fi

# Function to stop all running containers
stop_all_containers() {
  echo -e "${YELLOW}Stopping any running Heyken containers...${NC}"
  
  # Check if stop.sh exists and is executable
  if [ -f ./stop.sh ] && [ -x ./stop.sh ]; then
    ./stop.sh
  else
    # Fallback if stop.sh doesn't exist or isn't executable
    echo -e "${YELLOW}stop.sh not found or not executable. Using fallback method...${NC}"
    
    # Stop RocketChat containers
    if docker ps -q --filter "name=rocketchat" | grep -q .; then
      echo "Stopping RocketChat containers..."
      docker stop $(docker ps -q --filter "name=rocketchat")
    fi
    
    # Stop MongoDB containers
    if docker ps -q --filter "name=mongo" | grep -q .; then
      echo "Stopping MongoDB containers..."
      docker stop $(docker ps -q --filter "name=mongo")
    fi
    
    # Stop Mailhog containers
    if docker ps -q --filter "name=mailhog" | grep -q .; then
      echo "Stopping Mailhog containers..."
      docker stop $(docker ps -q --filter "name=mailhog")
    fi
    
    # Remove all stopped containers
    docker container prune -f
  fi
  
  echo -e "${GREEN}All containers stopped.${NC}"
}

# Function to set up the email server (Mailhog)
setup_email_server() {
  echo -e "${YELLOW}Setting up email server (Mailhog)...${NC}"
  
  # Create directory for email server if it doesn't exist
  mkdir -p ./docker/mailserver
  
  # Create docker-compose.yml for Mailhog if it doesn't exist
  if [ ! -f ./docker/mailserver/docker-compose.yml ]; then
    cat > ./docker/mailserver/docker-compose.yml << EOF
version: '3'

services:
  mailhog:
    image: mailhog/mailhog:latest
    container_name: heyken-mailhog
    ports:
      - "${MAILHOG_SMTP_PORT:-1025}:1025"
      - "${MAILHOG_WEB_PORT:-8025}:8025"
    networks:
      - heyken-network

networks:
  heyken-network:
    driver: bridge
EOF
  fi
  
  # Start Mailhog
  echo -e "${YELLOW}Starting Mailhog...${NC}"
  cd ./docker/mailserver && docker-compose up -d
  cd ../../
  
  echo -e "${GREEN}Email server (Mailhog) setup complete.${NC}"
  echo -e "SMTP server available at: localhost:${MAILHOG_SMTP_PORT:-1025}"
  echo -e "Web interface available at: http://localhost:${MAILHOG_WEB_PORT:-8025}"
}

# Function to set up RocketChat
setup_rocketchat() {
  echo -e "${YELLOW}Setting up RocketChat...${NC}"
  
  # Check if rocket-chat-auto directory exists, create if not
  if [ ! -d ./rocket-chat-auto ]; then
    mkdir -p ./rocket-chat-auto
  fi
  
  # Copy the start script if it doesn't exist
  if [ ! -f ./rocket-chat-auto/start-rocketchat.sh ] || [ ! -f ./rocket-chat-auto/setup-rocketchat-users.sh ]; then
    echo -e "${YELLOW}Creating RocketChat setup scripts...${NC}"
    
    # Create start-rocketchat.sh
    cat > ./rocket-chat-auto/start-rocketchat.sh << 'EOF'
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
ROCKETCHAT_URL=http://localhost:${ROCKETCHAT_PORT:-3100}
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
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:${ROCKETCHAT_PORT:-3100}/api/info | grep -q "200"; then
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
echo -e "${GREEN}RocketChat URL: http://localhost:${ROCKETCHAT_PORT:-3100}${NC}"
echo -e "${GREEN}Webmail URL: http://localhost:${MAILHOG_WEB_PORT:-8025}${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${YELLOW}To view logs:${NC}"
echo -e "${YELLOW}  docker-compose logs -f rocketchat${NC}"
echo -e "${YELLOW}To stop all services:${NC}"
echo -e "${YELLOW}  docker-compose down${NC}"
echo -e "${GREEN}==================================================${NC}"
EOF
    
    # Create setup-rocketchat-users.sh
    cat > ./rocket-chat-auto/setup-rocketchat-users.sh << 'EOF'
#!/bin/sh
# Script to set up RocketChat users using only curl

# Set default values for environment variables
ROCKETCHAT_URL="${ROCKETCHAT_URL:-http://localhost:3100}"
ROCKETCHAT_ADMIN_USERNAME="${ROCKETCHAT_ADMIN_USERNAME:-heyken_admin}"
ROCKETCHAT_ADMIN_PASSWORD="${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}"
ROCKETCHAT_ADMIN_EMAIL="${ROCKETCHAT_ADMIN_EMAIL:-admin@heyken.local}"
ROCKETCHAT_BOT_USERNAME="${ROCKETCHAT_BOT_USERNAME:-heyken_bot}"
ROCKETCHAT_BOT_PASSWORD="${ROCKETCHAT_BOT_PASSWORD:-heyken123}"
ROCKETCHAT_BOT_EMAIL="${ROCKETCHAT_BOT_EMAIL:-bot@heyken.local}"
ROCKETCHAT_HUMAN_USERNAME="${ROCKETCHAT_HUMAN_USERNAME:-heyken_user}"
ROCKETCHAT_HUMAN_PASSWORD="${ROCKETCHAT_HUMAN_PASSWORD:-user123}"
ROCKETCHAT_HUMAN_EMAIL="${ROCKETCHAT_HUMAN_EMAIL:-user@heyken.local}"

# Print setup information
echo "=========================================================="
echo "Setting up RocketChat users"
echo "=========================================================="
echo "RocketChat URL: $ROCKETCHAT_URL"
echo "Admin username: $ROCKETCHAT_ADMIN_USERNAME"
echo "Bot username: $ROCKETCHAT_BOT_USERNAME"
echo "Human username: $ROCKETCHAT_HUMAN_USERNAME"
echo "=========================================================="

# Wait for RocketChat to be ready
wait_for_rocketchat() {
  echo "Waiting for RocketChat to be ready..."
  max_attempts=30
  attempt=0
  
  while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt+1))
    echo "Attempt $attempt/$max_attempts..."
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$ROCKETCHAT_URL/api/info")
    
    if [ "$status" = "200" ]; then
      echo "RocketChat is ready!"
      return 0
    fi
    
    echo "RocketChat not ready yet (HTTP status: $status). Waiting 10 seconds..."
    sleep 10
  done
  
  echo "Timed out waiting for RocketChat to be ready."
  return 1
}

# Complete setup wizard if needed
setup_wizard() {
  echo "Checking if setup wizard needs to be completed..."
  
  # Get current status
  info=$(curl -s "$ROCKETCHAT_URL/api/info")
  
  # Try to access the setup endpoint directly
  echo "Attempting to create admin user via setup wizard..."
  admin_setup=$(curl -s -X POST \
    "$ROCKETCHAT_URL/api/v1/setup.admin" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$ROCKETCHAT_ADMIN_USERNAME\",
      \"password\": \"$ROCKETCHAT_ADMIN_PASSWORD\",
      \"email\": \"$ROCKETCHAT_ADMIN_EMAIL\",
      \"fullname\": \"Administrator\"
    }")
  
  if echo "$admin_setup" | grep -q "\"success\":true"; then
    echo "Admin user created successfully via setup wizard."
    # Sleep to allow the server to process the admin creation
    sleep 5
    return 0
  else
    echo "Setup wizard response: $admin_setup"
    echo "Setup wizard might already be completed or not available."
    echo "Will try to register directly..."
    
    # Try to register a new user directly
    register_response=$(curl -s -X POST \
      "$ROCKETCHAT_URL/api/v1/users.register" \
      -H "Content-Type: application/json" \
      -d "{
        \"username\": \"$ROCKETCHAT_ADMIN_USERNAME\",
        \"email\": \"$ROCKETCHAT_ADMIN_EMAIL\",
        \"pass\": \"$ROCKETCHAT_ADMIN_PASSWORD\",
        \"name\": \"Administrator\"
      }")
    
    if echo "$register_response" | grep -q "\"success\":true"; then
      echo "Admin user registered successfully."
      # Sleep to allow the server to process the registration
      sleep 5
      return 0
    else
      echo "Registration response: $register_response"
      echo "Will continue with login attempt..."
      return 0
    fi
  fi
}

# Login as admin and get auth token
admin_login() {
  echo "Logging in as admin..."
  
  # Try multiple login attempts with different approaches
  for attempt in 1 2 3; do
    echo "Login attempt $attempt..."
    
    # Different login approaches
    if [ "$attempt" -eq 1 ]; then
      # Standard login
      login_payload="{
        \"user\": \"$ROCKETCHAT_ADMIN_USERNAME\",
        \"password\": \"$ROCKETCHAT_ADMIN_PASSWORD\"
      }"
    elif [ "$attempt" -eq 2 ]; then
      # Try with email
      login_payload="{
        \"user\": \"$ROCKETCHAT_ADMIN_EMAIL\",
        \"password\": \"$ROCKETCHAT_ADMIN_PASSWORD\"
      }"
    else
      # Try with different format
      login_payload="{
        \"username\": \"$ROCKETCHAT_ADMIN_USERNAME\",
        \"password\": \"$ROCKETCHAT_ADMIN_PASSWORD\"
      }"
    fi
    
    login_response=$(curl -s -X POST \
      "$ROCKETCHAT_URL/api/v1/login" \
      -H "Content-Type: application/json" \
      -d "$login_payload")
    
    if echo "$login_response" | grep -q "\"status\":\"success\""; then
      auth_token=$(echo "$login_response" | grep -o '"authToken":"[^"]*' | cut -d'"' -f4)
      user_id=$(echo "$login_response" | grep -o '"userId":"[^"]*' | cut -d'"' -f4)
      
      if [ -n "$auth_token" ] && [ -n "$user_id" ]; then
        echo "Login successful. Auth token and user ID obtained."
        echo "AUTH_TOKEN=$auth_token"
        echo "USER_ID=$user_id"
        export AUTH_TOKEN="$auth_token"
        export USER_ID="$user_id"
        return 0
      else
        echo "Failed to extract auth token or user ID from response: $login_response"
      fi
    else
      echo "Login attempt $attempt failed: $login_response"
    fi
    
    # Wait before trying again
    sleep 3
  done
  
  echo "All login attempts failed. Trying to continue without authentication..."
  # Return success anyway to allow the script to continue
  # We'll handle authentication failures in the individual functions
  return 0
}

# Create a new user
create_user() {
  username="$1"
  email="$2"
  password="$3"
  roles="$4"
  
  echo "Creating user: $username with roles: $roles"
  
  # Convert roles string to JSON array
  roles_json="["
  IFS=',' read -ra ROLE_ARRAY <<< "$roles"
  for i in "${!ROLE_ARRAY[@]}"; do
    if [ $i -gt 0 ]; then
      roles_json+=","
    fi
    roles_json+="\"${ROLE_ARRAY[$i]}\""
  done
  roles_json+="]"
  
  create_response=$(curl -s -X POST \
    "$ROCKETCHAT_URL/api/v1/users.create" \
    -H "X-Auth-Token: $AUTH_TOKEN" \
    -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"$username\",
      \"email\": \"$email\",
      \"password\": \"$password\",
      \"username\": \"$username\",
      \"roles\": $roles_json,
      \"active\": true,
      \"joinDefaultChannels\": true,
      \"requirePasswordChange\": false,
      \"sendWelcomeEmail\": false
    }")
  
  if echo "$create_response" | grep -q "\"success\":true"; then
    echo "User $username created successfully!"
    return 0
  else
    # Check for specific error indicating user exists
    if echo "$create_response" | grep -q "Username is already in use\|already exists"; then
      echo "User $username already exists."
      return 0
    else
      echo "Failed to create user $username: $create_response"
      return 1
    fi
  fi
}

# Create channels
create_channel() {
  channel_name="$1"
  is_private="$2"
  
  endpoint="channels.create"
  if [ "$is_private" = "true" ]; then
    endpoint="groups.create"
  fi
  
  echo "Creating channel: $channel_name (private: $is_private)"
  
  channel_response=$(curl -s -X POST \
    "$ROCKETCHAT_URL/api/v1/$endpoint" \
    -H "X-Auth-Token: $AUTH_TOKEN" \
    -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"$channel_name\"
    }")
  
  if echo "$channel_response" | grep -q "\"success\":true"; then
    echo "Channel $channel_name created successfully!"
    return 0
  else
    # Check for specific error indicating channel exists
    if echo "$channel_response" | grep -q "name-already-exists\|already exists"; then
      echo "Channel $channel_name already exists."
      return 0
    else
      echo "Failed to create channel $channel_name: $channel_response"
      return 1
    fi
  fi
}

# Main execution
main() {
  # Wait for RocketChat to be ready
  if ! wait_for_rocketchat; then
    echo "Error: RocketChat not available. Exiting."
    exit 1
  fi
  
  # Complete setup wizard if needed
  setup_wizard
  
  # Try to login as admin
  admin_login
  
  # Check if we have authentication tokens
  if [ -n "$AUTH_TOKEN" ] && [ -n "$USER_ID" ]; then
    echo "Successfully authenticated. Creating users and channels..."
    
    # Create bot user
    if ! create_user "$ROCKETCHAT_BOT_USERNAME" "$ROCKETCHAT_BOT_EMAIL" "$ROCKETCHAT_BOT_PASSWORD" "user,bot"; then
      echo "Warning: Failed to create bot user."
    fi
    
    # Create human user
    if ! create_user "$ROCKETCHAT_HUMAN_USERNAME" "$ROCKETCHAT_HUMAN_EMAIL" "$ROCKETCHAT_HUMAN_PASSWORD" "user"; then
      echo "Warning: Failed to create human user."
    fi
    
    # Create channels
    create_channel "heyken-system" "false"
    create_channel "heyken-logs" "false"
    create_channel "heyken-sandbox" "true"
  else
    echo "Authentication failed. Unable to create users and channels automatically."
    echo "Please complete the setup manually through the web interface:"
    echo "1. Open $ROCKETCHAT_URL in your browser"
    echo "2. Complete the setup wizard if prompted"
    echo "3. Login with the admin credentials: $ROCKETCHAT_ADMIN_USERNAME / $ROCKETCHAT_ADMIN_PASSWORD"
    echo "4. Create the bot and human users manually through the admin panel"
  fi
  
  echo "=========================================================="
  echo "RocketChat setup process completed!"
  echo "=========================================================="
  echo "Admin user: $ROCKETCHAT_ADMIN_USERNAME / $ROCKETCHAT_ADMIN_PASSWORD"
  echo "Bot user: $ROCKETCHAT_BOT_USERNAME / $ROCKETCHAT_BOT_PASSWORD"
  echo "Human user: $ROCKETCHAT_HUMAN_USERNAME / $ROCKETCHAT_HUMAN_PASSWORD"
  echo "Channels to create: heyken-system, heyken-logs, heyken-sandbox"
  echo "=========================================================="
  echo "Access RocketChat at: $ROCKETCHAT_URL"
  echo "Access Mailhog at: http://localhost:${MAILHOG_WEB_PORT:-8025}"
  echo "=========================================================="
}

# Execute main function
main
EOF
    
    # Create docker-compose.yml
    cat > ./rocket-chat-auto/docker-compose.yml << 'EOF'
version: '3'

services:
  rocketchat:
    image: registry.rocket.chat/rocketchat/rocket.chat:latest
    restart: unless-stopped
    volumes:
      - ./uploads:/app/uploads
    environment:
      - PORT=3000
      - ROOT_URL=http://localhost:${ROCKETCHAT_PORT:-3100}
      - MONGO_URL=mongodb://mongo:27017/rocketchat
      - MONGO_OPLOG_URL=mongodb://mongo:27017/local
      - OVERWRITE_SETTING_Show_Setup_Wizard=completed
      - MAIL_URL=smtp://${MAIL_SERVER_HOST:-mailhog}:${MAIL_SERVER_PORT:-1025}
      - OVERWRITE_SETTING_SMTP_Host=${MAIL_SERVER_HOST:-mailhog}
      - OVERWRITE_SETTING_SMTP_Port=${MAIL_SERVER_PORT:-1025}
      - OVERWRITE_SETTING_From_Email=${MAIL_SERVER_FROM_EMAIL:-rocketchat@heyken.local}
      - OVERWRITE_SETTING_Email_Verification=false
      - OVERWRITE_SETTING_Accounts_EmailVerification=false
    depends_on:
      - mongo
    ports:
      - "${ROCKETCHAT_PORT:-3100}:3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/info"]
      interval: 10s
      timeout: 10s
      retries: 5
    networks:
      - rocket-network

  mongo:
    image: mongo:5.0
    restart: unless-stopped
    volumes:
      - ./data/db:/data/db
      - ./data/dump:/dump
    command: mongod --oplogSize 128 --replSet rs0 --storageEngine=wiredTiger
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 10s
      retries: 5
    networks:
      - rocket-network

  mongo-init-replica:
    image: mongo:5.0
    restart: "no"
    depends_on:
      - mongo
    command: >
      bash -c "
        echo 'Waiting for MongoDB to start...' &&
        sleep 10 &&
        mongosh mongo/rocketchat --eval \"
          rs.initiate({
            _id: 'rs0',
            members: [ { _id: 0, host: 'mongo:27017' } ]
          })
        \"
      "
    networks:
      - rocket-network

networks:
  rocket-network:
    driver: bridge
EOF
    
    # Make scripts executable
    chmod +x ./rocket-chat-auto/start-rocketchat.sh
    chmod +x ./rocket-chat-auto/setup-rocketchat-users.sh
  fi
  
  # Start RocketChat
  echo -e "${YELLOW}Starting RocketChat...${NC}"
  cd ./rocket-chat-auto && ./start-rocketchat.sh
  cd ../
  
  echo -e "${GREEN}RocketChat setup complete.${NC}"
}

# Function to create a status script
create_status_script() {
  echo -e "${YELLOW}Creating status script...${NC}"
  
  # Create scripts directory if it doesn't exist
  mkdir -p ./scripts
  
  # Create show_status.sh
  cat > ./scripts/show_status.sh << 'EOF'
#!/bin/bash
# Script to show the status of all Heyken services

# Colors for messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Display banner
echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}         HEYKEN SYSTEM STATUS                    ${NC}"
echo -e "${BLUE}=================================================${NC}"

# Load environment variables if .env exists
if [ -f ../.env ]; then
  source ../.env
fi

# Set default values if not defined in .env
ROCKETCHAT_PORT=${ROCKETCHAT_PORT:-3100}
MAILHOG_WEB_PORT=${MAILHOG_WEB_PORT:-8025}

# Function to check if a service is running
check_service() {
  local service_name=$1
  local container_pattern=$2
  local port=$3
  local url=$4
  
  echo -e "${YELLOW}Checking $service_name...${NC}"
  
  # Check if container is running
  if docker ps | grep -q "$container_pattern"; then
    echo -e "  Container: ${GREEN}Running${NC}"
    
    # Check if port is open
    if nc -z localhost $port 2>/dev/null; then
      echo -e "  Port $port: ${GREEN}Open${NC}"
      
      # Check if service is responding (if URL is provided)
      if [ -n "$url" ]; then
        http_code=$(curl -s -o /dev/null -w "%{http_code}" $url)
        if [ "$http_code" = "200" ]; then
          echo -e "  HTTP Status: ${GREEN}OK (200)${NC}"
        else
          echo -e "  HTTP Status: ${RED}Error ($http_code)${NC}"
        fi
      fi
    else
      echo -e "  Port $port: ${RED}Closed${NC}"
    fi
  else
    echo -e "  Container: ${RED}Not running${NC}"
  fi
  
  echo ""
}

# Check RocketChat
check_service "RocketChat" "rocketchat" "$ROCKETCHAT_PORT" "http://localhost:$ROCKETCHAT_PORT/api/info"

# Check MongoDB
check_service "MongoDB" "mongo" "27017" ""

# Check Mailhog
check_service "Mailhog" "mailhog" "$MAILHOG_WEB_PORT" "http://localhost:$MAILHOG_WEB_PORT"

# Show service URLs
echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}         SERVICE URLs                            ${NC}"
echo -e "${BLUE}=================================================${NC}"
echo -e "RocketChat: ${GREEN}http://localhost:$ROCKETCHAT_PORT${NC}"
echo -e "Mailhog (Email): ${GREEN}http://localhost:$MAILHOG_WEB_PORT${NC}"
echo -e "${BLUE}=================================================${NC}"
EOF
  
  # Make script executable
  chmod +x ./scripts/show_status.sh
  
  echo -e "${GREEN}Status script created.${NC}"
}

# Main execution
main() {
  # Stop any running containers
  stop_all_containers
  
  # Set up email server
  setup_email_server
  
  # Set up RocketChat
  setup_rocketchat
  
  # Create status script
  create_status_script
  
  # Display completion message
  echo -e "${GREEN}=================================================${NC}"
  echo -e "${GREEN}         HEYKEN SYSTEM SETUP COMPLETE           ${NC}"
  echo -e "${GREEN}=================================================${NC}"
  echo -e "RocketChat URL: ${GREEN}http://localhost:${ROCKETCHAT_PORT:-3100}${NC}"
  echo -e "Mailhog URL: ${GREEN}http://localhost:${MAILHOG_WEB_PORT:-8025}${NC}"
  echo -e "${GREEN}=================================================${NC}"
  echo -e "To check system status: ${YELLOW}./scripts/show_status.sh${NC}"
  echo -e "To stop all services: ${YELLOW}./stop.sh${NC}"
  echo -e "${GREEN}=================================================${NC}"
}

# Execute main function
main
