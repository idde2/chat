# Projekt-Analyse & Feature-Status (eddi.chat)

Stand: **August 2026** – Aktueller Entwicklungs- & Integrationsstatus des Gesamtsystems.

---

## 🏗️ Architektur-Übersicht

1. **Web-Server & Socket.IO (`main.py`)**:
   - Flask-Backend mit Session- & JWT-Authentifizierung.
   - Realtime-Kommunikation via Socket.IO für 1-zu-1-Chats & Gruppen-Rooms.
   - Performance-optimierte Kontaktabfragen, In-Memory Online-Status (`online_users`) & Live Typing Indicator.
   - Routen für Nachrichten-Suche, Nachrichten-Bearbeitung/Löschung sowie Upload-Handling (`/api/upload`).
2. **REST-API & Mobile-Integration (`backend.py`)**:
   - JWT-Token-Authentifizierung (`PyJWT`) via `/api/auth/login` und `/api/auth/register`.
   - Endpunkte für `/api/me`, `/api/contacts`, `/api/users`, `/api/messages`.
   - Gruppenerstellung via `/api/groups/create`.
3. **Datenbank & Connection Pooling (`api.py`, `migrate.py`)**:
   - `MySQLConnectionPool` zur Vermeidung von Verbindungsengpässen und DNS-Timeouts.
   - Robuste Schema-Migrationen in `migrate.py` (`groups`, `group_messages`, `msg.status`, `msg.file_url`, `msg.msg_type`, `msg.is_encrypted`).

---

## 🟢 Umgesetzte Features & System-Upgrades

| Feature / Bereich | Status | Details |
|-------------------|--------|---------|
| 👥 **Gruppen-Chats & Rollen** | ✅ Erledigt | `groups` & `group_messages` Tabellen, Gruppen-Erstellung Modal, Socket.IO Rooms (`group_<id>`) |
| 📁 **Filesharing & Medien-Vorschau** | ✅ Erledigt | `/api/upload` & `/upload` Endpunkte für Bilder, Audios & Dokumente (10MB Limit, `secure_filename`) |
| 👁️ **Read Receipts (Lese-Bestätigungen)** | ✅ Erledigt | `status`-Spalte (`sent`, `delivered`, `read`), automatische `mark_read` Events & Haken-Anzeige (✓ / ✓✓) |
| ⚡ **Performance & Stability Fixes** | ✅ Erledigt | DNS-Timeout behoben (`127.0.0.1`), MySQL Pooling in `api.py`, automatische Session-Cleaner in `main.py` |
| 🟢 **Online-Status & Live Typing** | ✅ Erledigt | In-Memory User-Tracking, Socket.IO `online_update`, `typing` & `stop_typing` Events |
| 🔒 **JWT Auth & PyJWT Integration** | ✅ Erledigt | `PyJWT` Paket-Integration für token-basierte REST- & Mobile-Authentifizierung |
| 🎨 **UI-Integration** | ✅ Erledigt | Einbindung von "Neue Gruppe erstellen", Online-Badges & Medien-Playern unter Wahrung aller bestehenden CSS-Klassen (`.container`, `.contact`, `.add-user`) |
| 😃 **Nachrichten-Reaktionen & Emojis** | ✅ Erledigt | `message_reactions` DB-Tabelle, Quick-Emoji Picker & Socket `reaction_update` |
| 🖼️ **Medien-Galerie Modal** | ✅ Erledigt | REST Endpunkt `/api/chat/<type>/<id>/media`, Modal-Übersicht für Bilder, Audios & Dokumente |
| 🔒 **E2E Client-Verschlüsselung** | ✅ Erledigt | Web Crypto API AES-GCM 256-bit Key Derivation (`initE2E`, `encryptMessage`, `decryptMessage`) |

---

## 🔴 Nächste Schritte & Empfohlene Features

### 1️⃣ Push-Benachrichtigungen (Web Push & FCM)
- **Web**: Service Worker (`static/js/sw.js`) & Web Push API für Benachrichtigungen bei geschlossener Seite.
- **Android**: Firebase Cloud Messaging (FCM) für Mobilgeräte.