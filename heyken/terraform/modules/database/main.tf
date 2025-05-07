# modules/database/main.tf - Konfiguracja warstwy baz danych

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.0"
    }
  }
}

variable "system_network" {
  description = "Nazwa sieci systemowej"
  type        = string
}

variable "system_db" {
  description = "Nazwa wolumenu bazy danych systemu"
  type        = string
}

# Główna baza danych systemu (PostgreSQL)
resource "docker_container" "system_db" {
  name  = "system_db"
  image = "postgres:14"

  networks_advanced {
    name = var.system_network
  }

  ports {
    internal = 5432
    external = 5432
  }

  volumes {
    volume_name    = var.system_db
    container_path = "/var/lib/postgresql/data"
  }

  env = [
    "POSTGRES_PASSWORD=postgres",
    "POSTGRES_USER=postgres",
    "POSTGRES_DB=systemdb"
  ]

  restart = "unless-stopped"
}

# API loggera
resource "docker_container" "logger_api" {
  name  = "logger_api"
  image = "logger_api:latest"

  networks_advanced {
    name = var.system_network
  }

  ports {
    internal = 5000
    external = 5020
  }

  volumes {
    volume_name    = var.system_db
    container_path = "/system_db"
  }

  env = [
    "DATABASE_URL=postgresql://postgres:postgres@system_db:5432/systemdb"
  ]

  restart = "unless-stopped"

  depends_on = [
    docker_container.system_db
  ]
}

# Usługa monitorowania systemu
resource "docker_container" "system_monitor" {
  name  = "system_monitor"
  image = "system_monitor:latest"

  networks_advanced {
    name = var.system_network
  }

  ports {
    internal = 5000
    external = 5021
  }

  volumes {
    volume_name    = var.system_db
    container_path = "/system_db"
  }

  volumes {
    host_path      = "/var/run/docker.sock"
    container_path = "/var/run/docker.sock"
  }

  env = [
    "DATABASE_URL=postgresql://postgres:postgres@system_db:5432/systemdb"
  ]

  restart = "unless-stopped"

  depends_on = [
    docker_container.system_db
  ]
}