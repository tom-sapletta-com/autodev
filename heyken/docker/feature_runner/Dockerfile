FROM python:3.9-slim

WORKDIR /app

# Kopiowanie kodu aplikacji
COPY FeatureRunner.py /app/

# Instalacja zależności Pythona
RUN pip install --no-cache-dir \
    flask \
    requests \
    docker \
    psycopg2-binary \
    pyyaml

# Tworzenie katalogu na dane
RUN mkdir -p /data

# Ekspozycja portów
EXPOSE 5000

# Uruchomienie aplikacji
CMD ["python", "FeatureRunner.py"]
