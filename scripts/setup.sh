#!/bin/bash
# Tworzenie wymaganych katalogów i plików szkieletowych dla projektu
set -e

mkdir -p registry
mkdir -p scripts
mkdir -p data/logs data/backups data/system_db
mkdir -p tests/unit tests/integration tests/performance

touch registry/component_registry.json

for d in data/logs data/backups data/system_db tests/unit tests/integration tests/performance; do
  touch "$d/.gitkeep"
done

echo 'Szkielet projektu utworzony.'
