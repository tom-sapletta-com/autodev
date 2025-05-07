# modules/core/main.tf - Konfiguracja pojedynczego rdzenia

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.0"
    }
  }
}

variable "core_id" {
  description = "ID rdzenia (1 lub 2)"
  type        = number
}

variable "is_active" {
  description = "Czy rdzeń jest aktywny"
  type        = bool
}

variable "network_id" {
  description = "ID sieci rdzenia"
  type        = string
}

variable "system_network" {
  description = "Nazwa sieci systemowej"
  type        = string
}

variable "shared_data" {
  description = "Nazwa wolumenu ze współdzielonymi danymi"
  type        = string
}

variable "system_db" {
  description = "Nazwa wolumenu bazy danych systemu"
  type        = string
}

variable "logs_volume" {
  description = "Nazwa wolumenu logów"
  type        = string
}

# Wolumeny specyficzne dla rdzenia
resource "docker_volume" "gitlab_config" {
  name = "gitlab_config_core${var.core_id}"
}

resource "docker_volume" "gitlab_data" {
  name = "gitlab_data_core${var.core_id}"
}

resource "docker_volume" "gitlab_logs" {
  name = "gitlab_logs_core${var.core_id}"
}

resource "docker_volume" "ollama_data" {
  name = "ollama_data_core${var.core_id}"
}

resource "docker_volume" "core_manager_data" {
  name = "core_manager_data_core${var.core_id}"
}

# Core Manager - menedżer rdzenia
resource "docker_container" "core_manager" {
  name  = "core_manager_${var.core_id}"
  image = "core_manager:latest"

  # Uruchom tylko jeśli rdzeń jest aktywny
  count = var.is_active ? 1 : 0

  networks_advanced {
    name = var.system_network
  }

  networks_advanced {
    name = var.network_id
  }

  volumes {
    volume_name    = var.shared_data
    container_path = "/shared"
  }

  volumes {
    volume_name    = var.system_db
    container_path = "/system_db"
  }

  volumes {
    volume_name    = var.logs_volume
    container_path = "/logs"
  }

  volumes {
    volume_name    = docker_volume.core_manager_data.name
    container_path = "/data"
  }

  volumes {
    host_path      = "/var/run/docker.sock"
    container_path = "/var/run/docker.sock"
  }

  env = [
    "CORE_ID=${var.core_id}",
    "IS_ACTIVE=${var.is_active}",
    "GITLAB_URL=http://gitlab_core${var.core_id}",
    "OLLAMA_URL=http://ollama_core${var.core_id}:11434"
  ]

  restart = "unless-stopped"
}

# GitLab CE
resource "docker_container" "gitlab" {
  name  = "gitlab_core${var.core_id}"
  image = "gitlab/gitlab-ce:latest"

  # Uruchom tylko jeśli rdzeń jest aktywny
  count = var.is_active ? 1 : 0

  networks_advanced {
    name = var.network_id
  }

  ports {
    internal = 80
    external = var.core_id == 1 ? 8080 : 8081
  }

  ports {
    internal = 22
    external = var.core_id == 1 ? 2221 : 2222
  }

  volumes {
    volume_name    = docker_volume.gitlab_config.name
    container_path = "/etc/gitlab"
  }

  volumes {
    volume_name    = docker_volume.gitlab_data.name
    container_path = "/var/opt/gitlab"
  }

  volumes {
    volume_name    = docker_volume.gitlab_logs.name
    container_path = "/var/log/gitlab"
  }

  env = [
    "GITLAB_OMNIBUS_CONFIG=external_url 'http://gitlab_core${var.core_id}'; gitlab_rails['gitlab_shell_ssh_port'] = ${var.core_id == 1 ? 2221 : 2222};"
  ]

  restart = "unless-stopped"
}

# GitLab Runner
resource "docker_container" "gitlab_runner" {
  name  = "gitlab_runner_core${var.core_id}"
  image = "gitlab/gitlab-runner:latest"

  # Uruchom tylko jeśli rdzeń jest aktywny
  count = var.is_active ? 1 : 0

  networks_advanced {
    name = var.network_id
  }

  volumes {
    host_path      = "/var/run/docker.sock"
    container_path = "/var/run/docker.sock"
  }

  volumes {
    container_path = "/etc/gitlab-runner"
    volume_name    = "gitlab_runner_config_core${var.core_id}"
  }

  restart = "unless-stopped"

  depends_on = [
    docker_container.gitlab
  ]
}

# Ollama - lokalny LLM
resource "docker_container" "ollama" {
  name  = "ollama_core${var.core_id}"
  image = "ollama/ollama:latest"

  # Uruchom tylko jeśli rdzeń jest aktywny
  count = var.is_active ? 1 : 0

  networks_advanced {
    name = var.network_id
  }

  networks_advanced {
    name = var.system_network
  }

  ports {
    internal = 11434
    external = var.core_id == 1 ? 11434 : 11435
  }

  volumes {
    volume_name    = docker_volume.ollama_data.name
    container_path = "/root/.ollama"
  }

  env = [
    "OLLAMA_HOST=0.0.0.0"
  ]

  restart = "unless-stopped"
}

# Middleware API
resource "docker_container" "middleware" {
  name  = "middleware_core${var.core_id}"
  image = "middleware_api:latest"

  # Uruchom tylko jeśli rdzeń jest aktywny
  count = var.is_active ? 1 : 0

  networks_advanced {
    name = var.network_id
  }

  networks_advanced {
    name = var.system_network
  }

  ports {
    internal = 5000
    external = var.core_id == 1 ? 5000 : 5001
  }

  volumes {
    volume_name    = var.logs_volume
    container_path = "/logs"
  }

  volumes {
    volume_name    = var.shared_data
    container_path = "/shared"
  }

  env = [
    "CORE_ID=${var.core_id}",
    "IS_ACTIVE=${var.is_active}",
    "OLLAMA_URL=http://ollama_core${var.core_id}:11434",
    "GITLAB_URL=http://gitlab_core${var.core_id}",
    "DATABASE_URL=postgresql://postgres:postgres@system_db:5432/systemdb"
  ]

  restart = "unless-stopped"

  depends_on = [
    docker_container.ollama
  ]
}

# Component Registry
resource "docker_container" "component_registry" {
  name  = "component_registry_core${var.core_id}"
  image = "component_registry:latest"

  # Uruchom tylko jeśli rdzeń jest aktywny
  count = var.is_active ? 1 : 0

  networks_advanced {
    name = var.network_id
  }

  networks_advanced {
    name = var.system_network
  }

  ports {
    internal = 5000
    external = var.core_id == 1 ? 5002 : 5003
  }

  volumes {
    volume_name    = var.shared_data
    container_path = "/shared"
  }

  volumes {
    volume_name    = var.system_db
    container_path = "/system_db"
  }

  env = [
    "CORE_ID=${var.core_id}",
    "IS_ACTIVE=${var.is_active}",
    "DATABASE_URL=postgresql://postgres:postgres@system_db:5432/systemdb"
  ]

  restart = "unless-stopped"
}

# Output endpoints
output "endpoints" {
  value = {
    gitlab    = "http://localhost:${var.core_id == 1 ? 8080 : 8081}"
    ollama    = "http://localhost:${var.core_id == 1 ? 11434 : 11435}"
    middleware = "http://localhost:${var.core_id == 1 ? 5000 : 5001}"
    registry  = "http://localhost:${var.core_id == 1 ? 5002 : 5003}"
  }
}