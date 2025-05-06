#!/bin/bash
# Tworzenie wymaganych katalogów i plików szkieletowych dla projektu
set -e

# Katalogi główne
mkdir -p registry
mkdir -p scripts
mkdir -p data/logs data/backups data/system_db
mkdir -p tests/unit tests/integration tests/performance
mkdir -p middleware-api
mkdir -p recovery-system

# Pliki szkieletowe
# Registry
[ -f registry/component_registry.json ] || echo '{\n  "components": []\n}' > registry/component_registry.json

# Middleware-API
for f in app.py autonomous_layer.py docker_manager.py ollama_client.py rocketchat_client.py logger.py; do
  [ -f "middleware-api/$f" ] || echo -e "# $f\n# Szkielet pliku dla $f" > "middleware-api/$f"
done

# Recovery-system
[ -f recovery-system/recovery.py ] || echo -e "# recovery.py\n# Szkielet pliku dla systemu przywracania" > recovery-system/recovery.py

# .gitkeep w katalogach na dane i testy
for d in data/logs data/backups data/system_db tests/unit tests/integration tests/performance; do
  [ -f "$d/.gitkeep" ] || touch "$d/.gitkeep"
done

echo 'Szkielet projektu utworzony.'
