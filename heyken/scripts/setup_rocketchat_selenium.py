#!/usr/bin/env python3
"""
RocketChat setup automation using Selenium
This script automates the RocketChat setup process through the web interface
"""

import os
import sys
import time
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('../.env')

# Configuration
config = {
    'admin_name': 'Administrator',
    'admin_username': os.getenv('ROCKETCHAT_ADMIN_USERNAME', 'admin'),
    'admin_email': os.getenv('ROCKETCHAT_ADMIN_EMAIL', 'admin@heyken.local'),
    'admin_password': os.getenv('ROCKETCHAT_ADMIN_PASSWORD', 'dxIsDLnhiqKfDt5J'),
    'organization_type': 'community',
    'organization_name': 'Heyken',
    'rocketchat_url': 'http://localhost:3100',
    'bot_username': os.getenv('ROCKETCHAT_BOT_USERNAME', 'heyken_bot'),
    'bot_email': os.getenv('ROCKETCHAT_BOT_EMAIL', 'bot@heyken.local'),
    'bot_password': os.getenv('ROCKETCHAT_BOT_PASSWORD', 'heyken123'),
    'human_username': os.getenv('ROCKETCHAT_HUMAN_USERNAME', 'user'),
    'human_email': os.getenv('ROCKETCHAT_HUMAN_EMAIL', 'user@heyken.local'),
    'human_password': os.getenv('ROCKETCHAT_HUMAN_PASSWORD', 'user123')
}

def setup_driver():
    """Set up the Selenium WebDriver"""
    print("Setting up WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_window_size(1366, 768)
        return driver
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        print("Trying Firefox...")
        try:
            options = webdriver.FirefoxOptions()
            options.add_argument('--headless')
            driver = webdriver.Firefox(options=options)
            driver.set_window_size(1366, 768)
            return driver
        except Exception as e:
            print(f"Error setting up Firefox WebDriver: {e}")
            sys.exit(1)

def wait_for_element(driver, by, value, timeout=30):
    """Wait for an element to be present and visible"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        print(f"Timeout waiting for element: {value}")
        return None

def complete_setup_wizard(driver):
    """Complete the RocketChat setup wizard"""
    print("Navigating to RocketChat...")
    driver.get(config['rocketchat_url'])
    
    # Check if we're on the setup wizard
    try:
        # Wait for the setup wizard to load
        print("Checking for setup wizard...")
        setup_wizard = wait_for_element(driver, By.CSS_SELECTOR, '.setup-wizard', timeout=10)
        
        if not setup_wizard:
            print("Setup wizard not found. RocketChat might be already configured.")
            return True
        
        print("Setup wizard found. Proceeding with setup...")
        
        # Step 1: Organization Info
        print("Step 1: Completing organization info...")
        
        # Wait for the organization type dropdown to be visible
        org_type_select = wait_for_element(driver, By.NAME, 'organizationType')
        if not org_type_select:
            return False
        
        # Select organization type
        Select(org_type_select).select_by_value(config['organization_type'])
        
        # Fill organization name
        org_name_input = driver.find_element(By.NAME, 'organizationName')
        org_name_input.clear()
        org_name_input.send_keys(config['organization_name'])
        
        # Select industry
        industry_select = driver.find_element(By.NAME, 'organizationIndustry')
        Select(industry_select).select_by_value('technology')
        
        # Select size
        size_select = driver.find_element(By.NAME, 'organizationSize')
        Select(size_select).select_by_value('1-10')
        
        # Select country
        country_select = driver.find_element(By.NAME, 'country')
        Select(country_select).select_by_value('worldwide')
        
        # Click Continue
        continue_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        continue_button.click()
        
        # Step 2: Register Server (skip)
        print("Step 2: Skipping server registration...")
        
        # Wait for the register server checkbox
        register_checkbox = wait_for_element(driver, By.NAME, 'registerServer')
        if not register_checkbox:
            return False
        
        # Uncheck the register server checkbox if it's checked
        if register_checkbox.is_selected():
            register_checkbox.click()
        
        # Click Continue
        continue_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        continue_button.click()
        
        # Step 3: Admin User
        print("Step 3: Setting up admin user...")
        
        # Wait for the admin name input
        admin_name_input = wait_for_element(driver, By.NAME, 'adminName')
        if not admin_name_input:
            return False
        
        # Fill admin name
        admin_name_input.clear()
        admin_name_input.send_keys(config['admin_name'])
        
        # Fill admin username
        admin_username_input = driver.find_element(By.NAME, 'adminUsername')
        admin_username_input.clear()
        admin_username_input.send_keys(config['admin_username'])
        
        # Fill admin email
        admin_email_input = driver.find_element(By.NAME, 'adminEmail')
        admin_email_input.clear()
        admin_email_input.send_keys(config['admin_email'])
        
        # Fill admin password
        admin_password_input = driver.find_element(By.NAME, 'adminPassword')
        admin_password_input.clear()
        admin_password_input.send_keys(config['admin_password'])
        
        # Click Continue
        continue_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        continue_button.click()
        
        # Step 4: Server Info
        print("Step 4: Configuring server info...")
        
        # Wait for the site name input
        site_name_input = wait_for_element(driver, By.NAME, 'siteName')
        if not site_name_input:
            return False
        
        # Fill site name
        site_name_input.clear()
        site_name_input.send_keys('Heyken')
        
        # Click Finish
        finish_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        finish_button.click()
        
        # Wait for setup to complete
        print("Waiting for setup to complete...")
        time.sleep(10)
        
        return True
        
    except NoSuchElementException as e:
        print(f"Element not found: {e}")
        return False
    except Exception as e:
        print(f"Error during setup wizard: {e}")
        return False

def login_as_admin(driver):
    """Login as admin user"""
    print("Logging in as admin...")
    
    try:
        # Navigate to login page
        driver.get(f"{config['rocketchat_url']}/home")
        
        # Wait for the username input
        username_input = wait_for_element(driver, By.NAME, 'username')
        if not username_input:
            return False
        
        # Fill username
        username_input.clear()
        username_input.send_keys(config['admin_username'])
        
        # Fill password
        password_input = driver.find_element(By.NAME, 'password')
        password_input.clear()
        password_input.send_keys(config['admin_password'])
        
        # Click Login
        login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        login_button.click()
        
        # Wait for login to complete
        sidebar = wait_for_element(driver, By.CSS_SELECTOR, '.sidebar')
        if not sidebar:
            return False
        
        print("Successfully logged in as admin.")
        return True
        
    except Exception as e:
        print(f"Error during login: {e}")
        return False

def create_user(driver, username, password, email, name):
    """Create a new user"""
    print(f"Creating user: {username}...")
    
    try:
        # Navigate to new user page
        driver.get(f"{config['rocketchat_url']}/admin/users/new")
        
        # Wait for the name input
        name_input = wait_for_element(driver, By.NAME, 'name')
        if not name_input:
            return False
        
        # Fill name
        name_input.clear()
        name_input.send_keys(name)
        
        # Fill username
        username_input = driver.find_element(By.NAME, 'username')
        username_input.clear()
        username_input.send_keys(username)
        
        # Fill email
        email_input = driver.find_element(By.NAME, 'email')
        email_input.clear()
        email_input.send_keys(email)
        
        # Fill password
        password_input = driver.find_element(By.NAME, 'password')
        password_input.clear()
        password_input.send_keys(password)
        
        # Fill password confirmation
        password_confirm_input = driver.find_element(By.NAME, 'password-confirm')
        password_confirm_input.clear()
        password_confirm_input.send_keys(password)
        
        # Click Save
        save_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        save_button.click()
        
        # Wait for save to complete
        time.sleep(3)
        
        print(f"User {username} created successfully.")
        return True
        
    except Exception as e:
        print(f"Error creating user {username}: {e}")
        return False

def create_channel(driver, channel_name, is_private=False):
    """Create a new channel"""
    print(f"Creating channel: {channel_name}...")
    
    try:
        # Navigate to new channel page
        channel_type = 'p' if is_private else 'c'
        driver.get(f"{config['rocketchat_url']}/admin/rooms/new/{channel_type}")
        
        # Wait for the name input
        name_input = wait_for_element(driver, By.NAME, 'name')
        if not name_input:
            return False
        
        # Fill name
        name_input.clear()
        name_input.send_keys(channel_name)
        
        # Click Save
        save_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        save_button.click()
        
        # Wait for save to complete
        time.sleep(3)
        
        print(f"Channel {channel_name} created successfully.")
        return True
        
    except Exception as e:
        print(f"Error creating channel {channel_name}: {e}")
        return False

def main():
    """Main function"""
    print("Starting RocketChat setup automation...")
    
    # Set up WebDriver
    driver = setup_driver()
    
    try:
        # Complete setup wizard
        if not complete_setup_wizard(driver):
            print("Failed to complete setup wizard.")
            return
        
        # Login as admin
        if not login_as_admin(driver):
            print("Failed to login as admin.")
            return
        
        # Create bot user
        create_user(
            driver,
            config['bot_username'],
            config['bot_password'],
            config['bot_email'],
            'Heyken Bot'
        )
        
        # Create human user
        create_user(
            driver,
            config['human_username'],
            config['human_password'],
            config['human_email'],
            'Human User'
        )
        
        # Create channels
        create_channel(driver, 'heyken-system')
        create_channel(driver, 'heyken-logs')
        create_channel(driver, 'heyken-sandbox', is_private=True)
        
        print("RocketChat setup completed successfully!")
        print(f"Admin user: {config['admin_username']} / {config['admin_password']}")
        print(f"Bot user: {config['bot_username']} / {config['bot_password']}")
        print(f"Human user: {config['human_username']} / {config['human_password']}")
        print("Created channels: heyken-system, heyken-logs, heyken-sandbox")
        print(f"You can now access RocketChat at: {config['rocketchat_url']}")
        
    except Exception as e:
        print(f"Error during setup: {e}")
    finally:
        # Close the WebDriver
        driver.quit()

if __name__ == "__main__":
    main()
