# modules/services/main.tf - Konfiguracja usług wspólnych

variable "system_network" {
  description = "Nazwa sieci systemowej"
  type        = string
}

# Konfiguracja dla dostawcy kreuzwerker/docker
terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.0"
    }
  }
}

# Puste wyjście dla endpoints, aby spełnić oczekiwania głównego modułu
output "endpoints" {
  value = {
    "status": "Gotowy do konfiguracji usług"
  }
}
