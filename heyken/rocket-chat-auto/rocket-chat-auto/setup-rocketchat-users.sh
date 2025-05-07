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
