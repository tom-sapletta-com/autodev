#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken - Continuing Infrastructure Deployment    ${NC}"
echo -e "${GREEN}==================================================${NC}"

echo -e "${YELLOW}Skipping RocketChat check and continuing with infrastructure deployment...${NC}"

# 1. Initialize the system if not already done
if [ ! -f ./.initialized ]; then
    echo -e "${YELLOW}System not initialized. Running initialization...${NC}"
    ./scripts/init.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}Initialization failed!${NC}"
        exit 1
    fi
    touch ./.initialized
fi

# 2. Run the deployment script
echo -e "${GREEN}Deploying the Heyken system...${NC}"
./scripts/deploy.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}Deployment failed!${NC}"
    exit 1
fi

# 3. Check system status
echo -e "${GREEN}Checking system status...${NC}"
./scripts/status.sh

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken system infrastructure deployed!          ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${YELLOW}Note: RocketChat has MongoDB version compatibility issues.${NC}"
echo -e "${YELLOW}MongoDB 4.0 is being used, but RocketChat requires 5.0+${NC}"
echo -e "${GREEN}To check system status: ./scripts/status.sh${NC}"
echo -e "${GREEN}To switch cores: ./scripts/switch_core.sh [1|2]${NC}"
