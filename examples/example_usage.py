# example_usage.py

"""
Example Usage of Recovery System and Ollama Client.

Copyright 2023 [Your Organization]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import logging
import json
import os
import time
from recovery import RecoverySystem
from ollama_client import OllamaClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_system_health(recovery_system, ollama_client):
    """Check the health of the system and Ollama service"""
    logger.info("Checking system health...")

    # Check system services status
    services_status = recovery_system._check_services_status()
    print("\nServices Status:")
    for service, status in services_status.items():
        print(f"- {service}: {status['status']} (image: {status['image']})")

    # Check system integrity
    integrity_ok = recovery_system._verify_system_integrity(services_status)
    print(f"\nSystem Integrity: {'OK' if integrity_ok else 'ISSUES DETECTED'}")

    # Check Ollama status
    ollama_status = ollama_client.check_status()
    print(f"\nOllama Status: {ollama_status['status']}")
    if ollama_status['status'] == 'available':
        print(f"  Details: {ollama_status['details']}")
    elif 'reason' in ollama_status:
        print(f"  Reason: {ollama_status['reason']}")

    return integrity_ok and ollama_status['status'] == 'available'

def run_ollama_inference(ollama_client, prompt, model="llama2"):
    """Run inference using Ollama"""
    logger.info(f"Running inference with model {model}...")

    print(f"\nSending prompt to {model}: \"{prompt}\"")
    start_time = time.time()

    response = ollama_client.run_inference(prompt, model)

    elapsed_time = time.time() - start_time
    print(f"Response received in {elapsed_time:.2f} seconds:")

    if 'status' in response and response['status'] == 'error':
        print(f"Error: {response['error']}")
        return False

    if 'response' in response:
        print(f"\n{response['response']}")
    else:
        print(json.dumps(response, indent=2))

    return True

def create_system_backup(recovery_system):
    """Create a system backup"""
    logger.info("Creating system backup...")

    print("\nCreating system backup...")
    success = recovery_system.create_backup()

    if success:
        print("Backup created successfully!")
    else:
        print("Failed to create backup!")

    return success

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Example usage of Recovery System and Ollama Client")
    parser.add_argument("--command", choices=["health", "inference", "backup"],
                        default="health", help="Command to execute")
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
                        help="URL for Ollama API")
    parser.add_argument("--prompt", default="Explain how Docker containers work",
                        help="Prompt for LLM inference")
    parser.add_argument("--model", default="llama2",
                        help="Model name for LLM inference")

    args = parser.parse_args()

    # Initialize clients
    logger.info("Initializing clients...")
    recovery_system = RecoverySystem()
    ollama_client = OllamaClient(ollama_url=args.ollama_url)

    if args.command == "health":
        check_system_health(recovery_system, ollama_client)
    elif args.command == "inference":
        run_ollama_inference(ollama_client, args.prompt, args.model)
    elif args.command == "backup":
        create_system_backup(recovery_system)

if __name__ == "__main__":
    main()