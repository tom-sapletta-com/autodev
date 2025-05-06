# Skrypt PowerShell do uruchamiania systemu autodev na Windows

# Sprawdzenie zależności
if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) { Write-Error 'Terraform nie jest zainstalowany.'; exit 1 }
if (-not (Get-Command ansible -ErrorAction SilentlyContinue)) { Write-Error 'Ansible nie jest zainstalowany.'; exit 1 }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Error 'Docker nie jest zainstalowany.'; exit 1 }
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) { Write-Error 'Docker Compose nie jest zainstalowany.'; exit 1 }

# Inicjalizacja infrastruktury
terraform init
terraform apply -auto-approve

# Deployment przez Ansible (przykład)
# ansible-playbook -i inventory.ini playbook.yml

# Uruchomienie usług docker-compose (jeśli dotyczy)
docker-compose up -d

# Uruchomienie warstwy middleware
pip install -r requirements.txt
Start-Process -NoNewWindow -FilePath python -ArgumentList ' -m uvicorn middleware-api.app:app --host 0.0.0.0 --port 5000'

Write-Output "System autodev uruchomiony."
