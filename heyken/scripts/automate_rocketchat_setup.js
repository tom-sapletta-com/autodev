// Automated RocketChat setup script using Puppeteer
const puppeteer = require('puppeteer');
require('dotenv').config({ path: '../.env' });

// Configuration from environment variables or defaults
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

async function setupRocketChat() {
  console.log('Starting RocketChat automated setup...');
  
  const browser = await puppeteer.launch({
    headless: false, // Set to true for production
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: null
  });
  
  try {
    const page = await browser.newPage();
    
    // Navigate to RocketChat
    console.log(`Navigating to ${config.rocketChatUrl}...`);
    await page.goto(config.rocketChatUrl, { waitUntil: 'networkidle2', timeout: 60000 });
    
    // Wait for the setup wizard to load
    console.log('Waiting for setup wizard...');
    await page.waitForSelector('.setup-wizard', { timeout: 60000 })
      .catch(() => {
        console.log('Setup wizard not found. RocketChat might be already configured.');
        return null;
      });
    
    // Check if we're on the setup wizard
    const isSetupWizard = await page.evaluate(() => {
      return window.location.href.includes('setup-wizard');
    });
    
    if (!isSetupWizard) {
      console.log('Not on setup wizard page. RocketChat might be already configured.');
      await browser.close();
      return;
    }
    
    // Step 1: Organization Info
    console.log('Completing organization info...');
    await page.waitForSelector('select[name="organizationType"]');
    await page.select('select[name="organizationType"]', config.organizationType);
    await page.type('input[name="organizationName"]', config.organizationName);
    await page.select('select[name="organizationIndustry"]', 'technology');
    await page.select('select[name="organizationSize"]', '1-10');
    
    // Click Continue
    await page.click('button[type="submit"]');
    
    // Step 2: Register Server (skip)
    console.log('Skipping server registration...');
    await page.waitForSelector('input[name="registerServer"]');
    await page.evaluate(() => {
      const checkbox = document.querySelector('input[name="registerServer"]');
      if (checkbox.checked) {
        checkbox.click();
      }
    });
    
    // Click Continue
    await page.click('button[type="submit"]');
    
    // Step 3: Admin User
    console.log('Setting up admin user...');
    await page.waitForSelector('input[name="adminName"]');
    await page.type('input[name="adminName"]', config.adminName);
    await page.type('input[name="adminUsername"]', config.adminUsername);
    await page.type('input[name="adminEmail"]', config.adminEmail);
    await page.type('input[name="adminPassword"]', config.adminPassword);
    
    // Click Continue
    await page.click('button[type="submit"]');
    
    // Step 4: Server Info
    console.log('Configuring server info...');
    await page.waitForSelector('input[name="siteName"]');
    await page.type('input[name="siteName"]', 'Heyken');
    
    // Click Continue/Finish
    await page.click('button[type="submit"]');
    
    // Wait for setup to complete
    console.log('Waiting for setup to complete...');
    await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 60000 });
    
    // Login as admin
    console.log('Logging in as admin...');
    await page.waitForSelector('input[name="username"]');
    await page.type('input[name="username"]', config.adminUsername);
    await page.type('input[name="password"]', config.adminPassword);
    await page.click('button[type="submit"]');
    
    // Wait for login to complete
    await page.waitForSelector('.sidebar', { timeout: 60000 });
    
    // Create bot user
    console.log('Creating bot user...');
    await page.goto(`${config.rocketChatUrl}/admin/users/new`, { waitUntil: 'networkidle2' });
    
    await page.waitForSelector('input[name="name"]');
    await page.type('input[name="name"]', 'Heyken Bot');
    await page.type('input[name="username"]', config.botUsername);
    await page.type('input[name="email"]', config.botEmail);
    await page.type('input[name="password"]', config.botPassword);
    await page.type('input[name="password-confirm"]', config.botPassword);
    
    // Submit form
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);
    
    // Create human user
    console.log('Creating human user...');
    await page.goto(`${config.rocketChatUrl}/admin/users/new`, { waitUntil: 'networkidle2' });
    
    await page.waitForSelector('input[name="name"]');
    await page.type('input[name="name"]', 'Human User');
    await page.type('input[name="username"]', config.humanUsername);
    await page.type('input[name="email"]', config.humanEmail);
    await page.type('input[name="password"]', config.humanPassword);
    await page.type('input[name="password-confirm"]', config.humanPassword);
    
    // Submit form
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);
    
    // Create channels
    console.log('Creating channels...');
    const channels = ['heyken-system', 'heyken-logs', 'heyken-sandbox'];
    
    for (const channel of channels) {
      await page.goto(`${config.rocketChatUrl}/admin/rooms/new/c`, { waitUntil: 'networkidle2' });
      await page.waitForSelector('input[name="name"]');
      await page.type('input[name="name"]', channel);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    }
    
    console.log('RocketChat setup completed successfully!');
    
  } catch (error) {
    console.error('Error during setup:', error);
  } finally {
    await browser.close();
  }
}

setupRocketChat().catch(console.error);
