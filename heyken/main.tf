# main.tf - Główna konfiguracja infrastruktury

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.0"
    }
  }
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
}

# Zmienne konfiguracyjne
variable "active_core_id" {
  description = "ID aktywnego rdzenia (1 lub 2)"
  type        = number
  default     = 1

  validation {
    condition     = var.active_core_id == 1 || var.active_core_id == 2
    error_message = "Wartość active_core_id musi być równa 1 lub 2."
  }
}

# Sieci Docker
resource "docker_network" "system_network" {
  name = "system_network"
}

resource "docker_network" "core1_network" {
  name = "core1_network"
}

resource "docker_network" "core2_network" {
  name = "core2_network"
}

resource "docker_network" "sandbox_network" {
  name = "sandbox_network"
}

# Wolumeny współdzielone między rdzeniami
resource "docker_volume" "shared_data" {
  name = "shared_data"
}

resource "docker_volume" "system_db" {
  name = "system_db"
}

resource "docker_volume" "logs" {
  name = "logs"
}

# Import modułów dla poszczególnych komponentów
module "core1" {
  source = "./modules/core"

  core_id        = 1
  is_active      = var.active_core_id == 1
  network_id     = docker_network.core1_network.id
  system_network = docker_network.system_network.name
  shared_data    = docker_volume.shared_data.name
  system_db      = docker_volume.system_db.name
  logs_volume    = docker_volume.logs.name
}

module "core2" {
  source = "./modules/core"

  core_id        = 2
  is_active      = var.active_core_id == 2
  network_id     = docker_network.core2_network.id
  system_network = docker_network.system_network.name
  shared_data    = docker_volume.shared_data.name
  system_db      = docker_volume.system_db.name
  logs_volume    = docker_volume.logs.name
}

module "sandbox" {
  source = "./modules/sandbox"

  network_id     = docker_network.sandbox_network.id
  system_network = docker_network.system_network.name
  active_core_id = var.active_core_id
  system_db      = docker_volume.system_db.name
}

module "services" {
  source = "./modules/services"

  system_network = docker_network.system_network.name
  active_core_id = var.active_core_id
}

module "database" {
  source = "./modules/database"

  system_network = docker_network.system_network.name
  system_db      = docker_volume.system_db.name
}

# Konfigurator aktywnego rdzenia
resource "docker_container" "core_switcher" {
  name  = "core_switcher"
  image = "alpine:latest"

  restart = "no"

  networks_advanced {
    name = docker_network.system_network.name
  }

  networks_advanced {
    name = docker_network.core1_network.name
  }

  networks_advanced {
    name = docker_network.core2_network.name
  }

  volumes {
    volume_name    = docker_volume.shared_data.name
    container_path = "/shared"
  }

  command = [
    "sh", "-c", "echo \"Active core: ${var.active_core_id}\" > /shared/active_core && sleep 5"
  ]
}

# Outputs
output "active_core" {
  value = "Core ${var.active_core_id} is currently active"
}

output "core1_endpoints" {
  value = module.core1.endpoints
}

output "core2_endpoints" {
  value = module.core2.endpoints
}

output "sandbox_endpoints" {
  value = module.sandbox.endpoints
}

output "service_endpoints" {
  value = module.services.endpoints
}