FROM python:3.9-slim

WORKDIR /app

# Instalacja wymaganych pakietów
RUN pip install --no-cache-dir \
    flask \
    requests

# Kopiowanie pliku aplikacji
COPY middleware_api.py /app/

# Tworzenie katalogu na logi
RUN mkdir -p /logs

# Ekspozycja portów
EXPOSE 5000

# Uruchomienie aplikacji
CMD ["python", "middleware_api.py"]
