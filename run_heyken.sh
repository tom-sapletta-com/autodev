#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "\033[0;32m==================================================\033[0m"
echo -e "\033[0;32m  Starting Heyken System                          \033[0m"
echo -e "\033[0;32m==================================================\033[0m"

# Start RocketChat
echo -e "\033[1;33mStarting RocketChat...\033[0m"
cd docker/rocketchat
docker-compose -f docker-compose-final-fixed.yml up -d
cd ../..

echo -e "\033[0;32m==================================================\033[0m"
echo -e "\033[0;32m  Heyken System Started                           \033[0m"
echo -e "\033[0;32m==================================================\033[0m"
echo -e "\033[0;32mRocketChat: http://localhost:3100\033[0m"
echo -e "\033[0;32mAdmin: heyken_admin / dxIsDLnhiqKfDt5J\033[0m"
echo -e "\033[0;32mBot: heyken_bot / heyken123\033[0m"
echo -e "\033[0;32mUser: heyken_user / user123\033[0m"
echo -e "\033[0;32m==================================================\033[0m"
