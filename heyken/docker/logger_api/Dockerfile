FROM python:3.9-slim

WORKDIR /app

# Instalacja wymaganych pakietów
RUN pip install --no-cache-dir \
    flask \
    requests \
    psycopg2-binary \
    sqlparse

# Kopiowanie pliku aplikacji
COPY logger_api.py /app/

# Tworzenie katalogu na logi
RUN mkdir -p /logs

# Ekspozycja portów
EXPOSE 5000

# Uruchomienie aplikacji
CMD ["python", "logger_api.py"]
