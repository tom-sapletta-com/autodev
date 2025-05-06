"""
Moduł do zarządzania projektami webowymi w systemie EvoDev.
Umożliwia tworzenie, wdrażanie i zarządzanie aplikacjami webowymi.
"""
import os
import json
import shutil
import subprocess
import logging
import docker
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ścieżki projektów
PROJECTS_DIR = os.path.expanduser("~/evodev_projects")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

class WebProject:
    """Klasa reprezentująca projekt webowy"""
    
    def __init__(self, name: str, project_type: str, port: int = 8088):
        self.name = name
        self.project_type = project_type
        self.port = port
        self.path = os.path.join(PROJECTS_DIR, name)
        self.container_name = f"evodev-web-{name}"
        
    def create(self) -> bool:
        """Tworzy nowy projekt na podstawie szablonu"""
        try:
            # Upewnij się, że katalogi istnieją
            os.makedirs(PROJECTS_DIR, exist_ok=True)
            
            # Sprawdź, czy projekt już istnieje
            if os.path.exists(self.path):
                logger.error(f"Projekt {self.name} już istnieje")
                return False
            
            # Utwórz katalog projektu
            os.makedirs(self.path)
            
            # Wybierz szablon na podstawie typu projektu
            if self.project_type == "static":
                self._create_static_site()
            elif self.project_type == "react":
                self._create_react_app()
            elif self.project_type == "flask":
                self._create_flask_app()
            else:
                logger.error(f"Nieznany typ projektu: {self.project_type}")
                return False
            
            # Zapisz metadane projektu
            self._save_metadata()
            
            logger.info(f"Projekt {self.name} został utworzony w {self.path}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia projektu: {str(e)}")
            return False
    
    def _create_static_site(self):
        """Tworzy statyczną stronę HTML"""
        index_html = os.path.join(self.path, "index.html")
        with open(index_html, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strona testowa EvoDev</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
        }
        p {
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Witaj w EvoDev!</h1>
        <p>To jest testowa strona utworzona przez system EvoDev.</p>
        <p>Możesz edytować ten plik, aby dostosować zawartość strony.</p>
    </div>
</body>
</html>""")
        
        # Utwórz plik Dockerfile
        dockerfile = os.path.join(self.path, "Dockerfile")
        with open(dockerfile, "w") as f:
            f.write("""FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]""")
            
    def _create_react_app(self):
        """Tworzy aplikację React"""
        # Utwórz podstawową strukturę aplikacji React
        os.makedirs(os.path.join(self.path, "public"))
        os.makedirs(os.path.join(self.path, "src"))
        
        # Utwórz plik package.json
        package_json = os.path.join(self.path, "package.json")
        with open(package_json, "w") as f:
            f.write("""{
  "name": "evodev-react-app",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}""")
        
        # Utwórz plik index.html
        index_html = os.path.join(self.path, "public", "index.html")
        with open(index_html, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="pl">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Aplikacja React EvoDev</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>""")
        
        # Utwórz plik App.js
        app_js = os.path.join(self.path, "src", "App.js")
        with open(app_js, "w") as f:
            f.write("""import React from 'react';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Witaj w EvoDev React App!</h1>
        <p>
          To jest testowa aplikacja React utworzona przez system EvoDev.
        </p>
      </header>
    </div>
  );
}

export default App;""")
        
        # Utwórz plik index.js
        index_js = os.path.join(self.path, "src", "index.js")
        with open(index_js, "w") as f:
            f.write("""import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);""")
        
        # Utwórz plik Dockerfile
        dockerfile = os.path.join(self.path, "Dockerfile")
        with open(dockerfile, "w") as f:
            f.write("""FROM node:16-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000
CMD ["npm", "start"]""")
            
    def _create_flask_app(self):
        """Tworzy aplikację Flask"""
        # Utwórz podstawową strukturę aplikacji Flask
        os.makedirs(os.path.join(self.path, "templates"))
        os.makedirs(os.path.join(self.path, "static"))
        
        # Utwórz plik app.py
        app_py = os.path.join(self.path, "app.py")
        with open(app_py, "w") as f:
            f.write("""from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)""")
        
        # Utwórz plik requirements.txt
        requirements_txt = os.path.join(self.path, "requirements.txt")
        with open(requirements_txt, "w") as f:
            f.write("""flask==2.0.1""")
        
        # Utwórz plik index.html
        index_html = os.path.join(self.path, "templates", "index.html")
        with open(index_html, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aplikacja Flask EvoDev</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
        }
        p {
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Witaj w EvoDev Flask App!</h1>
        <p>To jest testowa aplikacja Flask utworzona przez system EvoDev.</p>
        <p>Możesz edytować ten plik, aby dostosować zawartość strony.</p>
    </div>
</body>
</html>""")
        
        # Utwórz plik Dockerfile
        dockerfile = os.path.join(self.path, "Dockerfile")
        with open(dockerfile, "w") as f:
            f.write("""FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "app.py"]""")
    
    def _save_metadata(self):
        """Zapisuje metadane projektu"""
        metadata = {
            "name": self.name,
            "type": self.project_type,
            "port": self.port,
            "created_at": str(datetime.datetime.now())
        }
        
        metadata_file = os.path.join(self.path, ".evodev.json")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def deploy(self) -> bool:
        """Wdraża projekt jako kontener Docker"""
        try:
            client = docker.from_env()
            
            # Sprawdź, czy kontener już istnieje
            try:
                container = client.containers.get(self.container_name)
                # Jeśli kontener istnieje, zatrzymaj go i usuń
                container.stop()
                container.remove()
                logger.info(f"Usunięto istniejący kontener {self.container_name}")
            except docker.errors.NotFound:
                pass
            
            # Zbuduj obraz Docker
            logger.info(f"Budowanie obrazu Docker dla projektu {self.name}...")
            image, build_logs = client.images.build(
                path=self.path,
                tag=f"evodev-web/{self.name}:latest",
                rm=True
            )
            
            # Mapowanie portów w zależności od typu projektu
            port_mapping = {}
            if self.project_type == "static":
                port_mapping = {80: self.port}
            elif self.project_type == "react":
                port_mapping = {3000: self.port}
            elif self.project_type == "flask":
                port_mapping = {5000: self.port}
            
            # Uruchom kontener
            logger.info(f"Uruchamianie kontenera {self.container_name} na porcie {self.port}...")
            container = client.containers.run(
                image=f"evodev-web/{self.name}:latest",
                name=self.container_name,
                ports=port_mapping,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            logger.info(f"Projekt {self.name} został wdrożony jako kontener {self.container_name}")
            logger.info(f"Aplikacja dostępna pod adresem: http://localhost:{self.port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas wdrażania projektu: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """Zatrzymuje kontener projektu"""
        try:
            client = docker.from_env()
            
            try:
                container = client.containers.get(self.container_name)
                container.stop()
                logger.info(f"Kontener {self.container_name} został zatrzymany")
                return True
            except docker.errors.NotFound:
                logger.error(f"Kontener {self.container_name} nie istnieje")
                return False
                
        except Exception as e:
            logger.error(f"Błąd podczas zatrzymywania kontenera: {str(e)}")
            return False
    
    def start(self) -> bool:
        """Uruchamia kontener projektu"""
        try:
            client = docker.from_env()
            
            try:
                container = client.containers.get(self.container_name)
                container.start()
                logger.info(f"Kontener {self.container_name} został uruchomiony")
                return True
            except docker.errors.NotFound:
                logger.error(f"Kontener {self.container_name} nie istnieje")
                return False
                
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania kontenera: {str(e)}")
            return False
    
    def remove(self) -> bool:
        """Usuwa projekt i jego kontener"""
        try:
            # Zatrzymaj i usuń kontener
            self.stop()
            
            client = docker.from_env()
            try:
                container = client.containers.get(self.container_name)
                container.remove()
                logger.info(f"Kontener {self.container_name} został usunięty")
            except docker.errors.NotFound:
                pass
            
            # Usuń katalog projektu
            if os.path.exists(self.path):
                shutil.rmtree(self.path)
                logger.info(f"Katalog projektu {self.path} został usunięty")
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas usuwania projektu: {str(e)}")
            return False

def list_projects() -> List[Dict[str, Any]]:
    """Zwraca listę wszystkich projektów webowych"""
    try:
        if not os.path.exists(PROJECTS_DIR):
            return []
        
        projects = []
        for project_name in os.listdir(PROJECTS_DIR):
            project_path = os.path.join(PROJECTS_DIR, project_name)
            if os.path.isdir(project_path):
                metadata_file = os.path.join(project_path, ".evodev.json")
                if os.path.exists(metadata_file):
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                        projects.append(metadata)
        
        return projects
    
    except Exception as e:
        logger.error(f"Błąd podczas listowania projektów: {str(e)}")
        return []

def get_project(name: str) -> Optional[WebProject]:
    """Zwraca obiekt projektu na podstawie nazwy"""
    try:
        project_path = os.path.join(PROJECTS_DIR, name)
        metadata_file = os.path.join(project_path, ".evodev.json")
        
        if os.path.exists(metadata_file):
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                return WebProject(
                    name=metadata["name"],
                    project_type=metadata["type"],
                    port=metadata["port"]
                )
        
        return None
    
    except Exception as e:
        logger.error(f"Błąd podczas pobierania projektu: {str(e)}")
        return None

def create_and_deploy_project(name: str, project_type: str, port: int = 8088) -> Tuple[bool, str]:
    """Tworzy i wdraża nowy projekt webowy"""
    try:
        # Sprawdź, czy projekt już istnieje
        if get_project(name):
            return False, f"Projekt o nazwie {name} już istnieje"
        
        # Utwórz nowy projekt
        project = WebProject(name=name, project_type=project_type, port=port)
        if not project.create():
            return False, f"Nie udało się utworzyć projektu {name}"
        
        # Wdróż projekt
        if not project.deploy():
            return False, f"Nie udało się wdrożyć projektu {name}"
        
        return True, f"Projekt {name} został utworzony i wdrożony pod adresem http://localhost:{port}"
    
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia i wdrażania projektu: {str(e)}")
        return False, str(e)
