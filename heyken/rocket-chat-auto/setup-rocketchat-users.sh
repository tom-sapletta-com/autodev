#!/bin/sh
# Script to set up RocketChat users using only curl

# Set default values for environment variables
ROCKETCHAT_URL="${ROCKETCHAT_URL:-http://localhost:3100}"
ROCKETCHAT_ADMIN_USERNAME="${ROCKETCHAT_ADMIN_USERNAME:-admin}"
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
    echo "1. Open http://localhost:3100 in your browser"
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
  echo "Access RocketChat at: http://localhost:3100"
  echo "Access Mailhog at: http://localhost:8025"
  echo "=========================================================="
}

# Execute main function
main
