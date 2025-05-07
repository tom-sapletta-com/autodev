# Heyken

## System autonomicznego programowania z redundantnymi rdzeniami

**[heyken.io](https://heyken.io) | [hey-ken.com](https://hey-ken.com)**

Heyken to kompleksowy system autonomicznego programowania zaprojektowany z myślą o niezawodności i samorozwoju. 
System wykorzystuje architekturę dwóch redundantnych rdzeni, które zapewniają ciągłość działania nawet w przypadku awarii jednego z nich.

## Kluczowe funkcjonalności

1. **Redundantne rdzenie** - system działa na dwóch identycznych rdzeniach, z których jeden jest aktywny, a drugi w trybie gotowości
2. **Piaskownica testowa** - izolowane środowisko do bezpiecznego testowania nowych funkcjonalności
3. **Automatyzacja CI/CD** - zintegrowana z GitLab automatyzacja procesu testowania i wdrażania
4. **Samorozwój** - zdolność do samodzielnego tworzenia i testowania nowych funkcjonalności
5. **Dynamiczna infrastruktura** - możliwość dodawania nowych usług Docker według potrzeb
6. **Kompleksowe logowanie** - szczegółowe rejestrowanie wszystkich działań systemu

## Architektura

### Warstwy systemu
- **Rdzeń 1 i Rdzeń 2** - redundantne jednostki zarządzające całym systemem
- **Piaskownica (Sandbox)** - izolowane środowisko do testowania nowych funkcji
- **Baza danych** - centralne repozytorium przechowujące logi i konfiguracje
- **Usługi Docker** - dynamicznie dodawane kontenery z nowymi funkcjonalnościami

### Mechanizmy bezpieczeństwa
- Izolacja warstw poprzez dedykowane sieci Docker
- Testowanie wszystkich nowych funkcji w piaskownicy przed wdrożeniem
- Ograniczone użycie zewnętrznych API tylko do procesu nauki

## Uruchomienie

```bash
# Inicjalizacja systemu
./scripts/init.sh

# Wdrożenie infrastruktury
./scripts/deploy.sh

# Sprawdzanie statusu
./scripts/status.sh

# Przełączanie między rdzeniami
./scripts/switch_core.sh [1|2]
```

## Funkcje dodatkowe

- **text2sql** - interfejs do analizy logów przez zapytania w języku naturalnym
- **FeatureRunner** - mechanizm do testowania i wdrażania nowych funkcjonalności
- **Monitorowanie stanu** - ciągła obserwacja wszystkich komponentów systemu

---

&copy; 2025 Heyken - System autonomicznego programowania z redundantnymi rdzeniami
