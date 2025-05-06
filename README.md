# EvoDev

EvoDev to asystent ewolucyjny dla programistów. Uczy się nowych umiejętności (skilli) poprzez automatyczną instalację i konfigurację nowego oprogramowania (np. przez Docker Compose).

## Podsumowanie dokumentacji

- [docs/3.md](docs/3.md): Architektura systemu, główne komponenty (Ollama, VS Code Server, CLI/API Manager, GitLab, Rocket.Chat), klasy automatyzacji, przykłady kodu.
- [docs/4.md](docs/4.md): Etapy ewolucji systemu, przykłady użycia na różnych poziomach rozwoju.
- [docs/5.md](docs/5.md): Plan implementacji, przykładowa struktura katalogów, docker-compose, opis warstwy middleware, kod zarządzania usługami Docker, klienty API.
- [docs/6.md](docs/6.md): Architektura systemu rdzeniowego, system przywracania, integracja z GitLab CI/CD, rejestr komponentów, skrypty backupu i recovery.
- [docs/7.md](docs/7.md): Koncepcja dwóch redundantnych rdzeni (Core1, Core2), sandbox do testowania nowości, diagram architektury, rejestrowanie każdej akcji w bazie danych, automatyczne testowanie.
- [docs/8.md](docs/8.md): Implementacja infrastruktury w Terraform, przykładowy main.tf, definicje sieci, wolumenów, aktywnego rdzenia, sandboxa, loggera, modularność.

## Instalacja i konfiguracja projektu

### 1. Klonowanie repozytorium

```bash
git clone <adres_repozytorium>
cd EvoDev
```

### 2. Instalacja zależności systemowych

#### Linux (Fedora/Ubuntu/Arch)

```bash
sudo bash install.sh
```

#### Windows (PowerShell)

```powershell
./install.ps1
```

### 3. Konfiguracja środowiska

1. Skopiuj plik `.env.example` jako `.env`:
   ```bash
   cp .env.example .env
   ```
2. Uzupełnij klucz API do LLM (np. OpenRouter):
   ```env
   LLM_API_KEY_TEST=sk-test-1234
   ```

### 4. Instalacja projektu jako pakiet Pythona (tryb developerski)

```bash
pip install -e .
```

### 5. Uruchomienie testów głosowych

```bash
python3 test_voice_skill.py
```

---

## Automatyczna obsługa głosowa (voice skill)

- System po uruchomieniu pyta o token API do LLM.
- Po podaniu tokena instaluje i testuje obsługę głosu (ASR/TTS).
- Jeśli testy przejdą pomyślnie, voice-chatbot jest gotowy do użycia.

---

## Struktura projektu

```
.
├── docker-compose.yml
├── main.tf
├── modules/
│   ├── core/
│   ├── sandbox/
│   └── services/
├── middleware-api/
├── recovery-system/
├── registry/
│   └── component_registry.json
├── scripts/
│   ├── setup.sh
│   └── deploy.sh
├── data/
│   ├── logs/
│   ├── backups/
│   └── system_db/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── performance/
├── README.md
├── docs/
│   ├── 3.md
│   ├── 4.md
│   ├── 5.md
│   ├── 6.md
│   ├── 7.md
│   └── 8.md
├── pyproject.toml
├── setup.py
├── .env.example
├── test_voice_skill.py
└── scripts/
    └── ollama_autoselect.sh
```

## Kluczowe założenia
- Dwa rdzenie (Core1, Core2) – jeden aktywny, drugi standby, replikowalność i testowanie.
- Sandbox do testowania nowych funkcji i aktualizacji.
- Każda akcja, komenda, request rejestrowana w bazie danych (logi, historia, wersje komponentów, wyniki testów).
- Modularna architektura, łatwa rozbudowa przez Terraform/Ansible/Docker Compose.

## Rozszerzanie systemu o nowe skille

Aby dodać nową funkcjonalność (np. obsługę głosu, OCR, powiadomienia):
1. Wydaj polecenie przez Rocket.Chat (np. "Chcę rozmawiać głosowo").
2. System automatycznie zainstaluje wymagane biblioteki i przeprowadzi test.
3. Po pozytywnym teście funkcja jest gotowa do użycia.

## Przykład interakcji

- System: "Podaj klucz API do LLM (np. OpenRouter)."
- Użytkownik: "sk-xxxx..."
- System: "Instaluję obsługę głosu... Powiedz coś do mikrofonu..."
- System: "Voice-chatbot gotowy do użycia!"

Więcej szczegółów w dokumentacji w katalogu `docs/`.