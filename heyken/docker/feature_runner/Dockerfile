FROM python:3.9-slim

WORKDIR /app

# Instalacja wymaganych pakietów systemowych
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Instalacja Docker CLI
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Kopiowanie kodu aplikacji
COPY FeatureRunner.py /app/

# Instalacja zależności Pythona
RUN pip install --no-cache-dir \
    flask \
    requests \
    docker \
    psycopg2-binary \
    pyyaml \
    uuid

# Tworzenie katalogu na dane
RUN mkdir -p /data

# Ekspozycja portów
EXPOSE 5000

# Uruchomienie aplikacji
CMD ["python", "FeatureRunner.py"]
