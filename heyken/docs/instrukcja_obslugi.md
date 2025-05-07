# Instrukcja obsługi bota Heyken

## Spis treści
1. [Wprowadzenie](#wprowadzenie)
2. [Uruchamianie systemu](#uruchamianie-systemu)
3. [Logowanie do RocketChat](#logowanie-do-rocketchat)
4. [Komunikacja z botem](#komunikacja-z-botem)
5. [Dostępne komendy](#dostępne-komendy)
6. [Przykłady interakcji](#przykłady-interakcji)
7. [Rozwiązywanie problemów](#rozwiązywanie-problemów)

## Wprowadzenie

Bot Heyken to inteligentny asystent, który łączy platformę komunikacyjną RocketChat z modelem AI Ollama. Bot jest zaprojektowany do odpowiadania na pytania, wykonywania zadań i wspierania użytkowników w różnych działaniach.

## Uruchamianie systemu

Aby uruchomić system Heyken, wykonaj następujące kroki:

1. Przejdź do katalogu głównego projektu:
   ```bash
   cd /home/tom/github/tom-sapletta-com/evodev/heyken
   ```

2. Uruchom skrypt startowy:
   ```bash
   ./run.sh
   ```

3. Skrypt uruchomi wszystkie niezbędne komponenty:
   - RocketChat (port 3100)
   - MongoDB (baza danych dla RocketChat)
   - Ollama (port 11434)
   - Bot Heyken

4. Poczekaj na pełne uruchomienie systemu. Możesz monitorować postęp w konsoli.

## Logowanie do RocketChat

Po uruchomieniu systemu, możesz zalogować się do RocketChat:

1. Otwórz przeglądarkę i przejdź do adresu: http://localhost:3100

2. Zaloguj się używając danych:
   - Użytkownik: `heyken_user`
   - Hasło: `user123`

3. Bot Heyken jest już zalogowany jako `heyken_bot` i jest gotowy do interakcji.

## Komunikacja z botem

Aby komunikować się z botem Heyken, możesz:

1. **Wysłać wiadomość bezpośrednią**:
   - Kliknij na ikonę "Wiadomość bezpośrednia" (Direct Message)
   - Wyszukaj i wybierz użytkownika `heyken_bot`
   - Wpisz wiadomość i naciśnij Enter

2. **Oznaczyć bota w kanale**:
   - Dołącz do kanału, w którym jest bot
   - Wpisz `@heyken_bot` na początku wiadomości
   - Wpisz swoją wiadomość i naciśnij Enter

## Dostępne komendy

Bot Heyken obsługuje następujące komendy:

| Komenda | Opis |
|---------|------|
| `@heyken_bot pomoc` | Wyświetla listę dostępnych komend |
| `@heyken_bot status` | Sprawdza status bota |
| `@heyken_bot ping` | Sprawdza, czy bot jest aktywny |

Oprócz komend, możesz zadawać botowi dowolne pytania, a on spróbuje na nie odpowiedzieć.

## Przykłady interakcji

### Przykład 1: Zadawanie pytania

**Użytkownik**:
```
@heyken_bot Jak działa Docker?
```

**Bot** (zmienia status na "Pracuję nad: Jak działa Docker?"):
```
**Przetwarzam pytanie:** 
> Jak działa Docker?

Szacowany czas odpowiedzi: około 8 sekund.
```

**Bot** (po przetworzeniu, zmienia status na "online"):
```
Docker działa na zasadzie konteneryzacji, która pozwala na pakowanie aplikacji wraz ze wszystkimi jej zależnościami w izolowane środowiska zwane kontenerami.

Główne elementy działania Dockera:

1. **Obrazy** - niezmienne szablony zawierające system operacyjny, aplikację i zależności
2. **Kontenery** - uruchomione instancje obrazów
3. **Docker Engine** - usługa działająca w tle, która zarządza kontenerami
4. **Docker Hub** - repozytorium obrazów

W przeciwieństwie do maszyn wirtualnych, kontenery współdzielą jądro systemu operacyjnego hosta, co czyni je lżejszymi i bardziej wydajnymi.

Czy chciałbyś dowiedzieć się więcej o konkretnym aspekcie Dockera?
```

### Przykład 2: Używanie komendy status

**Użytkownik**:
```
@heyken_bot status
```

**Bot**:
```
Status bota Heyken:
- Stan: Online
- Czas działania: 2 godziny 15 minut
- Obsłużone wiadomości: 24
- Model AI: llama3
- Wersja: 1.0.0
```

### Przykład 3: Zadawanie złożonego pytania

**Użytkownik**:
```
@heyken_bot Jak mogę zaimplementować system automatycznego backupu bazy danych MongoDB w kontenerze Docker?
```

**Bot** (zmienia status na "Pracuję nad: Jak mogę zaimplementować system automatycznego..."):
```
**Przetwarzam pytanie:** 
> Jak mogę zaimplementować system automatycznego backupu bazy danych MongoDB w kontenerze Docker?

Szacowany czas odpowiedzi: około 15 sekund.
```

**Bot** (po przetworzeniu, zmienia status na "online"):
```
Aby zaimplementować system automatycznego backupu bazy danych MongoDB w kontenerze Docker, możesz zastosować następujące podejście:

1. **Stwórz skrypt backupu**:
   ```bash
   #!/bin/bash
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)
   BACKUP_DIR="/backup"
   
   # Utwórz backup
   mongodump --host mongodb --out $BACKUP_DIR/mongodb_$TIMESTAMP
   
   # Opcjonalnie: kompresuj backup
   tar -zcvf $BACKUP_DIR/mongodb_$TIMESTAMP.tar.gz $BACKUP_DIR/mongodb_$TIMESTAMP
   
   # Opcjonalnie: usuń niekompresowany katalog
   rm -rf $BACKUP_DIR/mongodb_$TIMESTAMP
   
   # Opcjonalnie: usuń stare backupy (starsze niż 7 dni)
   find $BACKUP_DIR -name "mongodb_*.tar.gz" -type f -mtime +7 -delete
   ```

2. **Stwórz obraz Docker dla backupu**:
   ```dockerfile
   FROM mongo:latest
   
   RUN apt-get update && apt-get install -y cron
   
   COPY backup.sh /backup.sh
   RUN chmod +x /backup.sh
   
   # Dodaj zadanie cron
   RUN echo "0 0 * * * /backup.sh >> /var/log/backup.log 2>&1" > /etc/cron.d/mongodb-backup
   RUN chmod 0644 /etc/cron.d/mongodb-backup
   
   # Utwórz plik logów
   RUN touch /var/log/backup.log
   
   CMD cron && tail -f /var/log/backup.log
   ```

3. **Dodaj usługę do docker-compose.yml**:
   ```yaml
   version: '3'
   
   services:
     mongodb:
       image: mongo:latest
       volumes:
         - mongodb_data:/data/db
       networks:
         - app_network
   
     mongodb-backup:
       build: ./backup
       volumes:
         - mongodb_backup:/backup
       networks:
         - app_network
       depends_on:
         - mongodb
   
   volumes:
     mongodb_data:
     mongodb_backup:
   
   networks:
     app_network:
   ```

4. **Uruchom usługi**:
   ```bash
   docker-compose up -d
   ```

Ten system będzie wykonywał backup bazy danych MongoDB codziennie o północy i przechowywał backupy przez 7 dni. Możesz dostosować harmonogram i politykę retencji według własnych potrzeb.

Czy potrzebujesz dodatkowych informacji na ten temat?
```

## Rozwiązywanie problemów

### Problem: Bot nie odpowiada

**Rozwiązanie**:
1. Sprawdź, czy wszystkie usługi są uruchomione:
   ```bash
   docker ps
   ```
2. Sprawdź logi bota:
   ```bash
   cat /home/tom/github/tom-sapletta-com/evodev/heyken/bot.log
   ```
3. Zrestartuj bota:
   ```bash
   cd /home/tom/github/tom-sapletta-com/evodev/heyken
   ./stop.sh
   ./run.sh
   ```

### Problem: Bot odpowiada wolno

**Rozwiązanie**:
1. Sprawdź obciążenie systemu:
   ```bash
   top
   ```
2. Sprawdź, czy Ollama działa poprawnie:
   ```bash
   curl http://localhost:11434/api/health
   ```
3. Zrestartuj Ollama:
   ```bash
   docker restart ollama
   ```

### Problem: Bot odpowiada wielokrotnie na tę samą wiadomość

**Rozwiązanie**:
1. Sprawdź logi bota, aby zidentyfikować problem:
   ```bash
   cat /home/tom/github/tom-sapletta-com/evodev/heyken/bot.log | grep "answered_messages"
   ```
2. Zrestartuj bota:
   ```bash
   cd /home/tom/github/tom-sapletta-com/evodev/heyken
   ./stop.sh
   ./run.sh
   ```

---

Instrukcja została stworzona: 2025-05-07
