# Heyken Bot

Bot integrujący RocketChat z Ollama do automatyzacji realizacji projektów według określonej metodologii.

## Funkcjonalności

- Integracja z RocketChat - odbieranie i wysyłanie wiadomości
- Integracja z Ollama - wykorzystanie modeli językowych do generowania kodu i dokumentacji
- Automatyzacja procesu realizacji projektów:
  1. Tworzenie dokumentacji projektu
  2. Planowanie realizacji w formie zdań logicznych w języku naturalnym
  3. Konwersja planów na kod Python
  4. Testowanie poprawności logicznej kodu
  5. Implementacja w środowisku Docker
  6. Testowanie w sandboxie

## Struktura projektu

```
heyken_bot/
├── src/                      # Kod źródłowy
│   ├── rocketchat/          # Integracja z RocketChat
│   ├── ollama/              # Integracja z Ollama
│   ├── project_manager/     # Zarządzanie projektami
│   ├── documentation/       # Generowanie dokumentacji
│   ├── planning/            # Planowanie projektów
│   ├── testing/             # Testowanie kodu
│   └── deployment/          # Wdrażanie w Dockerze
├── docs/                    # Dokumentacja
├── tests/                   # Testy
├── docker/                  # Pliki Dockera
└── scripts/                 # Skrypty pomocnicze
```

## Instalacja

### Wymagania

- Python 3.8+
- Docker
- RocketChat
- Ollama

### Instalacja z użyciem Docker Compose

```bash
# Klonowanie repozytorium
git clone https://github.com/tom-sapletta-com/evodev.git
cd evodev/heyken/heyken_bot

# Uruchomienie za pomocą Docker Compose
docker-compose up -d
```

### Instalacja manualna

```bash
# Klonowanie repozytorium
git clone https://github.com/tom-sapletta-com/evodev.git
cd evodev/heyken/heyken_bot

# Utworzenie wirtualnego środowiska
python -m venv venv
source venv/bin/activate  # Na Windowsie: venv\Scripts\activate

# Instalacja zależności
pip install -e .
```

## Użycie

### Konfiguracja

Utwórz plik `.env` na podstawie `.env.example`:

```bash
cp .env.example .env
```

Następnie edytuj plik `.env` i dostosuj ustawienia:

```
# RocketChat
ROCKETCHAT_URL=http://localhost:3100
ROCKETCHAT_BOT_USERNAME=heyken_bot
ROCKETCHAT_BOT_PASSWORD=heyken123

# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Inne ustawienia
PROJECT_DIR=/path/to/projects
```

### Uruchomienie bota

```bash
# Z użyciem skryptu
./scripts/start_bot.sh

# Lub bezpośrednio
python -m heyken_bot
```

## Przykłady użycia

### Tworzenie nowego projektu

W RocketChat, napisz do bota:

```
@heyken_bot nowy projekt: Kalkulator w Pythonie
```

Bot przeprowadzi Cię przez proces tworzenia projektu:
1. Wygeneruje dokumentację
2. Stworzy plan implementacji
3. Wygeneruje kod
4. Przetestuje kod
5. Wdroży w Dockerze
6. Udostępni sandbox do testów

## Licencja

MIT
