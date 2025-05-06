# EvoDev

<div align="center">
  <img src="https://raw.githubusercontent.com/tom-sapletta-com/evodev/main/docs/images/evodev-logo.svg" alt="EvoDev Logo" width="200">
  <br>
  <em>Ewolucyjny Asystent dla Programistów</em>
</div>

## Opis

EvoDev to asystent ewolucyjny dla programistów, który automatycznie instaluje, konfiguruje i rozwija środowiska programistyczne. System uczy się nowych umiejętności poprzez automatyczną instalację i konfigurację oprogramowania.

## Instalacja

```bash
pip install evodev
```

## Szybki start

```bash
# Klonowanie repozytorium
git clone https://github.com/tom-sapletta-com/evodev.git
cd evodev

# Instalacja zależności systemowych
sudo bash install.sh

# Uruchomienie systemu
./run.sh

# Uruchomienie monitora z widokiem logów
./run.sh --logs

# Zatrzymanie wszystkich usług
./stop.sh
```

## Kluczowe funkcje

- **Automatyczna konfiguracja środowiska** - System automatycznie instaluje i konfiguruje wszystkie potrzebne komponenty
- **Monitoring Dockera** - Śledzenie requestów między kontenerami i wizualizacja w przeglądarce
- **Integracja z LLM** - Wsparcie dla OpenAI, Anthropic i Ollama
- **Zarządzanie środowiskiem** - Edycja plików konfiguracyjnych i restart usług z poziomu przeglądarki
- **Integracja email** - Funkcjonalność email jako część systemu MCP

## Komponenty

- **Monitor** - System monitorowania zasobów i kontenerów Docker
- **Ollama** - Lokalne modele LLM
- **Middleware API** - Zarządzanie usługami
- **Docker Compose** - Orkiestracja kontenerów

## Dokumentacja

Pełna dokumentacja dostępna na [GitHub](https://github.com/tom-sapletta-com/evodev/blob/main/README.md).

## Licencja

MIT
