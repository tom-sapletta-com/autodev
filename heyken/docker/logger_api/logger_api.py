#!/usr/bin/env python3
import os
import json
import logging
import psycopg2
import sqlparse
from flask import Flask, request, jsonify

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/logs/logger_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("logger_api")

# Połączenie z bazą danych
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "system_db"),
            database=os.environ.get("DB_NAME", "systemdb"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASS", "postgres")
        )
        return conn
    except Exception as e:
        logger.error(f"Błąd połączenia z bazą danych: {str(e)}")
        return None

# Inicjalizacja aplikacji Flask
app = Flask(__name__)

@app.route("/logs", methods=["GET"])
def get_logs():
    """Endpoint do pobierania logów"""
    try:
        limit = int(request.args.get("limit", 100))
        log_type = request.args.get("type")
        
        query = "SELECT timestamp, core_id, log_type, action, status, details FROM activity_logs"
        params = []
        
        if log_type:
            query += " WHERE log_type = %s"
            params.append(log_type)
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Błąd połączenia z bazą danych"}), 500
        
        with conn.cursor() as cur:
            cur.execute(query, params)
            logs = []
            for row in cur.fetchall():
                logs.append({
                    "timestamp": str(row[0]),
                    "core_id": row[1],
                    "type": row[2],
                    "action": row[3],
                    "status": row[4],
                    "details": row[5]
                })
        
        conn.close()
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        logger.error(f"Błąd podczas pobierania logów: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/text2sql", methods=["POST"])
def text_to_sql():
    """Endpoint do konwersji zapytania tekstowego na SQL i wykonania go"""
    try:
        data = request.json
        query_text = data.get("query")
        
        if not query_text:
            return jsonify({"success": False, "error": "Brak wymaganego pola: query"}), 400
        
        # Tutaj byłaby integracja z modelem LLM dla text2sql
        # Używamy prostego parsera dla celów demonstracyjnych
        
        sql_query = ""
        if "ostatnie logi" in query_text.lower():
            sql_query = "SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10"
        elif "błędy" in query_text.lower():
            sql_query = "SELECT * FROM activity_logs WHERE status = 'error' ORDER BY timestamp DESC LIMIT 10"
        elif "komponent" in query_text.lower():
            for word in query_text.split():
                if word not in ["komponent", "komponenty", "pokaż", "pokaz", "wyświetl"]:
                    sql_query = f"SELECT * FROM component_versions WHERE component_name LIKE '%{word}%' ORDER BY timestamp DESC LIMIT 10"
                    break
        else:
            sql_query = "SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 5"
        
        # Formatowanie SQL dla lepszej czytelności
        formatted_sql = sqlparse.format(sql_query, reindent=True, keyword_case="upper")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False, 
                "error": "Błąd połączenia z bazą danych",
                "sql": formatted_sql
            }), 500
        
        with conn.cursor() as cur:
            cur.execute(sql_query)
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in cur.fetchall():
                result = {}
                for i, column in enumerate(columns):
                    result[column] = str(row[i]) if row[i] is not None else None
                results.append(result)
        
        conn.close()
        
        return jsonify({
            "success": True,
            "query": query_text,
            "sql": formatted_sql,
            "results": results
        })
    
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania zapytania text2sql: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Uruchamianie Logger API...")
    app.run(host="0.0.0.0", port=5000)
