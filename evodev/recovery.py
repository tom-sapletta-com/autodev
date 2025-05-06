"""
Recovery system module for EvoDev - handles system monitoring and recovery
"""
import os
import json
import datetime
import threading
import logging
import requests

# Try to import docker, but handle the case where it's not installed
try:
    import docker
except ImportError:
    docker = None

class RecoverySystem:
    """System for monitoring and recovering EvoDev services"""
    
    def __init__(self):
        """Initialize the recovery system with default settings"""
        # Configuration from environment variables
        self.gitlab_url = os.environ.get("GITLAB_URL", "http://localhost:8080")
        self.gitlab_token = os.environ.get("GITLAB_API_TOKEN", "default-token")
        self.backup_dir = os.environ.get("BACKUP_DIR", "/var/backups/evodev")
        self.backup_interval = int(os.environ.get("BACKUP_INTERVAL", 3600))
        
        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)

        # Initialize Docker client if docker module is available
        if docker is not None:
            self.docker_client = docker.from_env()
        else:
            self.docker_client = None
            self.logger.warning("Docker module not available, some functionality will be limited")
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # Logger setup
        self.logger = logging.getLogger("evodev.recovery")
        self.logger.info("Recovery system initialized")
    
    def _monitoring_loop(self):
        """Main monitoring loop that runs in a separate thread"""
        while True:
            try:
                # Check services status
                services_status = self._check_services_status()
                
                # Archive current system state
                self._archive_system_state(services_status)
                
                # Verify system integrity
                if not self._verify_system_integrity(services_status):
                    self._initiate_recovery(services_status)
                
                # Sleep for the configured interval
                threading.Event().wait(self.backup_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                threading.Event().wait(60)  # Wait a minute before retrying

    def _check_services_status(self):
        """Check the status of all Docker services"""
        services_status = {}

        # Return empty dict if docker client is not available
        if self.docker_client is None:
            self.logger.warning("Cannot check services: Docker client not available")
            return services_status

        for container in self.docker_client.containers.list(all=True):
            # Rest of the method remains the same
            health = "unknown"
            if "Health" in container.attrs.get("State", {}):
                health = container.attrs["State"]["Health"]["Status"]
                
            services_status[container.name] = {
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "health": health
            }
            
        return services_status
    
    def _archive_system_state(self, services_status):
        """Archive the current system state to a JSON file"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"system_state_{timestamp}.json")
        
        state_data = {
            "timestamp": timestamp,
            "services": services_status
        }
        
        with open(backup_file, "w") as f:
            f.write(json.dumps(state_data, indent=2))
            
        self.logger.info(f"System state archived to {backup_file}")
    
    def _verify_system_integrity(self, services_status):
        """Verify that all critical services are running properly"""
        # List of critical services
        critical_services = ["gitlab", "ollama", "autonomous-system", "recovery-system"]
        
        # Check if all critical services exist and are running
        for service in critical_services:
            if service not in services_status:
                self.logger.error(f"Critical service {service} is missing")
                return False
            
            if services_status[service]["status"] != "running":
                self.logger.error(f"Critical service {service} is not running")
                return False
        
        # Check GitLab API connectivity
        try:
            response = requests.get(
                f"{self.gitlab_url}/api/v4/projects",
                headers={"Private-Token": self.gitlab_token},
                timeout=5
            )
            
            if response.status_code != 200:
                self.logger.error(f"GitLab API returned status code {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to GitLab API: {str(e)}")
            return False
            
        return True

    def _initiate_recovery(self, services_status):
        """Initiate recovery procedures for failed services"""
        self.logger.warning("Initiating system recovery")

        # Skip if docker client is not available
        if self.docker_client is None:
            self.logger.warning("Cannot perform recovery: Docker client not available")
            return

        # Restart failed services
        for service_name, service_info in services_status.items():
            # Rest of the method remains the same
            if service_info["status"] != "running":
                self.logger.info(f"Attempting to restart {service_name}")
                try:
                    container = self.docker_client.containers.get(service_name)
                    container.restart()
                    self.logger.info(f"Service {service_name} restarted successfully")
                except Exception as e:
                    self.logger.error(f"Failed to restart {service_name}: {str(e)}")
        
        # Additional recovery steps could be implemented here
        
    def __str__(self):
        """String representation of the RecoverySystem"""
        return "RecoverySystem instance"
