FROM python:3.9-slim

WORKDIR /app

# Instalacja zależności Pythona
RUN pip install --no-cache-dir \
    flask \
    requests \
    psycopg2-binary \
    docker \
    prometheus_client \
    schedule

# Kopiowanie pliku aplikacji
COPY system_monitor.py /app/

# Tworzenie katalogu na logi
RUN mkdir -p /logs

# Ekspozycja portów
EXPOSE 5000
EXPOSE 9090

# Uruchomienie aplikacji
CMD ["python", "system_monitor.py"]
