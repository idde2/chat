# 💬 eddi.chat

Ein moderner, leistungsstarker Realtime-Chat-Server & Web-Client, entwickelt mit **Flask**, **Socket.IO** und **MySQL**.

---

## ✨ Features

- 🔐 **Authentifizierung & Sicherheit**: Session- & JWT-basierte Authentifizierung (`PyJWT`), Bcrypt-Passworthashing.
- ⚡ **Realtime-Kommunikation**: Socket.IO WebSockets für 1-zu-1-Chats, Gruppen-Rooms, Live Typing Indicators & Online-Status.
- 👥 **Gruppen-Chats**: Dynamische Gruppenerstellung, Gruppenräume und Mitgliederverwaltung.
- 📁 **Filesharing & Vorschau**: Upload und Vorschau von Bildern, Audiodateien und Dokumenten (bis 10 MB).
- 😃 **Nachrichten-Reaktionen**: Live-Emoji-Reaktionen auf Nachrichten.
- 🖼️ **Medien-Galerie**: REST-Endpunkte & Übersicht aller im Chat ausgetauschten Medien.
- 🎨 **Modernes UI/UX**: Premium Dark-Mode Interface mit Glassmorphism-Effekten, Google Fonts (`Inter`) und flüssigen Animationen.

---

## 🚀 Schnellstart & Installation

### 1. Lokal ausführen

#### Voraussetzungen
- Python 3.10+
- MySQL-Server

#### Installation
```bash
# Repository klonen & in Verzeichnis wechseln
cd chat

# Python Virtual Environment (optional aber empfohlen)
python -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate

# DB Migrationen ausführen
python migrate.py

# Tests starten
python test.py

# Server starten
python main.py
```

Der Server kann ohne weiteres nicht betrieben werden! es wird ein reverseproxy benötigt. der den path /chat hat (in meinem anwendungsfall wird es mit apache2 gemacht)

---

### 🐳 Docker Deployment

Starte die gesamte Anwendung inklusive MySQL-Datenbank mit einem einzigen Befehl:

```bash
docker-compose up --build -d
```

---

## 🔌 REST-API & Socket.IO Endpunkte

### REST API
- `POST /api/auth/login`: Login & Token-Generierung.
- `POST /api/auth/register`: Registrierung neuer Benutzer.
- `GET /api/me`: Eigene Benutzerdaten abrufen.
- `GET /api/contacts`: Kontaktliste abrufen.
- `GET /api/messages/<receiver_id>`: Nachrichtenverlauf laden.
- `POST /api/upload`: Dateiupload (Bilder, Audio, Dokumente).
- `POST /api/messages/<msg_id>/reactions`: Emoji-Reaktionen zu einer Nachricht hinzufügen/entfernen.
- `GET /api/chat/<target_type>/<target_id>/media`: Medien-Galerie abrufen.

---

## 🛠️ Architektur & Ordnerstruktur

```
chat/
├── main.py            # Flask Main Server & Socket.IO Events
├── backend.py         # REST-API Endpunkte & JWT Authentication
├── api.py             # MySQL Connection Pool & Helper-Funktionen
├── migrate.py         # Datenbank-Schema & Migrationen
├── test.py            # Automated Test-Suite
├── Dockerfile         # Docker Image Manifest
├── docker-compose.yml # Container Orchestration
├── static/
│   ├── css/           # Glassmorphism Stylesheets (chat.css, etc.)
│   ├── js/            # Client-seitige Scripts (chat.js)
│   └── uploads/       # Dateiupload-Speicher
└── templates/         # Jinja2 HTML Templates
```
