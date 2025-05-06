# EvoDev Monitor - PyPI Package Documentation

## Przegląd

EvoDev Monitor to zaawansowany system monitorowania dla środowisk programistycznych, który zapewnia:
- Monitorowanie zasobów systemowych (CPU, RAM, dysk)
- Śledzenie kontenerów Docker w czasie rzeczywistym
- Przeglądanie logów aplikacji
- Integrację z interfejsami webowymi kontenerów
- Wsparcie AI poprzez interfejs czatu

## Instalacja

```bash
pip install evodev-monitor
```

## Podstawowe użycie

### Uruchomienie monitora

```bash
# Uruchomienie z domyślnymi ustawieniami
evodev-monitor start

# Uruchomienie z określonym portem
evodev-monitor start --port 8888

# Uruchomienie z widokiem logów
evodev-monitor start --logs
```

### Zatrzymanie monitora

```bash
evodev-monitor stop
```

### Sprawdzenie statusu

```bash
evodev-monitor status
```

## Konfiguracja

### Zmienne środowiskowe

| Zmienna | Opis | Wartość domyślna |
|---------|------|------------------|
| `MONITOR_PORT` | Port na którym działa interfejs web | `8080` |
| `MONITOR_DB` | Ścieżka do pliku bazy danych | `monitor.db` |
| `LOG_LEVEL` | Poziom logowania | `INFO` |
| `MONITOR_LOG_FILE` | Ścieżka do pliku logu monitora | `monitor.log` |
| `APP_LOG_FILE` | Ścieżka do pliku logu aplikacji | `monitor.log` |
| `LLM_TOKEN` | Token API dla modelu językowego | `""` |
| `PARTNER_LINK` | Link partnerski do uzyskania tokenu API | `https://platform.openai.com/account/api-keys` |

### Plik konfiguracyjny

Utwórz plik `.env` w katalogu głównym projektu:

```
MONITOR_PORT=8080
LOG_LEVEL=INFO
MONITOR_LOG_FILE=monitor.log
LLM_TOKEN="twój-token-api"
```

## Główne funkcje

### 1. Monitorowanie zasobów systemowych

- Śledzenie użycia CPU w czasie rzeczywistym
- Monitorowanie zużycia pamięci RAM
- Analiza wykorzystania przestrzeni dyskowej
- Automatyczne powiadomienia o przekroczeniu progów

### 2. Zarządzanie kontenerami Docker

- Wyświetlanie statusu kontenerów w siatce 4x4
- Podgląd logów kontenerów
- Dostęp do interfejsów webowych kontenerów bezpośrednio z panelu
- Filtrowanie kontenerów według statusu

### 3. Przeglądarka logów

- Przeglądanie logów z różnych źródeł
- Filtrowanie według poziomu logowania
- Kolorowe oznaczenie różnych poziomów logów
- Możliwość pobrania plików logów

### 4. Integracja z Chat AI

- Wsparcie użytkownika przez interfejs czatu
- Integracja z modelami językowymi
- Automatyczna ewolucja systemu
- Personalizowane odpowiedzi

## API REST

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/api/status` | GET | Zwraca aktualny status systemu |
| `/api/events` | GET | Pobiera listę zdarzeń systemowych |
| `/api/logs` | GET | Pobiera logi aplikacji |
| `/api/docker` | GET | Zwraca informacje o kontenerach Docker |
| `/api/llm/token/status` | GET | Sprawdza status tokenu API |
| `/api/llm/token/set` | POST | Ustawia token API dla modelu językowego |
| `/api/chat/message` | POST | Wysyła wiadomość do modelu językowego |

## Rozszerzanie systemu

System można rozszerzać poprzez:

1. Tworzenie własnych modułów monitorujących:
   ```python
   from evodev_monitor import register_monitor
   
   @register_monitor
   def custom_monitor():
       # Implementacja monitorowania
       return {"status": "ok", "data": {...}}
   ```

2. Dodawanie własnych widoków:
   ```python
   from evodev_monitor import register_view
   
   @register_view('/custom')
   def custom_view():
       return render_template('custom.html')
   ```

## Rozwiązywanie problemów

### Konflikt portów
```bash
# Sprawdź zajęte porty
evodev-monitor check-ports

# Uruchom na innym porcie
evodev-monitor start --port 8081
```

### Problemy z bazą danych
```bash
# Zresetuj bazę danych
evodev-monitor reset-db
```

### Problemy z Docker API
```bash
# Sprawdź połączenie z Docker
evodev-monitor check-docker
```
