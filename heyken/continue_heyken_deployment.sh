#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken - Continuing System Deployment            ${NC}"
echo -e "${GREEN}==================================================${NC}"

# Verify RocketChat is running
echo -e "${GREEN}Verifying RocketChat is operational...${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3100 | grep -q "200"; then
    echo -e "${GREEN}RocketChat is operational at http://localhost:3100${NC}"
else
    echo -e "${RED}RocketChat is not responding properly!${NC}"
    echo -e "${YELLOW}Continuing with system deployment anyway...${NC}"
fi

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
echo -e "${GREEN}  Heyken system deployment completed!             ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}RocketChat is available at: http://localhost:3100${NC}"
echo -e "${GREEN}GitLab is available at: http://localhost:8080${NC}"
echo -e "${GREEN}Sandbox Manager is available at: http://localhost:5010${NC}"
echo -e "${GREEN}System Monitor is available at: http://localhost:5021${NC}"
echo -e "${GREEN}Logger API is available at: http://localhost:5020${NC}"
echo -e "${GREEN}To check system status: ./scripts/status.sh${NC}"
echo -e "${GREEN}To switch cores: ./scripts/switch_core.sh [1|2]${NC}"
