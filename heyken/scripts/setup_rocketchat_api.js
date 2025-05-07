// RocketChat setup using direct API calls
const axios = require('axios');
require('dotenv').config({ path: '../.env' });

// Configuration
const config = {
  adminName: 'Administrator',
  adminUsername: process.env.ROCKETCHAT_ADMIN_USERNAME || 'admin',
  adminEmail: process.env.ROCKETCHAT_ADMIN_EMAIL || 'admin@heyken.local',
  adminPassword: process.env.ROCKETCHAT_ADMIN_PASSWORD || 'dxIsDLnhiqKfDt5J',
  organizationType: 'community',
  organizationName: 'Heyken',
  rocketChatUrl: 'http://localhost:3100',
  botUsername: process.env.ROCKETCHAT_BOT_USERNAME || 'heyken_bot',
  botEmail: process.env.ROCKETCHAT_BOT_EMAIL || 'bot@heyken.local',
  botPassword: process.env.ROCKETCHAT_BOT_PASSWORD || 'heyken123',
  humanUsername: process.env.ROCKETCHAT_HUMAN_USERNAME || 'user',
  humanEmail: process.env.ROCKETCHAT_HUMAN_EMAIL || 'user@heyken.local',
  humanPassword: process.env.ROCKETCHAT_HUMAN_PASSWORD || 'user123'
};

// API client
const api = axios.create({
  baseURL: config.rocketChatUrl,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Sleep function
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function setupRocketChat() {
  console.log('Starting RocketChat API setup...');
  
  try {
    // Step 1: Check if RocketChat is accessible
    console.log('Checking if RocketChat is accessible...');
    await api.get('/api/info');
    console.log('RocketChat is accessible.');
    
    // Step 2: Complete the setup wizard
    console.log('Completing setup wizard...');
    
    // Step 2.1: Organization info
    await api.post('/api/v1/setupWizard', {
      organizationType: config.organizationType,
      organizationName: config.organizationName,
      organizationIndustry: 'technology',
      organizationSize: '1-10',
      country: 'worldwide',
      language: 'en',
      serverType: 'on-premise',
      registrationOptIn: false,
      agreePrivacyTerms: true,
      agreeTerms: true
    }).catch(err => {
      console.log('Setup wizard organization step error (might be already completed):', err.message);
    });
    
    // Step 2.2: Admin user
    await api.post('/api/v1/setupWizard/admin-user', {
      username: config.adminUsername,
      password: config.adminPassword,
      email: config.adminEmail,
      name: config.adminName
    }).catch(err => {
      console.log('Setup wizard admin user step error (might be already completed):', err.message);
    });
    
    // Wait for setup to complete
    console.log('Waiting for setup to complete...');
    await sleep(5000);
    
    // Step 3: Login as admin
    console.log('Logging in as admin...');
    const loginResponse = await api.post('/api/v1/login', {
      username: config.adminUsername,
      password: config.adminPassword
    }).catch(err => {
      console.error('Login error:', err.response?.data || err.message);
      throw new Error('Failed to login as admin');
    });
    
    const { authToken, userId } = loginResponse.data.data;
    
    // Update API client with auth headers
    api.defaults.headers['X-Auth-Token'] = authToken;
    api.defaults.headers['X-User-Id'] = userId;
    
    console.log('Successfully logged in as admin.');
    
    // Step 4: Create bot user
    console.log('Creating bot user...');
    await api.post('/api/v1/users.create', {
      name: 'Heyken Bot',
      email: config.botEmail,
      password: config.botPassword,
      username: config.botUsername,
      roles: ['user'],
      joinDefaultChannels: true,
      requirePasswordChange: false,
      sendWelcomeEmail: false
    }).catch(err => {
      if (err.response?.data?.error?.includes('Username is already in use')) {
        console.log('Bot user already exists.');
      } else {
        console.error('Error creating bot user:', err.response?.data || err.message);
      }
    });
    
    // Step 5: Create human user
    console.log('Creating human user...');
    await api.post('/api/v1/users.create', {
      name: 'Human User',
      email: config.humanEmail,
      password: config.humanPassword,
      username: config.humanUsername,
      roles: ['user'],
      joinDefaultChannels: true,
      requirePasswordChange: false,
      sendWelcomeEmail: false
    }).catch(err => {
      if (err.response?.data?.error?.includes('Username is already in use')) {
        console.log('Human user already exists.');
      } else {
        console.error('Error creating human user:', err.response?.data || err.message);
      }
    });
    
    // Step 6: Create channels
    console.log('Creating channels...');
    const channels = ['heyken-system', 'heyken-logs', 'heyken-sandbox'];
    
    for (const channel of channels) {
      // Create public channel
      const isPrivate = channel === 'heyken-sandbox';
      const endpoint = isPrivate ? '/api/v1/groups.create' : '/api/v1/channels.create';
      
      await api.post(endpoint, {
        name: channel
      }).catch(err => {
        if (err.response?.data?.error?.includes('Channel already exists')) {
          console.log(`Channel ${channel} already exists.`);
        } else {
          console.error(`Error creating channel ${channel}:`, err.response?.data || err.message);
        }
      });
      
      // Add bot user to channel
      await addUserToChannel(config.botUsername, channel, isPrivate);
      
      // Add human user to channel
      await addUserToChannel(config.humanUsername, channel, isPrivate);
    }
    
    console.log('RocketChat setup completed successfully!');
    
  } catch (error) {
    console.error('Error during setup:', error);
  }
}

async function addUserToChannel(username, channel, isPrivate) {
  try {
    // First get user ID
    const userResponse = await api.get(`/api/v1/users.info?username=${username}`);
    const userId = userResponse.data.user._id;
    
    // Add user to channel
    const endpoint = isPrivate ? '/api/v1/groups.invite' : '/api/v1/channels.invite';
    
    // First get channel/group ID
    const roomEndpoint = isPrivate ? '/api/v1/groups.info' : '/api/v1/channels.info';
    const roomResponse = await api.get(`${roomEndpoint}?roomName=${channel}`);
    const roomId = isPrivate ? roomResponse.data.group._id : roomResponse.data.channel._id;
    
    await api.post(endpoint, {
      roomId,
      userId
    });
    
    console.log(`Added ${username} to ${channel}`);
  } catch (error) {
    console.error(`Error adding ${username} to ${channel}:`, error.response?.data || error.message);
  }
}

// Install required dependencies if not already installed
const { execSync } = require('child_process');

try {
  require.resolve('axios');
  require.resolve('dotenv');
} catch (e) {
  console.log('Installing required dependencies...');
  execSync('npm install axios dotenv', { stdio: 'inherit' });
}

// Run the setup
setupRocketChat().catch(console.error);
