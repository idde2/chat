# Projekt-Analyse & Feature-Status (eddi.chat)

Nach umfassender Analyse des gesamten Projekts (Web-Backend `main.py`, REST-API `backend.py`, DB-Modell `api.py`/`migrate.py`, Frontend-Templates sowie der Android App in Jetpack Compose):

---

## 🏗️ Architektur-Übersicht

1. **Web-Server & Socket.IO (`main.py`)**:
   - Session-basiertes Web-Interface (Flask)
   - Realtime-Kommunikation über Flask-SocketIO (Räume pro Chat-Paar `id1_id2`)
   - Nachrichten-Suche, Online-Status & Nachrichten-Bearbeitung/Löschung
2. **REST-API & Mobile-Integration (`backend.py`)**:
   - JWT-Authentifizierung (`/api/auth/login`, `/api/auth/register`)
   - Endpunkte für `/api/me`, `/api/contacts`, `/api/users`, `/api/messages`
   - Vorbereitung für die Android App (Jetpack Compose UI)
3. **Datenbank & Helpers (`api.py`, `migrate.py`)**:
   - MySQL-Datenbankanbindung (`sqlq`)
   - Schema-Migrationen für `status`, `groups`, `conv`, `edited`

---

## 🟢 Bereits umgesetzte Features & Fixes

| Feature / Bereich | Status | Details |
|-------------------|--------|---------|
| 🔒 **JWT Auth & REST API** | ✅ Erledigt | Endpunkte in `backend.py`, Token-basierte Auth für Socket.IO & Android App |
| 🔍 **Nachrichten-Suche** | ✅ Erledigt | Route `/search` in `main.py` (Volltextsuche in `msg.content`) |
| 🟢 **Online-Status & Typing** | ✅ Erledigt | Events `typing`, `stop_typing` & tracking in `online_users` |
| ✏️ **Nachrichten-Edit & Delete** | ✅ Erledigt | Endpunkte `/edit_msg` & `/delete_msg` mit Socket.IO-Broadcasts (`msg_edited`, `msg_deleted`) |
| 🛠️ **DB-Migrationen** | ✅ Erledigt | `migrate.py` fügt `status`, `groups`, `conv` Spalten hinzu |

---

## 🔴 Noch offene Punkte & Nächste Schritte

### 1️⃣ Push-Benachrichtigungen (Web Push & FCM)
- **Web**: Service Worker (`static/js/sw.js`) & Web Push API (`pywebpush`)
- **Android**: Firebase Cloud Messaging (FCM) für Hintergrund-Benachrichtigungen bei geschlossener App

### 2️⃣ Reaktionen & Zitate (Replies)
- DB-Tabelle `reactions` (`msg_id`, `user_id`, `reaction`)
- `replied_to` Spalte in `msg` für Antworten auf spezifische Nachrichten
- Frontend-UI (Web & Compose) zur Auswahl von Emojis & Vorschau von Zitaten

### 3️⃣ Medien-Galerie & Anhang-Manager
- Route `/gallery/<receiver>` zur Übersicht aller geteilten Bilder/Dateien
- Lightbox-Vorschau im Web-Interface und Grid-View in der Android App

### 4️⃣ Android App (Compose UI Sync)
- Anbindung der neuen Backend-Features (`typing`, `/search`, `/edit_msg`, `/delete_msg`) an die Kotlin-Screens (`ChatScreen.kt`, `ContactsScreen.kt`)

---

## 📊 Roadmap & Priorität

1. **Android App Synchronisation**: Einbinden von Typing-Indikatoren & Edit/Delete in `ChatScreen.kt`
2. **Push Notifications**: FCM / WebPush Integration
3. **Medien-Galerie & Reaktionen**: Ausbau der Interaktionsmöglichkeiten