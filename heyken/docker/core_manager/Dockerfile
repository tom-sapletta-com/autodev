FROM python:3.9-slim

WORKDIR /app

# Kopiowanie kodu aplikacji
COPY app.py /app/

# Instalacja zależności Pythona
RUN pip install --no-cache-dir \
    flask \
    requests \
    docker \
    psycopg2-binary

# Konfiguracja logowania
RUN mkdir -p /logs

# Ekspozycja portów
EXPOSE 5000

# Uruchomienie aplikacji
CMD ["python", "app.py"]
