FROM python:3.9-slim

WORKDIR /app

# Instalacja wymaganych pakietów
RUN pip install --no-cache-dir \
    flask \
    requests \
    psycopg2-binary

# Tworzenie pliku głównego aplikacji
RUN echo '#!/usr/bin/env python3\n\
import os\n\
import json\n\
import logging\n\
import psycopg2\n\
from flask import Flask, request, jsonify\n\
\n\
# Konfiguracja logowania\n\
logging.basicConfig(\n\
    level=logging.INFO,\n\
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",\n\
    handlers=[\n\
        logging.FileHandler("/logs/component_registry.log"),\n\
        logging.StreamHandler()\n\
    ]\n\
)\n\
logger = logging.getLogger("component_registry")\n\
\n\
# Połączenie z bazą danych\n\
def get_db_connection():\n\
    try:\n\
        conn = psycopg2.connect(\n\
            host=os.environ.get("DB_HOST", "system_db"),\n\
            database=os.environ.get("DB_NAME", "systemdb"),\n\
            user=os.environ.get("DB_USER", "postgres"),\n\
            password=os.environ.get("DB_PASS", "postgres")\n\
        )\n\
        return conn\n\
    except Exception as e:\n\
        logger.error(f"Błąd połączenia z bazą danych: {str(e)}")\n\
        return None\n\
\n\
# Inicjalizacja aplikacji Flask\n\
app = Flask(__name__)\n\
\n\
@app.route("/components", methods=["GET"])\n\
def get_components():\n\
    """Endpoint do pobierania listy komponentów"""\n\
    try:\n\
        conn = get_db_connection()\n\
        if not conn:\n\
            return jsonify({"success": False, "error": "Błąd połączenia z bazą danych"}), 500\n\
        \n\
        with conn.cursor() as cur:\n\
            cur.execute("SELECT component_name, version, timestamp, status FROM component_versions ORDER BY timestamp DESC")\n\
            components = []\n\
            for row in cur.fetchall():\n\
                components.append({\n\
                    "name": row[0],\n\
                    "version": row[1],\n\
                    "timestamp": str(row[2]),\n\
                    "status": row[3]\n\
                })\n\
        \n\
        conn.close()\n\
        return jsonify({"success": True, "components": components})\n\
    except Exception as e:\n\
        logger.error(f"Błąd podczas pobierania komponentów: {str(e)}")\n\
        return jsonify({"success": False, "error": str(e)}), 500\n\
\n\
@app.route("/register", methods=["POST"])\n\
def register_component():\n\
    """Endpoint do rejestrowania nowego komponentu"""\n\
    try:\n\
        data = request.json\n\
        name = data.get("name")\n\
        version = data.get("version")\n\
        status = data.get("status", "active")\n\
        \n\
        if not name or not version:\n\
            return jsonify({"success": False, "error": "Brak wymaganych pól: name, version"}), 400\n\
        \n\
        conn = get_db_connection()\n\
        if not conn:\n\
            return jsonify({"success": False, "error": "Błąd połączenia z bazą danych"}), 500\n\
        \n\
        with conn.cursor() as cur:\n\
            cur.execute(\n\
                "INSERT INTO component_versions (component_name, version, status) VALUES (%s, %s, %s)",\n\
                (name, version, status)\n\
            )\n\
        \n\
        conn.commit()\n\
        conn.close()\n\
        \n\
        logger.info(f"Zarejestrowano nowy komponent: {name} v{version} ({status})")\n\
        return jsonify({"success": True, "message": f"Komponent {name} v{version} zarejestrowany"})\n\
    \n\
    except Exception as e:\n\
        logger.error(f"Błąd podczas rejestracji komponentu: {str(e)}")\n\
        return jsonify({"success": False, "error": str(e)}), 500\n\
\n\
if __name__ == "__main__":\n\
    logger.info("Uruchamianie Component Registry...")\n\
    app.run(host="0.0.0.0", port=5000)\n\
' > /app/component_registry.py

# Tworzenie katalogu na logi
RUN mkdir -p /logs

# Ekspozycja portów
EXPOSE 5000

# Uruchomienie aplikacji
CMD ["python", "component_registry.py"]
