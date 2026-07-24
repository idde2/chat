from flask import request, jsonify, Blueprint
import jwt
import os
import json
import ast
from datetime import datetime, timedelta, timezone
import bcrypt
from functools import wraps
from api import sqlq

# -------------------------------------------------------
# Blueprint + JWT Secret
# -------------------------------------------------------
back = Blueprint("back", __name__)

# Lese Secret aus Umgebungsvariable, fallback auf festen Wert
JWT_SECRET = os.environ.get("JWT_SECRET", "EDD1_CH4T_JWT_S3CR3T_K3Y_CH4NG3_M3!")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30


# -------------------------------------------------------
# Helper: JWT Token erstellen
# -------------------------------------------------------
def create_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": int((now + timedelta(days=JWT_EXPIRY_DAYS)).timestamp()),
        "iat": int(now.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


# -------------------------------------------------------
# Decorator: JWT-Schutz für Routen
# -------------------------------------------------------
def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"code": 401, "error": "Kein Token angegeben"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify({"code": 401, "error": "Token abgelaufen"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"code": 401, "error": "Ungültiger Token"}), 401
        except Exception as e:
            return jsonify({"code": 401, "error": "Auth Fehler"}), 401

        request.jwt_user_id = int(payload["sub"])
        request.jwt_username = payload["username"]
        return f(*args, **kwargs)
    return decorated


# -------------------------------------------------------
# Hilfsfunktion: Socket.IO JWT-Validierung (für main.py)
# -------------------------------------------------------
def verify_jwt_token(token: str):
    """Gibt (user_id, username) zurück oder wirft Exception."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return int(payload["sub"]), payload["username"]


# -------------------------------------------------------
# Route: GET /api/
# -------------------------------------------------------
@back.route("/")
def index():
    return jsonify({
        "code": 200,
        "name": "eddi.chat API",
        "version": "1.0",
        "endpoints": {
            "auth": {
                "login":    "POST /api/auth/login",
                "register": "POST /api/auth/register",
            },
            "protected": {
                "me":            "GET /api/me",
                "contacts":      "GET /api/contacts",
                "add_contact":   "POST /api/contacts/<user_id>",
                "users":         "GET /api/users",
                "messages":      "GET /api/messages/<receiver_id>",
                "send_message":  "POST /api/messages/<receiver_id>",
            }
        }
    })


# -------------------------------------------------------
# Route: POST /api/auth/login
# -------------------------------------------------------
@back.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return jsonify({"code": 400, "error": "Username und Passwort erforderlich"}), 400

    row = sqlq(
        "SELECT id, password FROM users WHERE username = %s",
        (username,), "one"
    )
    if not row:
        return jsonify({"code": 401, "error": "Ungültige Zugangsdaten"}), 401

    user_id, stored_hash = row[0], row[1]

    # bcrypt-Vergleich
    if not bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
        return jsonify({"code": 401, "error": "Ungültige Zugangsdaten"}), 401

    token = create_token(user_id, username)
    return jsonify({
        "code": 200,
        "token": token,
        "user": {"id": user_id, "username": username}
    })


# -------------------------------------------------------
# Route: POST /api/auth/register
# -------------------------------------------------------
@back.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    email    = str(data.get("email", "")).strip()

    if not username or not password or not email:
        return jsonify({"code": 400, "error": "Username, Passwort und E-Mail erforderlich"}), 400

    existing = sqlq("SELECT id FROM users WHERE username = %s", (username,), "one")
    if existing:
        return jsonify({"code": 409, "error": "Benutzername bereits vergeben"}), 409

    existing_mail = sqlq("SELECT id FROM users WHERE email = %s", (email,), "one")
    if existing_mail:
        return jsonify({"code": 409, "error": "E-Mail bereits vergeben"}), 409

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    sqlq(
        "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
        (username, password_hash, email), "none"
    )

    user_id_row = sqlq("SELECT id FROM users WHERE username = %s", (username,), "one")
    user_id = user_id_row[0]
    token = create_token(user_id, username)
    return jsonify({
        "code": 201,
        "token": token,
        "user": {"id": user_id, "username": username}
    }), 201


# -------------------------------------------------------
# Route: GET /api/me
# -------------------------------------------------------
@back.route("/me")
@jwt_required
def me():
    user_id  = request.jwt_user_id
    username = request.jwt_username
    row = sqlq("SELECT email FROM users WHERE id = %s", (user_id,), "one")
    email = row[0] if row else ""
    return jsonify({
        "code": 200,
        "user": {"id": user_id, "username": username, "email": email}
    })


# -------------------------------------------------------
# Route: GET /api/contacts
# -------------------------------------------------------
@back.route("/contacts")
@jwt_required
def get_contacts():
    user_id = request.jwt_user_id
    row = sqlq("SELECT kontacts FROM users WHERE id = %s", (user_id,), "one")
    if not row or not row[0]:
        return jsonify({"code": 200, "contacts": []})

    raw = row[0]
    try:
        contact_ids = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        try:
            contact_ids = ast.literal_eval(raw)
        except Exception:
            contact_ids = []

    contacts = []
    for cid in contact_ids:
        u = sqlq("SELECT id, username FROM users WHERE id = %s", (cid,), "one")
        if u:
            contacts.append({"id": u[0], "username": u[1]})

    return jsonify({"code": 200, "contacts": contacts})


# -------------------------------------------------------
# Route: POST /api/contacts/<user_id>
# -------------------------------------------------------
@back.route("/contacts/<int:target_id>", methods=["POST"])
@jwt_required
def add_contact(target_id):
    my_id = request.jwt_user_id

    # Existiert der Ziel-User?
    target = sqlq("SELECT id FROM users WHERE id = %s", (target_id,), "one")
    if not target:
        return jsonify({"code": 404, "error": "Benutzer nicht gefunden"}), 404

    row = sqlq("SELECT kontacts FROM users WHERE id = %s", (my_id,), "one")
    raw = row[0] if row else "[]"
    try:
        contact_ids = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        try:
            contact_ids = ast.literal_eval(raw)
        except Exception:
            contact_ids = []

    if target_id not in contact_ids:
        contact_ids.append(target_id)
        sqlq(
            "UPDATE users SET kontacts = %s WHERE id = %s",
            (json.dumps(contact_ids), my_id), "none"
        )

    return jsonify({"code": 200, "message": "Kontakt hinzugefügt"})


# -------------------------------------------------------
# Route: GET /api/users?q=<search>
# -------------------------------------------------------
@back.route("/users")
@jwt_required
def get_users():
    my_id = request.jwt_user_id
    q = request.args.get("q", "").strip()

    if q:
        rows = sqlq(
            "SELECT id, username FROM users WHERE id != %s AND username LIKE %s LIMIT 50",
            (my_id, f"%{q}%"), "all"
        )
    else:
        rows = sqlq(
            "SELECT id, username FROM users WHERE id != %s LIMIT 50",
            (my_id,), "all"
        )

    users = [{"id": r[0], "username": r[1]} for r in rows] if rows else []
    return jsonify({"code": 200, "users": users})


# -------------------------------------------------------
# Route: GET /api/messages/<receiver_id>
# -------------------------------------------------------
@back.route("/messages/<int:receiver_id>")
@jwt_required
def get_messages(receiver_id):
    my_id = request.jwt_user_id
    rows = sqlq(
        """SELECT id, receiver, content, time
           FROM msg
           WHERE (id = %s AND receiver = %s) OR (id = %s AND receiver = %s)
           ORDER BY time ASC""",
        (my_id, receiver_id, receiver_id, my_id), "all"
    )
    messages = []
    if rows:
        for r in rows:
            messages.append({
                "sender_id":   r[0],
                "receiver_id": r[1],
                "content":     r[2],
                "time":        str(r[3]),
                "is_mine":     r[0] == my_id
            })
    return jsonify({"code": 200, "messages": messages})


# -------------------------------------------------------
# Route: POST /api/messages/<receiver_id>
# -------------------------------------------------------
@back.route("/messages/<int:receiver_id>", methods=["POST"])
@jwt_required
def send_message(receiver_id):
    my_id    = request.jwt_user_id
    data     = request.get_json(silent=True) or {}
    content  = str(data.get("content", "")).strip()

    if not content:
        return jsonify({"code": 400, "error": "Nachrichteninhalt erforderlich"}), 400

    # Existiert Empfänger?
    target = sqlq("SELECT username FROM users WHERE id = %s", (receiver_id,), "one")
    if not target:
        return jsonify({"code": 404, "error": "Empfänger nicht gefunden"}), 404

    sqlq(
        "INSERT INTO msg (id, receiver, content) VALUES (%s, %s, %s)",
        (my_id, receiver_id, content), "none"
    )

    # Socket.IO Emit über den globalen socketio aus api.py
    from api import socketio as sio
    if sio:
        ids  = sorted([int(my_id), int(receiver_id)])
        room = f"{ids[0]}_{ids[1]}"
        my_username = request.jwt_username
        sio.emit("msg", {"content": content, "sender": my_username, "sender_id": my_id}, room=room)

    return jsonify({"code": 201, "message": "Nachricht gesendet"})
