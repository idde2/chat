# Projekt-Analyse & Feature-Status (eddi.chat)

Stand: **August 2026** – Aktueller Entwicklungs- & Integrationsstatus des Gesamtsystems.

---

## 🏗️ Architektur-Übersicht

1. **Web-Server & Socket.IO (`main.py`)**:
   - Flask-Backend mit automatischer DB-Schema-Migration beim Start (`run_migrations()`).
   - Duale Authentifizierung (Session-Cookie & JWT Fallback) für nahtlosen Web- & API-Zugriff.
   - Realtime-Kommunikation via Socket.IO für 1-zu-1-Chats, Gruppen-Rooms & individuelle User-Rooms.
   - Performance-optimierte Kontaktabfragen, In-Memory Online-Status (`online_users`) & Live Typing Indicator.
   - Routen für Nachrichten-Suche, Nachrichten-Bearbeitung/Löschung sowie Upload-Handling (`/upload`, `/api/upload`).
2. **REST-API & Mobile-Integration (`backend.py`)**:
   - JWT-Token-Authentifizierung (`PyJWT`) via `/api/auth/login` und `/api/auth/register` mit Flask-Session Fallback in `@jwt_required`.
   - Endpunkte für `/api/me`, `/api/contacts`, `/api/users`, `/api/messages`.
   - Gruppenerstellung via `/api/groups/create`.
3. **Datenbank & Connection Pooling (`api.py`, `migrate.py`)**:
   - `MySQLConnectionPool` zur Vermeidung von Verbindungsengpässen und DNS-Timeouts.
   - Robuste Schema-Migrationen in `migrate.py` (`groups`, `group_messages`, `msg.msg_id` [AUTO_INCREMENT PRIMARY KEY], `msg.status`, `msg.file_url`, `msg.msg_type`, `msg.is_encrypted`, `message_reactions`).

---

## 🟢 Umgesetzte Features & System-Upgrades

| Feature / Bereich | Status | Details |
|-------------------|--------|---------|
| 👥 **Gruppen-Chats & Rollen** | ✅ Erledigt | `groups` & `group_messages` Tabellen, Gruppen-Erstellung Modal, Socket.IO Rooms (`group_<id>`) |
| 📁 **Filesharing & Medien-Vorschau** | ✅ Erledigt | `/api/upload` & `/upload` Endpunkte für Bilder, Audios & Dokumente (10MB Limit, `secure_filename`) |
| 👁️ **Read Receipts (Lese-Bestätigungen)** | ✅ Erledigt | `status`-Spalte (`sent`, `delivered`, `read`), automatische `mark_read` Events & Haken-Anzeige (✓ / ✓✓) |
| ⚡ **Performance & Stability Fixes** | ✅ Erledigt | DNS-Timeout behoben (`127.0.0.1`), MySQL Pooling in `api.py`, automatische Session-Cleaner & Auto-Migration in `main.py` |
| 🟢 **Online-Status & Live Typing** | ✅ Erledigt | In-Memory User-Tracking, Socket.IO `online_update`, `typing` & `stop_typing` Events |
| 🔒 **JWT Auth & Session Fallback** | ✅ Erledigt | `@jwt_required` Decorator unterstützt sowohl JWT Bearer Tokens (Mobile) als auch Flask Web-Sessions |
| 🎨 **UI-Integration** | ✅ Erledigt | Einbindung von "Neue Gruppe erstellen", Online-Badges & Medien-Playern unter Wahrung aller bestehenden CSS-Klassen (`.container`, `.contact`, `.add-user`) |
| 😃 **Nachrichten-Reaktionen & Emojis** | ✅ Erledigt | Eindeutige `msg_id` Zuordnung, 0ms optimistisches UI-Update & synchrone Socket.IO Raum-Broadcasts (`reaction_update`) |
| 🖼️ **Medien-Galerie Modal** | ✅ Erledigt | REST/Web Endpunkte `/media/<type>/<id>`, saubere Trennung von Einzel- & Gruppenmedien (`conv IS NULL OR conv = 0`), Vorschau für Bilder, Audio & Dokumente |
| 🔒 **E2E Client-Verschlüsselung** | ✅ Erledigt | Web Crypto API AES-GCM 256-bit Key Derivation (`initE2E`, `encryptMessage`, `decryptMessage`) |

---

## 🔴 Nächste Schritte & Empfohlene Features

### 1️⃣ Push-Benachrichtigungen (Web Push & FCM)
- **Web**: Service Worker (`static/js/sw.js`) & Web Push API für Benachrichtigungen bei geschlossener Seite.
- **Android**: Firebase Cloud Messaging (FCM) für Mobilgeräte.