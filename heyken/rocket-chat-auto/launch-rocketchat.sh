#!/bin/bash
# Launch script for Rocket.Chat with auto-user setup

# Configuration - edit these values as needed
METHOD=${1:-1}  # Default to method 1
DIR="rocket-chat-auto"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print banner
echo -e "${GREEN}========================================"
echo "Rocket.Chat Auto-User Setup Launcher"
echo -e "========================================${NC}"

# Create base directory
mkdir -p $DIR
cd $DIR

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
  echo -e "${YELLOW}Creating .env file with default credentials...${NC}"
  cat > .env << 'EOF'
# Admin User Configuration
ROCKETCHAT_ADMIN_USERNAME=admin
ROCKETCHAT_ADMIN_PASSWORD=dxIsDLnhiqKfDt5J
ROCKETCHAT_ADMIN_EMAIL=admin@heyken.local

# Bot User Configuration
ROCKETCHAT_BOT_USERNAME=heyken_bot
ROCKETCHAT_BOT_PASSWORD=heyken123
ROCKETCHAT_BOT_EMAIL=bot@heyken.local

# Human User Configuration
ROCKETCHAT_HUMAN_USERNAME=user
ROCKETCHAT_HUMAN_PASSWORD=user123
ROCKETCHAT_HUMAN_EMAIL=user@heyken.local
EOF
  echo -e "${GREEN}Created .env file${NC}"
fi

# Create necessary directories
mkdir -p data/db data/dump uploads scripts

# Launch based on method
case $METHOD in
  1)
    echo -e "${YELLOW}Using Method 1: Docker Compose with separate setup service${NC}"
    
    # Create docker-compose.yml
    cat > docker-compose.yml << 'EOF'
version: '3'

services:
  rocketchat:
    image: registry.rocket.chat/rocketchat/rocket.chat:latest
    restart: unless-stopped
    volumes:
      - ./uploads:/app/uploads
    environment:
      - PORT=3000
      - ROOT_URL=http://localhost:3100
      - MONGO_URL=mongodb://mongo:27017/rocketchat
      - MONGO_OPLOG_URL=mongodb://mongo:27017/local
      - OVERWRITE_SETTING_Show_Setup_Wizard=completed
    depends_on:
      - mongo
    ports:
      - 3100:3000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/info"]
      interval: 10s
      timeout: 10s
      retries: 5

  mongo:
    image: mongo:5.0
    restart: unless-stopped
    volumes:
      - ./data/db:/data/db
      - ./data/dump:/dump
    command: mongod --oplogSize 128 --replSet rs0 --storageEngine=wiredTiger
    healthcheck:
      test: ["CMD", "mongo", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 10s
      retries: 5

  mongo-init-replica:
    image: mongo:5.0
    restart: "no"
    depends_on:
      - mongo
    command: >
      bash -c "
        echo 'Waiting for MongoDB to start...' &&
        sleep 10 &&
        mongo mongo/rocketchat --eval \"
          rs.initiate({
            _id: 'rs0',
            members: [ { _id: 0, host: 'mongo:27017' } ]
          })
        \"
      "

  setup-users:
    image: curlimages/curl:latest
    depends_on:
      - rocketchat
    volumes:
      - ./setup-rocketchat-users.sh:/setup.sh
      - ./.env:/.env
    environment:
      - ROCKETCHAT_URL=http://rocketchat:3000
    entrypoint: ["sh", "-c", "chmod +x /setup.sh && /setup.sh"]
    restart: "no"
EOF

    # Create setup script
    cat > setup-rocketchat-users.sh << 'EOF'
#!/bin/sh
# Script to set up RocketChat users using only curl

# Set default values for environment variables
ROCKETCHAT_URL="${ROCKETCHAT_URL:-http://localhost:3000}"
ROCKETCHAT_ADMIN_USERNAME="${ROCKETCHAT_ADMIN_USERNAME:-admin}"
ROCKETCHAT_ADMIN_PASSWORD="${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}"
ROCKETCHAT_ADMIN_EMAIL="${ROCKETCHAT_ADMIN_EMAIL:-admin@heyken.local}"
ROCKETCHAT_BOT_USERNAME="${ROCKETCHAT_BOT_USERNAME:-heyken_bot}"
ROCKETCHAT_BOT_PASSWORD="${ROCKETCHAT_BOT_PASSWORD:-heyken123}"
ROCKETCHAT_BOT_EMAIL="${ROCKETCHAT_BOT_EMAIL:-bot@heyken.local}"
ROCKETCHAT_HUMAN_USERNAME="${ROCKETCHAT_HUMAN_USERNAME:-user}"
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
  
  if echo "$info" | grep -q "\"wizard\":{\"step\":"; then
    echo "Setup wizard active. Completing initial setup..."
    
    # Step 1: Admin user setup
    echo "Creating admin user..."
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
      return 0
    else
      echo "Failed to create admin via setup wizard: $admin_setup"
      return 1
    fi
  else
    echo "Setup wizard not active or already completed."
    return 0
  fi
}

# Login as admin and get auth token
admin_login() {
  echo "Logging in as admin..."
  
  login_response=$(curl -s -X POST \
    "$ROCKETCHAT_URL/api/v1/login" \
    -H "Content-Type: application/json" \
    -d "{
      \"user\": \"$ROCKETCHAT_ADMIN_USERNAME\",
      \"password\": \"$ROCKETCHAT_ADMIN_PASSWORD\"
    }")
  
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
      return 1
    fi
  else
    echo "Admin login failed: $login_response"
    return 1
  fi
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
      \"joinDefaultChannels\": true
    }")
  
  if echo "$create_response" | grep -q "\"success\":true"; then
    echo "User $username created successfully!"
    return 0
  else
    # Check for specific error indicating user exists
    if echo "$create_response" | grep -q "Username is already in use"; then
      echo "User $username already exists."
      return 0
    else
      echo "Failed to create user $username: $create_response"
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
  if ! setup_wizard; then
    echo "Error: Failed to complete setup wizard. Trying to proceed anyway..."
  fi
  
  # Login as admin
  if ! admin_login; then
    echo "Error: Failed to log in as admin. Exiting."
    exit 1
  fi
  
  # Create bot user
  if ! create_user "$ROCKETCHAT_BOT_USERNAME" "$ROCKETCHAT_BOT_EMAIL" "$ROCKETCHAT_BOT_PASSWORD" "user,bot"; then
    echo "Warning: Failed to create bot user."
  fi
  
  # Create human user
  if ! create_user "$ROCKETCHAT_HUMAN_USERNAME" "$ROCKETCHAT_HUMAN_EMAIL" "$ROCKETCHAT_HUMAN_PASSWORD" "user"; then
    echo "Warning: Failed to create human user."
  fi
  
  echo "=========================================================="
  echo "RocketChat user setup completed!"
  echo "=========================================================="
  echo "Admin user: $ROCKETCHAT_ADMIN_USERNAME"
  echo "Bot user: $ROCKETCHAT_BOT_USERNAME"
  echo "Human user: $ROCKETCHAT_HUMAN_USERNAME"
  echo "=========================================================="
}

# Execute main function
main
EOF

    # Make setup script executable
    chmod +x setup-rocketchat-users.sh
    
    # Start containers
    echo -e "${GREEN}Starting Docker containers...${NC}"
    docker-compose up -d
    
    echo -e "${YELLOW}Waiting for setup to complete...${NC}"
    sleep 10
    docker-compose logs -f setup-users
    ;;
    
  2)
    echo -e "${YELLOW}Using Method 2: Standalone script for existing installation${NC}"
    
    # Create standalone script
    cat > create-rocketchat-users.sh << 'EOF'
#!/bin/bash
# Script to set up RocketChat users using only curl

# Load environment variables from .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "No .env file found. Using default values."
fi

# Set default values for environment variables
ROCKETCHAT_URL="${ROCKETCHAT_URL:-http://localhost:3000}"
ROCKETCHAT_ADMIN_USERNAME="${ROCKETCHAT_ADMIN_USERNAME:-admin}"
ROCKETCHAT_ADMIN_PASSWORD="${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}"
ROCKETCHAT_ADMIN_EMAIL="${ROCKETCHAT_ADMIN_EMAIL:-admin@heyken.local}"
ROCKETCHAT_BOT_USERNAME="${ROCKETCHAT_BOT_USERNAME:-heyken_bot}"
ROCKETCHAT_BOT_PASSWORD="${ROCKETCHAT_BOT_PASSWORD:-heyken123}"
ROCKETCHAT_BOT_EMAIL="${ROCKETCHAT_BOT_EMAIL:-bot@heyken.local}"
ROCKETCHAT_HUMAN_USERNAME="${ROCKETCHAT_HUMAN_USERNAME:-user}"
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
  local max_attempts=30
  local attempt=0
  
  while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt+1))
    echo "Attempt $attempt/$max_attempts..."
    
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$ROCKETCHAT_URL/api/info")
    
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
  local info=$(curl -s "$ROCKETCHAT_URL/api/info")
  
  if echo "$info" | grep -q "\"wizard\":{\"step\":"; then
    echo "Setup wizard active. Completing initial setup..."
    
    # Step 1: Admin user setup
    echo "Creating admin user..."
    local admin_setup=$(curl -s -X POST \
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
      return 0
    else
      echo "Failed to create admin via setup wizard: $admin_setup"
      return 1
    fi
  else
    echo "Setup wizard not active or already completed."
    return 0
  fi
}

# Login as admin and get auth token
admin_login() {
  echo "Logging in as admin..."
  
  local login_response=$(curl -s -X POST \
    "$ROCKETCHAT_URL/api/v1/login" \
    -H "Content-Type: application/json" \
    -d "{
      \"user\": \"$ROCKETCHAT_ADMIN_USERNAME\",
      \"password\": \"$ROCKETCHAT_ADMIN_PASSWORD\"
    }")
  
  if echo "$login_response" | grep -q "\"status\":\"success\""; then
    local auth_token=$(echo "$login_response" | grep -o '"authToken":"[^"]*' | cut -d'"' -f4)
    local user_id=$(echo "$login_response" | grep -o '"userId":"[^"]*' | cut -d'"' -f4)
    
    if [ -n "$auth_token" ] && [ -n "$user_id" ]; then
      echo "Login successful. Auth token and user ID obtained."
      echo "AUTH_TOKEN=$auth_token"
      echo "USER_ID=$user_id"
      export AUTH_TOKEN="$auth_token"
      export USER_ID="$user_id"
      return 0
    else
      echo "Failed to extract auth token or user ID from response: $login_response"
      return 1
    fi
  else
    echo "Admin login failed: $login_response"
    return 1
  fi
}

# Create a new user
create_user() {
  local username="$1"
  local email="$2"
  local password="$3"
  local roles="$4"
  
  echo "Creating user: $username with roles: $roles"
  
  # Convert roles string to JSON array
  local roles_json="["
  IFS=',' read -ra ROLE_ARRAY <<< "$roles"
  for i in "${!ROLE_ARRAY[@]}"; do
    if [ $i -gt 0 ]; then
      roles_json+=","
    fi
    roles_json+="\"${ROLE_ARRAY[$i]}\""
  done
  roles_json+="]"
  
  local create_response=$(curl -s -X POST \
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
      \"joinDefaultChannels\": true
    }")
  
  if echo "$create_response" | grep -q "\"success\":true"; then
    echo "User $username created successfully!"
    return 0
  else
    # Check for specific error indicating user exists
    if echo "$create_response" | grep -q "Username is already in use"; then
      echo "User $username already exists."
      return 0
    else
      echo "Failed to create user $username: $create_response"
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
  if ! setup_wizard; then
    echo "Error: Failed to complete setup wizard. Trying to proceed anyway..."
  fi
  
  # Login as admin
  if ! admin_login; then
    echo "Error: Failed to log in as admin. Exiting."
    exit 1
  fi
  
  # Create bot user
  if ! create_user "$ROCKETCHAT_BOT_USERNAME" "$ROCKETCHAT_BOT_EMAIL" "$ROCKETCHAT_BOT_PASSWORD" "user,bot"; then
    echo "Warning: Failed to create bot user."
  fi
  
  # Create human user
  if ! create_user "$ROCKETCHAT_HUMAN_USERNAME" "$ROCKETCHAT_HUMAN_EMAIL" "$ROCKETCHAT_HUMAN_PASSWORD" "user"; then
    echo "Warning: Failed to create human user."
  fi
  
  echo "=========================================================="
  echo "RocketChat user setup completed!"
  echo "=========================================================="
  echo "Admin user: $ROCKETCHAT_ADMIN_USERNAME"
  echo "Bot user: $ROCKETCHAT_BOT_USERNAME"
  echo "Human user: $ROCKETCHAT_HUMAN_USERNAME"
  echo "=========================================================="
}

# Execute main function
main
EOF

    # Make the script executable
    chmod +x create-rocketchat-users.sh
    
    echo -e "${GREEN}Script has been created: create-rocketchat-users.sh${NC}"
    echo -e "${YELLOW}Run './create-rocketchat-users.sh' to setup users on your existing Rocket.Chat instance${NC}"
    echo -e "${YELLOW}Or specify a custom URL: ROCKETCHAT_URL=http://your-server:3000 ./create-rocketchat-users.sh${NC}"
    ;;
    
  3)
    echo -e "${YELLOW}Using Method 3: Custom Docker image with integrated setup${NC}"
    
    # Create Dockerfile
    cat > Dockerfile << 'EOF'
FROM registry.rocket.chat/rocketchat/rocket.chat:latest

USER root

# Install necessary packages
RUN apt-get update && apt-get install -y curl jq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy setup script
COPY setup-users.sh /app/setup-users.sh
RUN chmod +x /app/setup-users.sh

# Add custom entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER rocketchat

ENTRYPOINT ["/app/entrypoint.sh"]
EOF

    # Create entrypoint.sh
    cat > entrypoint.sh << 'EOF'
#!/bin/bash
# Custom entrypoint script for RocketChat Docker image
# This script starts RocketChat and runs the user setup script

echo "Starting RocketChat with user auto-setup..."

# Start RocketChat in the background
node main.js &
ROCKETCHAT_PID=$!

# Give RocketChat some time to initialize before running the setup script
echo "Waiting for RocketChat to initialize before setting up users..."
sleep 60

# Export environment variables from host to script
export ROCKETCHAT_URL=http://localhost:3000
export ROCKETCHAT_ADMIN_USERNAME
export ROCKETCHAT_ADMIN_PASSWORD
export ROCKETCHAT_ADMIN_EMAIL
export ROCKETCHAT_BOT_USERNAME
export ROCKETCHAT_BOT_PASSWORD
export ROCKETCHAT_BOT_EMAIL
export ROCKETCHAT_HUMAN_USERNAME
export ROCKETCHAT_HUMAN_PASSWORD
export ROCKETCHAT_HUMAN_EMAIL

# Run setup script
echo "Running user setup script..."
/app/setup-users.sh

# Wait for the RocketChat process to finish
wait $ROCKETCHAT_PID
EOF

    # Create setup-users.sh
    cat > setup-users.sh << 'EOF'
#!/bin/bash
# Script to set up RocketChat users from inside the Docker container
# This script runs after RocketChat has started

# Set default values if not provided
ROCKETCHAT_URL="${ROCKETCHAT_URL:-http://localhost:3000}"
ROCKETCHAT_ADMIN_USERNAME="${ROCKETCHAT_ADMIN_USERNAME:-admin}"
ROCKETCHAT_ADMIN_PASSWORD="${ROCKETCHAT_ADMIN_PASSWORD:-dxIsDLnhiqKfDt5J}"
ROCKETCHAT_ADMIN_EMAIL="${ROCKETCHAT_ADMIN_EMAIL:-admin@heyken.local}"
ROCKETCHAT_BOT_USERNAME="${ROCKETCHAT_BOT_USERNAME:-heyken_bot}"
ROCKETCHAT_BOT_PASSWORD="${ROCKETCHAT_BOT_PASSWORD:-heyken123}"
ROCKETCHAT_BOT_EMAIL="${ROCKETCHAT_BOT_EMAIL:-bot@heyken.local}"
ROCKETCHAT_HUMAN_USERNAME="${ROCKETCHAT_HUMAN_USERNAME:-user}"
ROCKETCHAT_HUMAN_PASSWORD="${ROCKETCHAT_HUMAN_PASSWORD:-user123}"
ROCKETCHAT_HUMAN_EMAIL="${ROCKETCHAT_HUMAN_EMAIL:-user@heyken.local}"

echo "===== RocketChat User Setup ====="
echo "Setting up users on: $ROCKETCHAT_URL"

# Check if RocketChat is ready
check_rocketchat_ready() {
  local max_retries=30
  local retry=0
  
  echo "Checking if RocketChat API is ready..."
  
  while [ $retry -lt $max_retries ]; do
    retry=$((retry+1))
    
    if curl -s "$ROCKETCHAT_URL/api/info" | grep -q "version"; then
      echo "RocketChat is ready!"
      return 0
    fi
    
    echo "RocketChat not ready yet. Retry $retry/$max_retries"
    sleep 5
  done
  
  echo "ERROR: RocketChat not ready after $max_retries retries"
  return 1
}

# Login as admin user
admin_login() {
  echo "Attempting to login as admin..."
  
  local login_data=$(curl -s -X POST \
    "$ROCKETCHAT_URL/api/v1/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$ROCKETCHAT_ADMIN_USERNAME\",\"password\":\"$ROCKETCHAT_ADMIN_PASSWORD\"}")
  
  if echo "$login_data" | grep -q "\"status\":\"success\""; then
    local auth_token=$(echo "$login_data" | grep -o '"authToken":"[^"]*' | cut -d'"' -f4)
    local user_id=$(echo "$login_data" | grep -o '"userId":"[^"]*' | cut -d'"' -f4)
    
    echo "Admin login successful"
    AUTH_TOKEN="$auth_token"
    USER_ID="$user_id"
    return 0
  else
    echo "Admin login failed. Setup wizard may need completion."
    return 1
  fi
}

# Complete setup wizard if needed
complete_setup_wizard() {
  echo "Attempting to complete setup wizard..."
  
  local setup_response=$(curl -s -X POST \
    "$ROCKETCHAT_URL/api/v1/setup.admin" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$ROCKETCHAT_ADMIN_USERNAME\",
      \"password\": \"$ROCKETCHAT_ADMIN_PASSWORD\",
      \"email\": \"$ROCKETCHAT_ADMIN_EMAIL\",
      \"fullname\": \"Administrator\"
    }")
  
  if echo "$setup_response" | grep -q "\"success\":true"; then
    echo "Setup wizard completed successfully"
    return 0
  else
    echo "Setup wizard completion failed or not needed: $(echo "$setup_response" | grep -o '"error":"[^"]*' | cut -d'"' -f4)"
    return 1
  fi
}

# Create a user
create_user() {
  local username="$1"
  local password="$2"
  local email="$3"
  local roles="$4"
  
  # Skip if no auth token
  if [ -z "$AUTH_TOKEN" ] || [ -z "$USER_ID" ]; then
    echo "Cannot create user $username: No auth token or user ID"
    return 1
  fi
  
  echo "Creating user: $username with roles: $roles"
  
  # Create roles JSON array
  local roles_json="["
  IFS=',' read -ra ROLE_ARRAY <<< "$roles"
  for i in "${!ROLE_ARRAY[@]}"; do
    if [ $i -gt 0 ]; then
      roles_json+=","
    fi
    roles_json+="\"${ROLE_ARRAY[$i]}\""
  done
  roles_json+="]"
  
  local user_data=$(curl -s -X POST \
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
      \"requirePasswordChange\": false,
      \"joinDefaultChannels\": true,
      \"sendWelcomeEmail\": false
    }")
  
  if echo "$user_data" | grep -q "\"success\":true"; then
    echo "User $username created successfully"
    return 0
  elif echo "$user_data" | grep -q "Username is already in use"; then
    echo "User $username already exists"
    return 0
  else
    echo "Failed to create user $username: $(echo "$user_data" | grep -o '"error":"[^"]*' | cut -d'"' -f4)"
    return 1
  fi
}

# Main function
main() {
  # Check if RocketChat is ready
  if ! check_rocketchat_ready; then
    echo "ERROR: Cannot connect to RocketChat API"
    exit 1
  fi
  
  # Try to login directly first
  if ! admin_login; then
    # If login fails, try to complete setup wizard
    if complete_setup_wizard; then
      echo "Setup wizard completed. Trying to login again..."
      if ! admin_login; then
        echo "ERROR: Still cannot login as admin after setup"
        exit 1
      fi
    else
      echo "ERROR: Cannot complete setup or login"
      exit 1
    fi
  fi
  
  # Create bot user
  if create_user "$ROCKETCHAT_BOT_USERNAME" "$ROCKETCHAT_BOT_PASSWORD" "$ROCKETCHAT_BOT_EMAIL" "user,bot"; then
    echo "Bot user setup complete"
  else
    echo "WARNING: Bot user setup failed"
  fi
  
  # Create human user
  if create_user "$ROCKETCHAT_HUMAN_USERNAME" "$ROCKETCHAT_HUMAN_PASSWORD" "$ROCKETCHAT_HUMAN_EMAIL" "user"; then
    echo "Human user setup complete"
  else
    echo "WARNING: Human user setup failed"
  fi
  
  echo "===== User Setup Complete ====="
  echo "Admin: $ROCKETCHAT_ADMIN_USERNAME"
  echo "Bot: $ROCKETCHAT_BOT_USERNAME"
  echo "Human: $ROCKETCHAT_HUMAN_USERNAME"
}

# Execute main function
main
EOF

    # Create docker-compose file
    cat > docker-compose.yml << 'EOF'
version: '3'

services:
  rocketchat:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    volumes:
      - ./uploads:/app/uploads
    environment:
      - PORT=3000
      - ROOT_URL=http://localhost:3100
      - MONGO_URL=mongodb://mongo:27017/rocketchat
      - MONGO_OPLOG_URL=mongodb://mongo:27017/local
      - OVERWRITE_SETTING_Show_Setup_Wizard=completed
      # User configuration
      - ROCKETCHAT_ADMIN_USERNAME=admin
      - ROCKETCHAT_ADMIN_PASSWORD=dxIsDLnhiqKfDt5J
      - ROCKETCHAT_ADMIN_EMAIL=admin@heyken.local
      - ROCKETCHAT_BOT_USERNAME=heyken_bot
      - ROCKETCHAT_BOT_PASSWORD=heyken123
      - ROCKETCHAT_BOT_EMAIL=bot@heyken.local
      - ROCKETCHAT_HUMAN_USERNAME=user
      - ROCKETCHAT_HUMAN_PASSWORD=user123
      - ROCKETCHAT_HUMAN_EMAIL=user@heyken.local
    depends_on:
      - mongo
    ports:
      - 3100:3000

  mongo:
    image: mongo:5.0
    restart: unless-stopped
    volumes:
      - ./data/db:/data/db
      - ./data/dump:/dump
    command: mongod --oplogSize 128 --replSet rs0 --storageEngine=wiredTiger

  mongo-init-replica:
    image: mongo:5.0
    restart: "no"
    depends_on:
      - mongo
    command: >
      bash -c "
        echo 'Waiting for MongoDB to start...' &&
        sleep 10 &&
        mongo mongo/rocketchat --eval \"
          rs.initiate({
            _id: 'rs0',
            members: [ { _id: 0, host: 'mongo:27017' } ]
          })
        \"
      "
EOF

    # Make scripts executable
    chmod +x entrypoint.sh setup-users.sh
    
    # Start containers
    echo -e "${GREEN}Building and starting Docker containers...${NC}"
    docker-compose up -d
    
    echo -e "${YELLOW}Waiting for setup to complete...${NC}"
    sleep 10
    docker-compose logs -f rocketchat
    ;;
    
  *)
    echo -e "${RED}Invalid method: $METHOD${NC}"
    echo "Valid methods are:"
    echo "  1 - Docker Compose with separate setup service"
    echo "  2 - Standalone script for existing installation"
    echo "  3 - Custom Docker image with integrated setup"
    exit 1
    ;;
esac

echo -e "${GREEN}=========================================="
echo "Setup complete!"
echo -e "===========================================${NC}"
echo "Rocket.Chat should be available at: http://localhost:3100"
echo ""
echo "Default users:"
echo "- Admin: $ROCKETCHAT_ADMIN_USERNAME / $ROCKETCHAT_ADMIN_PASSWORD"
echo "- Bot: $ROCKETCHAT_BOT_USERNAME / $ROCKETCHAT_BOT_PASSWORD"
echo "- Human: $ROCKETCHAT_HUMAN_USERNAME / $ROCKETCHAT_HUMAN_PASSWORD"
echo ""
echo -e "${YELLOW}If you need help, check the logs:${NC}"
echo "  docker-compose logs -f"