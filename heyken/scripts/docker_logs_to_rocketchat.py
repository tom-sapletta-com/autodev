#!/usr/bin/env python3
"""
Script to forward Docker logs to RocketChat.
This script monitors Docker logs from specified containers and forwards them to a RocketChat channel.
"""
import os
import sys
import time
import json
import logging
import subprocess
import requests
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('docker_logs_forwarder.log')
    ]
)
logger = logging.getLogger(__name__)

class RocketChatClient:
    """Simple RocketChat client to send messages to multiple channels."""
    
    def __init__(self, server_url, username, password, channel_names=["heyken-logs", "logs"]):
        """
        Initialize the RocketChat client.
        
        Args:
            server_url: URL of the RocketChat server
            username: Username for authentication
            password: Password for authentication
            channel_names: List of channel names or single channel name to send logs to
        """
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        
        # Convert single channel name to list if needed
        if isinstance(channel_names, str):
            self.channel_names = [channel_names]
        else:
            self.channel_names = channel_names
            
        self.auth_token = None
        self.user_id = None
        self.channel_ids = {}  # Dictionary mapping channel names to IDs
        self.headers = {}
        
    def login(self):
        """
        Login to RocketChat.
        
        Returns:
            bool: True if login was successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/v1/login",
                json={"user": self.username, "password": self.password}
            )
            
            if response.status_code == 200 and response.json().get("status") == "success":
                data = response.json().get("data", {})
                self.auth_token = data.get("authToken")
                self.user_id = data.get("userId")
                self.headers = {
                    "X-Auth-Token": self.auth_token,
                    "X-User-Id": self.user_id,
                    "Content-Type": "application/json"
                }
                logger.info(f"Logged in to RocketChat as {self.username}")
                return True
            else:
                logger.error(f"Login error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Exception during login: {str(e)}")
            return False
            
    def find_channel_id(self):
        """
        Find the IDs of the channels to send logs to.
        
        Returns:
            bool: True if at least one channel was found or created, False otherwise
        """
        if not self.auth_token or not self.user_id:
            logger.error("Not logged in to RocketChat")
            return False
            
        try:
            # Try to find the channels
            response = requests.get(
                f"{self.server_url}/api/v1/channels.list",
                headers=self.headers
            )
            
            if response.status_code != 200 or not response.json().get("success"):
                logger.error(f"Failed to get channels: {response.text}")
                return False
                
            channels = response.json().get("channels", [])
            
            # Process each channel in our list
            for channel_name in self.channel_names:
                channel_found = False
                
                # Look for the channel in the list
                for channel in channels:
                    if channel.get("name") == channel_name:
                        self.channel_ids[channel_name] = channel.get("_id")
                        channel_found = True
                        logger.info(f"Found channel {channel_name} with ID {self.channel_ids[channel_name]}")
                        break
                        
                # If channel not found, try to create it
                if not channel_found:
                    logger.info(f"Channel {channel_name} not found, creating it...")
                    response = requests.post(
                        f"{self.server_url}/api/v1/channels.create",
                        headers=self.headers,
                        json={"name": channel_name}
                    )
                    
                    if response.status_code == 200 and response.json().get("success"):
                        self.channel_ids[channel_name] = response.json().get("channel", {}).get("_id")
                        logger.info(f"Created channel {channel_name} with ID {self.channel_ids[channel_name]}")
                    else:
                        logger.error(f"Failed to create channel {channel_name}: {response.text}")
            
            # Return True if at least one channel was found or created
            return len(self.channel_ids) > 0
                
        except Exception as e:
            logger.error(f"Exception finding channels: {str(e)}")
            return False
            
    def send_message(self, text):
        """
        Send a message to all configured channels.
        
        Args:
            text: The message text to send
            
        Returns:
            bool: True if the message was sent successfully to at least one channel, False otherwise
        """
        if not self.auth_token or not self.user_id or not self.channel_ids:
            logger.error("Not properly initialized to send messages")
            return False
            
        success = False
        
        # Send to all configured channels
        for channel_name, channel_id in self.channel_ids.items():
            try:
                response = requests.post(
                    f"{self.server_url}/api/v1/chat.postMessage",
                    headers=self.headers,
                    json={"roomId": channel_id, "text": text}
                )
                
                if response.status_code == 200 and response.json().get("success"):
                    logger.debug(f"Message sent to channel {channel_name}")
                    success = True
                else:
                    logger.error(f"Failed to send message to channel {channel_name}: {response.text}")
                    # If token expired, try to re-login
                    if "token expired" in response.text.lower() or "not authorized" in response.text.lower():
                        logger.info("Token expired, trying to re-login")
                        if self.login() and self.find_channel_id():
                            # Try again with new token for this channel
                            if channel_name in self.channel_ids:
                                try:
                                    response = requests.post(
                                        f"{self.server_url}/api/v1/chat.postMessage",
                                        headers=self.headers,
                                        json={"roomId": self.channel_ids[channel_name], "text": text}
                                    )
                                    if response.status_code == 200 and response.json().get("success"):
                                        logger.debug(f"Message sent to channel {channel_name} after re-login")
                                        success = True
                                except Exception as e:
                                    logger.error(f"Exception sending message to {channel_name} after re-login: {str(e)}")
            except Exception as e:
                logger.error(f"Exception sending message to channel {channel_name}: {str(e)}")
                
        return success
            
class DockerLogForwarder:
    """Forwards Docker logs to RocketChat."""
    
    def __init__(self, rocketchat_client, containers=None):
        """
        Initialize the Docker log forwarder.
        
        Args:
            rocketchat_client: RocketChatClient instance to send logs with
            containers: List of container names to monitor, or None for all
        """
        self.rocketchat = rocketchat_client
        self.containers = containers or []
        self.running = False
        
    def start(self):
        """Start forwarding logs."""
        if not self.rocketchat.login() or not self.rocketchat.find_channel_id():
            logger.error("Failed to initialize RocketChat client")
            return False
            
        self.running = True
        
        # Send startup message
        self.rocketchat.send_message("🚀 **Docker Log Forwarder Started**")
        
        # Get list of containers if none specified
        if not self.containers:
            try:
                result = subprocess.run(
                    ["docker", "ps", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.containers = result.stdout.strip().split("\n")
                logger.info(f"Found containers: {', '.join(self.containers)}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to list containers: {e}")
                self.rocketchat.send_message(f"❌ **Error**: Failed to list Docker containers: {e}")
                return False
                
        # Start monitoring logs for each container
        for container in self.containers:
            self._monitor_container_logs(container)
            
        return True
        
    def _monitor_container_logs(self, container):
        """
        Monitor logs from a specific container.
        
        Args:
            container: Name of the container to monitor
        """
        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "inspect", container],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning(f"Container {container} not found, skipping")
                self.rocketchat.send_message(f"⚠️ **Warning**: Container `{container}` not found, skipping")
                return
                
            # Send initial message
            self.rocketchat.send_message(f"📋 **Starting log monitoring for container**: `{container}`")
            
            # Start monitoring logs
            process = subprocess.Popen(
                ["docker", "logs", "--follow", "--since", "1m", "--timestamps", container],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Read and forward logs
            for line in iter(process.stdout.readline, ""):
                if not self.running:
                    process.terminate()
                    break
                    
                # Format the log line
                formatted_line = f"🐳 **Docker [{container}]**: {line.strip()}"
                
                # Truncate if too long
                if len(formatted_line) > 2000:
                    formatted_line = formatted_line[:1997] + "..."
                    
                # Send to RocketChat
                self.rocketchat.send_message(formatted_line)
                
        except Exception as e:
            logger.error(f"Error monitoring logs for {container}: {str(e)}")
            self.rocketchat.send_message(f"❌ **Error monitoring logs for `{container}`**: {str(e)}")
            
    def stop(self):
        """Stop forwarding logs."""
        self.running = False
        self.rocketchat.send_message("🛑 **Docker Log Forwarder Stopped**")
        

def main():
    """Main function."""
    try:
        # Load environment variables
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if os.path.exists(env_path):
            logger.info(f"Loading environment variables from {env_path}")
            load_dotenv(env_path)
        else:
            logger.warning("No .env file found, using default values")
            
        # Get RocketChat configuration
        rocketchat_url = os.getenv("ROCKETCHAT_URL", "http://localhost:3100")
        rocketchat_username = os.getenv("ROCKETCHAT_BOT_USERNAME", "heyken_bot")
        rocketchat_password = os.getenv("ROCKETCHAT_BOT_PASSWORD", "heyken123")
        
        # Get containers to monitor
        containers = ["rocketchat", "ollama"]
        
        # Create RocketChat client with multiple channels
        rocketchat_client = RocketChatClient(
            server_url=rocketchat_url,
            username=rocketchat_username,
            password=rocketchat_password,
            channel_names=["heyken-logs", "logs"]
        )
        
        # Create and start log forwarder
        forwarder = DockerLogForwarder(rocketchat_client, containers)
        
        logger.info(f"Starting Docker log forwarder for containers: {', '.join(containers)}")
        if forwarder.start():
            logger.info("Docker log forwarder started successfully")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Stopping Docker log forwarder")
                forwarder.stop()
        else:
            logger.error("Failed to start Docker log forwarder")
            
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        sys.exit(1)
        

if __name__ == "__main__":
    main()
