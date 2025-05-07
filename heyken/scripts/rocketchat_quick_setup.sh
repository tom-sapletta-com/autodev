#!/bin/bash

# Colors for messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Heyken - RocketChat Quick Setup                 ${NC}"
echo -e "${GREEN}==================================================${NC}"

# 1. Stop any running RocketChat instances
echo -e "${YELLOW}Stopping any running RocketChat instances...${NC}"
cd ../docker/rocketchat
docker-compose -f docker-compose-auto.yml down -v 2>/dev/null || true
docker-compose -f docker-compose-new.yml down -v 2>/dev/null || true
docker-compose down -v 2>/dev/null || true
cd ../..

# 2. Clean up data directories
echo -e "${YELLOW}Cleaning up data directories...${NC}"
sudo rm -rf docker/rocketchat/data_auto docker/rocketchat/data_new docker/rocketchat/data 2>/dev/null || true

# 3. Create a simple docker-compose file
echo -e "${YELLOW}Creating a simple RocketChat configuration...${NC}"
cat > docker/rocketchat/docker-compose-simple.yml << 'EOF'
version: '3'

services:
  mongodb:
    image: mongo:5.0
    restart: always
    volumes:
      - ./data_simple/db:/data/db
    command: mongod --oplogSize 128 --replSet rs0
    networks:
      - rocketchat

  mongodb-init:
    image: mongo:5.0
    restart: on-failure
    command: >
      bash -c "sleep 10 && mongosh mongodb/rocketchat --eval \"rs.initiate({ _id: 'rs0', members: [ { _id: 0, host: 'mongodb:27017' } ]})\""
    depends_on:
      - mongodb
    networks:
      - rocketchat

  rocketchat:
    image: registry.rocket.chat/rocketchat/rocket.chat:7.5.1
    restart: always
    volumes:
      - ./uploads_simple:/app/uploads
    environment:
      - ROOT_URL=http://localhost:3100
      - MONGO_URL=mongodb://mongodb:27017/rocketchat
      - MONGO_OPLOG_URL=mongodb://mongodb:27017/local
      - PORT=3000
    depends_on:
      - mongodb
    ports:
      - 3100:3000
    networks:
      - rocketchat
      - system_network

networks:
  rocketchat:
    driver: bridge
  system_network:
    external: true
EOF

# 4. Start RocketChat with the simple configuration
echo -e "${YELLOW}Starting RocketChat with simple configuration...${NC}"
cd docker/rocketchat
docker-compose -f docker-compose-simple.yml up -d
cd ../..

# 5. Wait for RocketChat to be ready
echo -e "${YELLOW}Waiting for RocketChat to be ready...${NC}"
MAX_ATTEMPTS=30
ATTEMPT=0
ROCKETCHAT_READY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  echo -n "."
  # Try to connect to RocketChat
  if curl -s http://localhost:3100 > /dev/null; then
    echo -e "\n${GREEN}RocketChat is now accessible!${NC}"
    ROCKETCHAT_READY=true
    break
  fi
  ATTEMPT=$((ATTEMPT+1))
  sleep 5
done

if [ "$ROCKETCHAT_READY" = false ]; then
  echo -e "${RED}RocketChat failed to start properly after $(($MAX_ATTEMPTS * 5)) seconds.${NC}"
  exit 1
fi

# 6. Provide instructions for manual setup
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  RocketChat is now running at:                   ${NC}"
echo -e "${GREEN}  http://localhost:3100                           ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "${YELLOW}Please complete the following steps manually:${NC}"
echo -e "1. Open http://localhost:3100 in your browser"
echo -e "2. Complete the setup wizard with the following information:"
echo -e "   - Organization Type: Community"
echo -e "   - Organization Name: Heyken"
echo -e "   - Admin Name: Administrator"
echo -e "   - Admin Username: admin"
echo -e "   - Admin Email: admin@heyken.local"
echo -e "   - Admin Password: dxIsDLnhiqKfDt5J"
echo -e "3. After setup is complete, login as admin"
echo -e "4. Go to Administration → Users → New"
echo -e "5. Create a user with:"
echo -e "   - Name: Human User"
echo -e "   - Username: user"
echo -e "   - Email: user@heyken.local"
echo -e "   - Password: user123"
echo -e "6. Create another user with:"
echo -e "   - Name: Heyken Bot"
echo -e "   - Username: heyken_bot"
echo -e "   - Email: bot@heyken.local"
echo -e "   - Password: heyken123"
echo -e "7. Create channels: heyken-system, heyken-logs, heyken-sandbox"
echo -e "8. Add both users to all channels"
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}After completing these steps, you can continue    ${NC}"
echo -e "${GREEN}with the Heyken deployment by running:            ${NC}"
echo -e "${GREEN}./continue_heyken_deployment.sh                   ${NC}"
echo -e "${GREEN}==================================================${NC}"
