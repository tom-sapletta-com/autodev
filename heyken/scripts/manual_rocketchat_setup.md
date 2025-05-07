# Manual RocketChat Setup Instructions

## Step 1: Access RocketChat Setup Wizard
1. Open your browser and go to http://localhost:3100
2. You will be presented with the RocketChat setup wizard

## Step 2: Complete the Setup Wizard
1. **Organization Info**:
   - Organization Type: Community
   - Organization Name: Heyken
   - Industry: Technology
   - Size: 1-10 people
   - Country: Your country
   - Website: (leave blank)

2. **Register Server**:
   - Uncheck "Register your server" to skip registration

3. **Admin User**:
   - Name: Administrator
   - Username: admin
   - Email: admin@example.com
   - Password: dxIsDLnhiqKfDt5J

4. **Server Info**:
   - Site Name: Heyken
   - Language: English

## Step 3: Create Additional Users
After completing the setup wizard and logging in as admin:

1. **Create Bot User**:
   - Go to Administration → Users → New
   - Name: Heyken Bot
   - Username: heyken_bot
   - Email: heyken_bot@example.com
   - Password: heyken123
   - Role: user

2. **Create Human User**:
   - Go to Administration → Users → New
   - Name: Human User
   - Username: user
   - Email: user@example.com
   - Password: user123
   - Role: user

## Step 4: Create Channels
1. Click the "+" button next to Channels
2. Select "Create Channel"
3. Create the following channels:
   - heyken-system (Public)
   - heyken-logs (Public)
   - heyken-sandbox (Private)

4. Add both the bot user and human user to all channels

## Step 5: Configure System Settings
1. Go to Administration → Settings
2. Under "Accounts", set:
   - Registration Form: Disabled
   - Manually Approve New Users: Enabled

## Step 6: Login as User
1. Logout from the admin account
2. Login with:
   - Username: user
   - Password: user123

## Troubleshooting
If you encounter issues with the setup:
1. Stop all containers: `./stop.sh`
2. Remove the RocketChat data directory: `sudo rm -rf docker/rocketchat/data_auto`
3. Start again: `./run_heyken.sh`
