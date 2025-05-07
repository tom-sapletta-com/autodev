#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken - Starting System                        ${NC}"
echo -e "${GREEN}==================================================${NC}"

# 1. Start RocketChat first
# Start Email Server
echo -e "${YELLOW}Starting Email Server...${NC}"
cd docker/mailserver
docker-compose up -d
cd ../..

# Start Email Server
echo -e "${YELLOW}Starting Email Server...${NC}"
cd docker/mailserver
docker-compose up -d
cd ../..

echo -e "${GREEN}Starting RocketChat services...${NC}"
cd docker/rocketchat

# Check if simple configuration exists
if [ -f docker-compose-email.yml ]; then
    echo -e "${GREEN}Using simplified RocketChat setup...${NC}"
    docker-compose -f docker-compose-email.yml up -d
# Check if custom configuration exists
elif [ -f docker-compose-email.yml ]; then
    echo -e "${GREEN}Using custom RocketChat setup...${NC}"
    docker-compose -f docker-compose-email.yml up -d
# Try to use the auto-configuration file next
elif [ -f docker-compose-email.yml ]; then
    echo -e "${GREEN}Using auto-configured RocketChat setup...${NC}"
    docker-compose -f docker-compose-email.yml up -d
else
    # Fall back to the new configuration if custom and auto config are not available
    echo -e "${YELLOW}Using standard RocketChat setup...${NC}"
    docker-compose -f docker-compose-email.yml up -d
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to start RocketChat services!${NC}"
    exit 1
fi
echo -e "${GREEN}RocketChat services started successfully.${NC}"
cd ../..

# Wait for RocketChat to be fully operational
echo -e "${YELLOW}Waiting for RocketChat to be fully operational...${NC}"
MAX_ATTEMPTS=30
ATTEMPT=0
ROCKETCHAT_READY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    echo -n "."
    # Try to connect to RocketChat
    if curl -s http://localhost:3100 > /dev/null; then
        echo -e "\n${GREEN}RocketChat is now operational!${NC}"
        ROCKETCHAT_READY=true
        break
    fi
    ATTEMPT=$((ATTEMPT+1))
    sleep 5
done

if [ "$ROCKETCHAT_READY" = false ]; then
    echo -e "\n${RED}RocketChat failed to start properly after $(($MAX_ATTEMPTS * 5)) seconds.${NC}"
    echo -e "${YELLOW}Continuing with the rest of the infrastructure anyway...${NC}"
else
    # Configure RocketChat with users
    echo -e "${GREEN}Setting up RocketChat users and channels...${NC}"
    cd scripts
    
    # Try to use the simple setup script first
    if [ -f setup_rocketchat_simple.sh ]; then
        ./setup_rocketchat_simple.sh
    # Try to use the complete setup script next
    elif [ -f setup_rocketchat_complete.sh ]; then
        ./setup_rocketchat_complete.sh
    # Try to use the fixed setup script next
    elif [ -f setup_rocketchat_fixed.sh ]; then
        ./setup_rocketchat_fixed.sh
    else
        # Fall back to the original setup script
        ./setup_rocketchat.sh
    fi
    
    cd ..
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}RocketChat setup had some issues, but continuing...${NC}"
    else
        echo -e "${GREEN}RocketChat setup completed successfully.${NC}"
    fi
fi

# 2. Initialize the system if not already done
if [ ! -f ./.initialized ]; then
    echo -e "${YELLOW}System not initialized. Running initialization...${NC}"
    ./scripts/init.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}Initialization failed!${NC}"
        exit 1
    fi
    touch ./.initialized
fi

# 3. Run the deployment script
echo -e "${GREEN}Deploying the Heyken system...${NC}"
./scripts/deploy.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}Deployment failed!${NC}"
    exit 1
fi

# 4. Check system status
echo -e "${GREEN}Checking system status...${NC}"
./scripts/status.sh

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken system started successfully!             ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}RocketChat is available at: http://localhost:3100${NC}"
echo -e "${GREEN}Login with: user / user123${NC}"
echo -e "${GREEN}To check system status: ./scripts/status.sh${NC}"
echo -e "${GREEN}To switch cores: ./scripts/switch_core.sh [1|2]${NC}"
