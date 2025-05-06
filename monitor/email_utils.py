#!/usr/bin/env python3
import os
import smtplib
import imaplib
import email
import email.mime.text
import email.mime.multipart
import subprocess
import logging
import json
import docker
from pathlib import Path

logger = logging.getLogger('evodev-monitor')

# Email configuration
EMAIL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'email_config.json')

def get_email_config():
    """Get email configuration from config file or create default"""
    if os.path.exists(EMAIL_CONFIG_PATH):
        try:
            with open(EMAIL_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading email config: {str(e)}")
            return {}
    return {}

def save_email_config(config):
    """Save email configuration to config file"""
    try:
        with open(EMAIL_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving email config: {str(e)}")
        return False

def check_email_dependencies():
    """Check if required Python packages are installed"""
    try:
        import smtplib
        import imaplib
        import email
        return True
    except ImportError:
        return False

def install_email_dependencies():
    """Install required Python packages for email functionality"""
    try:
        subprocess.check_call(["pip", "install", "secure-smtplib", "imapclient", "email-validator"])
        return True
    except Exception as e:
        logger.error(f"Error installing email dependencies: {str(e)}")
        return False

def check_email_docker():
    """Check if email docker container is running"""
    try:
        client = docker.from_env()
        containers = client.containers.list()
        for container in containers:
            if 'mailserver' in container.name and container.status == 'running':
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking docker containers: {str(e)}")
        return False

def setup_email_docker():
    """Set up a local email server using Docker"""
    try:
        # Create docker-compose file for email server
        compose_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'email-server')
        os.makedirs(compose_dir, exist_ok=True)
        
        compose_file = os.path.join(compose_dir, 'docker-compose.yml')
        with open(compose_file, 'w') as f:
            f.write("""version: '3'

services:
  mailserver:
    image: mailserver/docker-mailserver:latest
    container_name: evodev-mailserver
    hostname: mail.evodev.local
    ports:
      - "25:25"
      - "143:143"
      - "587:587"
      - "993:993"
    volumes:
      - ./maildata:/var/mail
      - ./mailstate:/var/mail-state
      - ./config:/tmp/docker-mailserver
    environment:
      - ENABLE_SPAMASSASSIN=0
      - ENABLE_CLAMAV=0
      - ENABLE_FAIL2BAN=0
      - ENABLE_POSTGREY=0
      - ONE_DIR=1
      - DMS_DEBUG=1
    cap_add:
      - NET_ADMIN
""")
        
        # Run docker-compose up
        subprocess.check_call(["docker-compose", "up", "-d"], cwd=compose_dir)
        
        # Setup initial email account
        setup_script = os.path.join(compose_dir, 'setup.sh')
        with open(setup_script, 'w') as f:
            f.write("""#!/bin/bash
docker exec -it evodev-mailserver setup email add admin@evodev.local password123
""")
        os.chmod(setup_script, 0o755)
        subprocess.check_call([setup_script], cwd=compose_dir)
        
        # Save default configuration
        config = {
            "smtp_server": "localhost",
            "smtp_port": 25,
            "imap_server": "localhost",
            "imap_port": 143,
            "email": "admin@evodev.local",
            "password": "password123",
            "use_ssl": False
        }
        save_email_config(config)
        
        return True
    except Exception as e:
        logger.error(f"Error setting up email docker: {str(e)}")
        return False

def test_email_connection(config=None):
    """Test email connection with given configuration"""
    if config is None:
        config = get_email_config()
    
    if not config:
        return False, "No email configuration found"
    
    # Test SMTP connection
    try:
        if config.get('use_ssl', False):
            server = smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port'])
        else:
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        
        server.ehlo()
        if not config.get('use_ssl', False):
            server.starttls()
        server.login(config['email'], config['password'])
        server.quit()
    except Exception as e:
        return False, f"SMTP connection failed: {str(e)}"
    
    # Test IMAP connection
    try:
        if config.get('use_ssl', False):
            server = imaplib.IMAP4_SSL(config['imap_server'], config['imap_port'])
        else:
            server = imaplib.IMAP4(config['imap_server'], config['imap_port'])
        
        server.login(config['email'], config['password'])
        server.logout()
    except Exception as e:
        return False, f"IMAP connection failed: {str(e)}"
    
    return True, "Email connection successful"

def send_email(to, subject, body, config=None):
    """Send email using configured SMTP server"""
    if config is None:
        config = get_email_config()
    
    if not config:
        return False, "No email configuration found"
    
    try:
        msg = email.mime.multipart.MIMEMultipart()
        msg['From'] = config['email']
        msg['To'] = to
        msg['Subject'] = subject
        
        msg.attach(email.mime.text.MIMEText(body, 'plain'))
        
        if config.get('use_ssl', False):
            server = smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port'])
        else:
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        
        server.ehlo()
        if not config.get('use_ssl', False):
            server.starttls()
        server.login(config['email'], config['password'])
        server.send_message(msg)
        server.quit()
        
        return True, "Email sent successfully"
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False, f"Error sending email: {str(e)}"

def read_emails(folder='INBOX', limit=10, config=None):
    """Read emails from specified folder using IMAP"""
    if config is None:
        config = get_email_config()
    
    if not config:
        return False, "No email configuration found"
    
    try:
        if config.get('use_ssl', False):
            server = imaplib.IMAP4_SSL(config['imap_server'], config['imap_port'])
        else:
            server = imaplib.IMAP4(config['imap_server'], config['imap_port'])
        
        server.login(config['email'], config['password'])
        server.select(folder)
        
        status, data = server.search(None, 'ALL')
        email_ids = data[0].split()
        
        # Get the latest emails up to the limit
        if limit > 0 and len(email_ids) > limit:
            email_ids = email_ids[-limit:]
        
        emails = []
        for e_id in email_ids:
            status, data = server.fetch(e_id, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            
            # Extract email content
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()
            
            emails.append({
                'id': e_id.decode(),
                'from': msg['From'],
                'to': msg['To'],
                'subject': msg['Subject'],
                'date': msg['Date'],
                'body': body
            })
        
        server.logout()
        return True, emails
    except Exception as e:
        logger.error(f"Error reading emails: {str(e)}")
        return False, f"Error reading emails: {str(e)}"

def setup_email_system():
    """Set up the email system, installing dependencies if needed"""
    # Check Python dependencies
    if not check_email_dependencies():
        success = install_email_dependencies()
        if not success:
            return False, "Failed to install email dependencies"
    
    # Check if we have email configuration
    config = get_email_config()
    if not config:
        # Check if Docker email server is running
        if not check_email_docker():
            # Set up Docker email server
            success = setup_email_docker()
            if not success:
                return False, "Failed to set up email server"
        
        # Get configuration again after setup
        config = get_email_config()
    
    # Test email connection
    success, message = test_email_connection(config)
    if not success:
        return False, message
    
    return True, "Email system is ready"

def configure_email(smtp_server, smtp_port, imap_server, imap_port, 
                   email, password, use_ssl=False):
    """Configure email settings"""
    config = {
        "smtp_server": smtp_server,
        "smtp_port": int(smtp_port),
        "imap_server": imap_server,
        "imap_port": int(imap_port),
        "email": email,
        "password": password,
        "use_ssl": bool(use_ssl)
    }
    
    if save_email_config(config):
        return test_email_connection(config)
    
    return False, "Failed to save email configuration"

# MCP (Model Context Protocol) integration
def setup_mcp_integration():
    """Set up MCP integration for email functionality"""
    try:
        # Check if MCP package is installed
        try:
            import mcp
            mcp_available = True
        except ImportError:
            logger.warning("MCP SDK not available. Installing dummy package for compatibility.")
            mcp_available = False
        
        # Create MCP configuration
        mcp_config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mcp')
        os.makedirs(mcp_config_dir, exist_ok=True)
        
        mcp_config_file = os.path.join(mcp_config_dir, 'config.json')
        with open(mcp_config_file, 'w') as f:
            json.dump({
                "tools": [
                    {
                        "name": "email_tool",
                        "description": "Tool for sending and reading emails",
                        "functions": [
                            {
                                "name": "send_email",
                                "description": "Send an email to a recipient",
                                "parameters": {
                                    "to": "Email address of the recipient",
                                    "subject": "Subject of the email",
                                    "body": "Content of the email"
                                }
                            },
                            {
                                "name": "read_emails",
                                "description": "Read emails from inbox",
                                "parameters": {
                                    "folder": "Email folder to read from (default: INBOX)",
                                    "limit": "Maximum number of emails to read (default: 10)"
                                }
                            }
                        ]
                    }
                ]
            }, f, indent=2)
        
        if mcp_available:
            return True, "MCP integration set up successfully"
        else:
            return True, "MCP configuration created, but MCP SDK not available. Using fallback mode."
    except Exception as e:
        logger.error(f"Error setting up MCP integration: {str(e)}")
        return False, f"Error setting up MCP integration: {str(e)}"
