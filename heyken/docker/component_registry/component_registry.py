#!/usr/bin/env python3
import os
import json
import logging
import psycopg2
from flask import Flask, request, jsonify

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/logs/component_registry.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("component_registry")

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

@app.route("/components", methods=["GET"])
def get_components():
    """Endpoint do pobierania komponentów"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Błąd połączenia z bazą danych"}), 500
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT component_name, version, status, created_at, updated_at, description
                FROM component_versions
                ORDER BY component_name, created_at DESC
            """)
            components = []
            for row in cur.fetchall():
                components.append({
                    "component_name": row[0],
                    "version": row[1],
                    "status": row[2],
                    "created_at": str(row[3]),
                    "updated_at": str(row[4]),
                    "description": row[5]
                })
        
        conn.close()
        return jsonify({"success": True, "components": components})
    
    except Exception as e:
        logger.error(f"Błąd podczas pobierania komponentów: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/components/<component_name>", methods=["GET"])
def get_component_versions(component_name):
    """Endpoint do pobierania wersji konkretnego komponentu"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Błąd połączenia z bazą danych"}), 500
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT component_name, version, status, created_at, updated_at, description
                FROM component_versions
                WHERE component_name = %s
                ORDER BY created_at DESC
            """, (component_name,))
            versions = []
            for row in cur.fetchall():
                versions.append({
                    "component_name": row[0],
                    "version": row[1],
                    "status": row[2],
                    "created_at": str(row[3]),
                    "updated_at": str(row[4]),
                    "description": row[5]
                })
        
        conn.close()
        return jsonify({"success": True, "versions": versions})
    
    except Exception as e:
        logger.error(f"Błąd podczas pobierania wersji komponentu {component_name}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/components", methods=["POST"])
def register_component():
    """Endpoint do rejestracji nowej wersji komponentu"""
    try:
        data = request.json
        component_name = data.get("component_name")
        version = data.get("version")
        status = data.get("status", "active")
        description = data.get("description", "")
        
        if not component_name or not version:
            return jsonify({"success": False, "error": "Brak wymaganych pól: component_name, version"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Błąd połączenia z bazą danych"}), 500
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO component_versions (component_name, version, status, description)
                VALUES (%s, %s, %s, %s)
                RETURNING id, created_at, updated_at
            """, (component_name, version, status, description))
            
            result = cur.fetchone()
            component_id = result[0]
            created_at = result[1]
            updated_at = result[2]
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "component": {
                "id": component_id,
                "component_name": component_name,
                "version": version,
                "status": status,
                "created_at": str(created_at),
                "updated_at": str(updated_at),
                "description": description
            }
        })
    
    except Exception as e:
        logger.error(f"Błąd podczas rejestracji komponentu: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/components/<component_name>/<version>", methods=["PUT"])
def update_component_status(component_name, version):
    """Endpoint do aktualizacji statusu komponentu"""
    try:
        data = request.json
        new_status = data.get("status")
        
        if not new_status:
            return jsonify({"success": False, "error": "Brak wymaganego pola: status"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Błąd połączenia z bazą danych"}), 500
        
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE component_versions
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE component_name = %s AND version = %s
                RETURNING id, created_at, updated_at
            """, (new_status, component_name, version))
            
            if cur.rowcount == 0:
                conn.close()
                return jsonify({"success": False, "error": "Komponent nie znaleziony"}), 404
            
            result = cur.fetchone()
            component_id = result[0]
            created_at = result[1]
            updated_at = result[2]
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "component": {
                "id": component_id,
                "component_name": component_name,
                "version": version,
                "status": new_status,
                "created_at": str(created_at),
                "updated_at": str(updated_at)
            }
        })
    
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji statusu komponentu: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Uruchamianie Component Registry...")
    app.run(host="0.0.0.0", port=5000)
