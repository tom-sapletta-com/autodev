# modules/sandbox/main.tf - Konfiguracja piaskownicy testowej

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.0"
    }
  }
}

variable "network_id" {
  description = "ID sieci piaskownicy"
  type        = string
}

variable "system_network" {
  description = "Nazwa sieci systemowej"
  type        = string
}

variable "active_core_id" {
  description = "ID aktywnego rdzenia"
  type        = number
}

variable "system_db" {
  description = "Nazwa wolumenu bazy danych systemu"
  type        = string
}

# Wolumeny piaskownicy
resource "docker_volume" "sandbox_data" {
  name = "sandbox_data"
}

resource "docker_volume" "sandbox_ollama" {
  name = "sandbox_ollama"
}

# Sandbox Manager - menedżer piaskownicy
resource "docker_container" "sandbox_manager" {
  name  = "sandbox_manager"
  image = "sandbox_manager:latest"

  networks_advanced {
    name = var.network_id
  }

  networks_advanced {
    name = var.system_network
  }

  ports {
    internal = 5000
    external = 5010
  }

  volumes {
    volume_name    = docker_volume.sandbox_data.name
    container_path = "/data"
  }

  volumes {
    host_path      = "/var/run/docker.sock"
    container_path = "/var/run/docker.sock"
  }

  volumes {
    volume_name    = var.system_db
    container_path = "/system_db"
  }

  env = [
    "ACTIVE_CORE_ID=${var.active_core_id}",
    "OLLAMA_CORE_URL=http://ollama_core${var.active_core_id}:11434",
    "MIDDLEWARE_CORE_URL=http://middleware_core${var.active_core_id}:5000",
    "DATABASE_URL=postgresql://postgres:postgres@system_db:5432/systemdb"
  ]

  restart = "unless-stopped"
}

# Test Core - testowa instancja rdzenia
resource "docker_container" "test_core" {
  name  = "test_core"
  image = "core_manager:latest"

  networks_advanced {
    name = var.network_id
  }

  volumes {
    volume_name    = docker_volume.sandbox_data.name
    container_path = "/data"
  }

  volumes {
    host_path      = "/var/run/docker.sock"
    container_path = "/var/run/docker.sock"
  }

  env = [
    "CORE_ID=test",
    "IS_ACTIVE=true",
    "SANDBOX_MODE=true",
    "OLLAMA_URL=http://test_ollama:11434"
  ]

  restart = "unless-stopped"
}

# Test Ollama - testowa instancja Ollama
resource "docker_container" "test_ollama" {
  name  = "test_ollama"
  image = "ollama/ollama:latest"

  networks_advanced {
    name = var.network_id
  }

  volumes {
    volume_name    = docker_volume.sandbox_ollama.name
    container_path = "/root/.ollama"
  }

  env = [
    "OLLAMA_HOST=0.0.0.0"
  ]

  restart = "unless-stopped"
}

# Feature Runner - uruchamianie i testowanie nowych funkcji
resource "docker_container" "feature_runner" {
  name  = "feature_runner"
  image = "feature_runner:latest"

  networks_advanced {
    name = var.network_id
  }

  networks_advanced {
    name = var.system_network
  }

  volumes {
    volume_name    = docker_volume.sandbox_data.name
    container_path = "/data"
  }

  volumes {
    host_path      = "/var/run/docker.sock"
    container_path = "/var/run/docker.sock"
  }

  volumes {
    volume_name    = var.system_db
    container_path = "/system_db"
  }

  env = [
    "ACTIVE_CORE_ID=${var.active_core_id}",
    "TEST_OLLAMA_URL=http://test_ollama:11434",
    "SANDBOX_MANAGER_URL=http://sandbox_manager:5000",
    "DATABASE_URL=postgresql://postgres:postgres@system_db:5432/systemdb"
  ]

  restart = "unless-stopped"
}

# Output endpoints
output "endpoints" {
  value = {
    sandbox_manager = "http://localhost:5010"
    test_ollama     = "http://test_ollama:11434" # Dostępny tylko wewnętrznie
    feature_runner  = "http://feature_runner:5000" # Dostępny tylko wewnętrznie
  }
}