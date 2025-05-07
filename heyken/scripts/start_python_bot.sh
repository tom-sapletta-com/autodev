#!/bin/bash

# Skrypt uruchamiający bota Heyken w Pythonie

# Ustalenie ścieżek
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
BOT_DIR="$PARENT_DIR/heyken_bot"
ENV_FILE="$PARENT_DIR/.env"

# Sprawdzenie, czy plik .env istnieje
if [ ! -f "$ENV_FILE" ]; then
    echo "Błąd: Plik .env nie istnieje w katalogu $PARENT_DIR"
    exit 1
fi

# Sprawdzenie, czy katalog bota istnieje
if [ ! -d "$BOT_DIR" ]; then
    echo "Błąd: Katalog bota $BOT_DIR nie istnieje"
    exit 1
fi

# Przejście do katalogu bota
cd "$BOT_DIR" || exit 1

# Sprawdzenie, czy Python jest zainstalowany
if ! command -v python3 &> /dev/null; then
    echo "Błąd: Python 3 nie jest zainstalowany"
    exit 1
fi

# Sprawdzenie, czy pip jest zainstalowany
if ! command -v pip3 &> /dev/null; then
    echo "Błąd: pip3 nie jest zainstalowany"
    exit 1
fi

# Sprawdzenie, czy virtualenv jest zainstalowany
if ! command -v virtualenv &> /dev/null; then
    echo "Instalowanie virtualenv..."
    pip3 install virtualenv
fi

# Utworzenie i aktywacja środowiska wirtualnego, jeśli nie istnieje
if [ ! -d "venv" ]; then
    echo "Tworzenie środowiska wirtualnego..."
    virtualenv venv
fi

# Aktywacja środowiska wirtualnego
echo "Aktywacja środowiska wirtualnego..."
source venv/bin/activate

# Instalacja zależności
echo "Instalacja zależności..."
pip install -e .

# Sprawdzenie, czy Ollama jest dostępne
OLLAMA_URL=$(grep -E "^OLLAMA_URL=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
if [ -z "$OLLAMA_URL" ]; then
    OLLAMA_URL="http://localhost:11434"
fi

OLLAMA_MODEL=$(grep -E "^OLLAMA_MODEL=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
if [ -z "$OLLAMA_MODEL" ]; then
    OLLAMA_MODEL="llama3"
fi

echo "Sprawdzanie połączenia z Ollama ($OLLAMA_URL)..."
OLLAMA_RESPONSE=$(curl -s "$OLLAMA_URL/api/tags" 2>&1)
if [ $? -ne 0 ]; then
    echo "BŁĄD: Nie można połączyć się z Ollama pod adresem $OLLAMA_URL"
    echo "Odpowiedź: $OLLAMA_RESPONSE"
    echo "Upewnij się, że Ollama jest uruchomione przed kontynuowaniem"
    echo "Możesz uruchomić Ollama za pomocą Docker:"
    echo "  docker run -d --name ollama -p 11434:11434 ollama/ollama"
    echo "  docker exec -it ollama ollama pull $OLLAMA_MODEL"
    echo "Bot zostanie uruchomiony, ale odpowiedzi będą generowane bez użycia Ollama."
    echo "Naciśnij Enter, aby kontynuować lub Ctrl+C, aby anulować..."
    read
else
    echo "Połączenie z Ollama nawiązane."
    echo "Sprawdzanie dostępności modelu $OLLAMA_MODEL..."
    
    # Sprawdź, czy model jest dostępny (sprawdza zarówno dokładną nazwę jak i nazwę z tagiem :latest)
    if echo "$OLLAMA_RESPONSE" | grep -q "\"name\":\"$OLLAMA_MODEL\"\|\"name\":\"$OLLAMA_MODEL:latest\""; then
        echo "Model $OLLAMA_MODEL lub $OLLAMA_MODEL:latest jest dostępny."
        # Ustaw zmienną środowiskową OLLAMA_MODEL_AVAILABLE na true
        export OLLAMA_MODEL_AVAILABLE=true
    else
        echo "OSTRZEŻENIE: Model $OLLAMA_MODEL ani $OLLAMA_MODEL:latest nie jest dostępny w Ollama."
        echo "Dostępne modele:"
        echo "$OLLAMA_RESPONSE" | grep -o '"name":"[^"]*"' | cut -d '"' -f4
        echo "Możesz pobrać model za pomocą:"
        echo "  docker exec -it ollama ollama pull $OLLAMA_MODEL"
        echo "Bot zostanie uruchomiony, ale odpowiedzi mogą nie działać poprawnie."
        echo "Naciśnij Enter, aby kontynuować lub Ctrl+C, aby anulować..."
        read
        # Ustaw zmienną środowiskową OLLAMA_MODEL_AVAILABLE na false
        export OLLAMA_MODEL_AVAILABLE=false
    fi
fi

# Sprawdzenie, czy RocketChat jest dostępny
ROCKETCHAT_URL=$(grep -E "^ROCKETCHAT_URL=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
if [ -z "$ROCKETCHAT_URL" ]; then
    ROCKETCHAT_URL="http://localhost:3100"
fi

ROCKETCHAT_BOT_USERNAME=$(grep -E "^ROCKETCHAT_BOT_USERNAME=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
ROCKETCHAT_BOT_PASSWORD=$(grep -E "^ROCKETCHAT_BOT_PASSWORD=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')

if [ -z "$ROCKETCHAT_BOT_USERNAME" ]; then
    ROCKETCHAT_BOT_USERNAME="heyken_bot"
fi

if [ -z "$ROCKETCHAT_BOT_PASSWORD" ]; then
    ROCKETCHAT_BOT_PASSWORD="heyken123"
fi

echo "Sprawdzanie połączenia z RocketChat ($ROCKETCHAT_URL)..."
ROCKETCHAT_INFO=$(curl -s "$ROCKETCHAT_URL/api/info")
if [ $? -ne 0 ] || [ -z "$ROCKETCHAT_INFO" ]; then
    echo "BŁĄD: Nie można połączyć się z RocketChat pod adresem $ROCKETCHAT_URL"
    echo "Upewnij się, że RocketChat jest uruchomiony przed kontynuowaniem"
    echo "Naciśnij Enter, aby kontynuować mimo to lub Ctrl+C, aby anulować..."
    read
else
    echo "Połączenie z RocketChat nawiązane."
    echo "Sprawdzanie konta bota ($ROCKETCHAT_BOT_USERNAME)..."
    
    # Próba logowania jako bot
    BOT_LOGIN_RESPONSE=$(curl -s -X POST "$ROCKETCHAT_URL/api/v1/login" \
        -H "Content-Type: application/json" \
        -d '{"user":"'"$ROCKETCHAT_BOT_USERNAME"'","password":"'"$ROCKETCHAT_BOT_PASSWORD"'"}' 2>&1)
    
    if echo "$BOT_LOGIN_RESPONSE" | grep -q "success\":true"; then
        echo "Logowanie jako bot powiodło się. Konto bota jest poprawnie skonfigurowane."
    else
        echo "BŁĄD: Nie można zalogować się jako bot ($ROCKETCHAT_BOT_USERNAME)."
        echo "Odpowiedź: $BOT_LOGIN_RESPONSE"
        echo "Konto bota może nie istnieć lub hasło może być nieprawidłowe."
        echo "Czy chcesz uruchomić skrypt konfiguracyjny RocketChat, aby utworzyć konto bota? (t/n)"
        read -r setup_rocketchat
        
        if [[ "$setup_rocketchat" =~ ^[Tt]$ ]]; then
            echo "Uruchamianie skryptu konfiguracyjnego RocketChat..."
            "$SCRIPT_DIR/setup_rocketchat.sh"
            
            # Ponowna próba logowania
            echo "Ponowna próba logowania jako bot..."
            BOT_LOGIN_RESPONSE=$(curl -s -X POST "$ROCKETCHAT_URL/api/v1/login" \
                -H "Content-Type: application/json" \
                -d '{"user":"'"$ROCKETCHAT_BOT_USERNAME"'","password":"'"$ROCKETCHAT_BOT_PASSWORD"'"}' 2>&1)
            
            if echo "$BOT_LOGIN_RESPONSE" | grep -q "success\":true"; then
                echo "Logowanie jako bot powiodło się po konfiguracji. Konto bota jest poprawnie skonfigurowane."
            else
                echo "BŁĄD: Nadal nie można zalogować się jako bot po konfiguracji."
                echo "Odpowiedź: $BOT_LOGIN_RESPONSE"
                echo "Bot zostanie uruchomiony, ale może nie działać poprawnie."
                echo "Naciśnij Enter, aby kontynuować mimo to lub Ctrl+C, aby anulować..."
                read
            fi
        else
            echo "Bot zostanie uruchomiony, ale może nie działać poprawnie bez konta bota."
            echo "Naciśnij Enter, aby kontynuować mimo to lub Ctrl+C, aby anulować..."
            read
        fi
    fi
fi

# Uruchomienie bota
echo "Uruchamianie bota Heyken..."
python -m src.main --env "$ENV_FILE"
