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
        logging.FileHandler("/logs/system_monitor.log"),\n\
        logging.StreamHandler()\n\
    ]\n\
)\n\
logger = logging.getLogger("system_monitor")\n\
\n\
# Inicjalizacja klienta Docker\n\
docker_client = docker.from_env()\n\
\n\
# Metryki Prometheus\n\
SERVICE_STATUS = Gauge("service_status", "Status usługi (1=up, 0=down)", ["service_name", "core_id"])\n\
SYSTEM_HEALTH = Gauge("system_health", "Ogólny stan systemu (0-100)")\n\
CORE_SWITCHES = Counter("core_switches_total", "Całkowita liczba przełączeń rdzeni")\n\
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
# Stan systemu\n\
system_status = {\n\
    "core1_status": "unknown",\n\
    "core2_status": "unknown",\n\
    "active_core_id": 1,\n\
    "system_health": 100,\n\
    "services": {},\n\
    "last_update": 0\n\
}\n\
\n\
def check_services():\n\
    """Sprawdzanie stanu usług systemowych"""\n\
    try:\n\
        containers = docker_client.containers.list()\n\
        \n\
        # Reset statusów usług\n\
        for service_name in system_status["services"]:\n\
            for core_id in [1, 2]:\n\
                SERVICE_STATUS.labels(service_name=service_name, core_id=core_id).set(0)\n\
        \n\
        system_status["services"] = {}\n\
        \n\
        for container in containers:\n\
            service_name = container.name\n\
            core_id = 1 if "core1" in service_name else 2 if "core2" in service_name else 0\n\
            \n\
            system_status["services"][service_name] = {\n\
                "status": "running" if container.status == "running" else "down",\n\
                "core_id": core_id,\n\
                "container_id": container.id\n\
            }\n\
            \n\
            # Aktualizacja metryk Prometheus\n\
            if core_id > 0:\n\
                SERVICE_STATUS.labels(\n\
                    service_name=service_name,\n\
                    core_id=core_id\n\
                ).set(1 if container.status == "running" else 0)\n\
        \n\
        # Sprawdzenie statusu rdzeni\n\
        core1_services = [s for s in system_status["services"].values() if s["core_id"] == 1]\n\
        core2_services = [s for s in system_status["services"].values() if s["core_id"] == 2]\n\
        \n\
        core1_running = all(s["status"] == "running" for s in core1_services) if core1_services else False\n\
        core2_running = all(s["status"] == "running" for s in core2_services) if core2_services else False\n\
        \n\
        system_status["core1_status"] = "healthy" if core1_running else "degraded" if core1_services else "unknown"\n\
        system_status["core2_status"] = "healthy" if core2_running else "degraded" if core2_services else "unknown"\n\
        \n\
        # Odczytanie aktywnego rdzenia z pliku\n\
        try:\n\
            with open("/shared/active_core", "r") as f:\n\
                content = f.read().strip()\n\
                if "Active core: 1" in content:\n\
                    system_status["active_core_id"] = 1\n\
                elif "Active core: 2" in content:\n\
                    system_status["active_core_id"] = 2\n\
        except Exception as e:\n\
            logger.error(f"Błąd odczytu active_core: {str(e)}")\n\
        \n\
        # Obliczenie ogólnego stanu systemu\n\
        active_core_status = system_status["core1_status"] if system_status["active_core_id"] == 1 else system_status["core2_status"]\n\
        if active_core_status == "healthy":\n\
            system_status["system_health"] = 100\n\
        elif active_core_status == "degraded":\n\
            system_status["system_health"] = 50\n\
        else:\n\
            system_status["system_health"] = 0\n\
        \n\
        SYSTEM_HEALTH.set(system_status["system_health"])\n\
        \n\
        system_status["last_update"] = time.time()\n\
        logger.info(f"Stan systemu zaktualizowany: Aktywny rdzeń {system_status[\'active_core_id\']}, zdrowie {system_status[\'system_health\']}%")\n\
        \n\
    except Exception as e:\n\
        logger.error(f"Błąd podczas sprawdzania usług: {str(e)}")\n\
\n\
def monitor_loop():\n\
    """Główna pętla monitorowania"""\n\
    schedule.every(30).seconds.do(check_services)\n\
    \n\
    while True:\n\
        schedule.run_pending()\n\
        time.sleep(1)\n\
\n\
# Inicjalizacja aplikacji Flask\n\
app = Flask(__name__)\n\
\n\
@app.route("/status", methods=["GET"])\n\
def get_status():\n\
    """Endpoint do pobierania statusu systemu"""\n\
    return jsonify(system_status)\n\
\n\
@app.route("/history", methods=["GET"])\n\
def get_history():\n\
    """Endpoint do pobierania historii przełączeń rdzeni"""\n\
    try:\n\
        limit = int(request.args.get("limit", 10))\n\
        \n\
        conn = get_db_connection()\n\
        if not conn:\n\
            return jsonify({"success": False, "error": "Błąd połączenia z bazą danych"}), 500\n\
        \n\
        with conn.cursor() as cur:\n\
            cur.execute(\n\
                "SELECT timestamp, details FROM activity_logs WHERE action = \'switch_core\' ORDER BY timestamp DESC LIMIT %s",\n\
                (limit,)\n\
            )\n\
            \n\
            history = []\n\
            for row in cur.fetchall():\n\
                history.append({\n\
                    "timestamp": str(row[0]),\n\
                    "details": row[1]\n\
                })\n\
        \n\
        conn.close()\n\
        return jsonify({"success": True, "history": history})\n\
    \n\
    except Exception as e:\n\
        logger.error(f"Błąd podczas pobierania historii: {str(e)}")\n\
        return jsonify({"success": False, "error": str(e)}), 500\n\
\n\
if __name__ == "__main__":\n\
    logger.info("Uruchamianie System Monitor...")\n\
    \n\
    # Uruchomienie serwera metryk Prometheus\n\
    start_http_server(9090)\n\
    \n\
    # Pierwsze sprawdzenie stanu\n\
    check_services()\n\
    \n\
    # Uruchomienie wątku monitorowania\n\
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)\n\
    monitor_thread.start()\n\
    \n\
    # Uruchomienie serwera API\n\
    app.run(host="0.0.0.0", port=5000)\n\
' > /app/system_monitor.py

# Tworzenie katalogu na logi
RUN mkdir -p /logs

# Ekspozycja portów
EXPOSE 5000 9090

# Uruchomienie aplikacji
CMD ["python", "system_monitor.py"]
