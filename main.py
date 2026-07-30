from flask import Flask, render_template, request, redirect, session, make_response, jsonify, Response, abort

from flask_session import Session
from flask_socketio import SocketIO, emit, join_room

import json
import bcrypt
from datetime import datetime, timedelta
import os
from PIL import Image, ImageDraw, ImageFont
import ast
import requests as requests

from api import get_connection, set_config, get_conf, log, register_socketio, sqlq, auth, background
from backend import back

import uuid
from werkzeug.utils import secure_filename



domain = str(get_conf("domain"))
path = str(get_conf("path"))


session_dir = os.path.join(os.getcwd(), "flask_session")
os.makedirs(session_dir, exist_ok=True)

# Bereinige beschädigte oder 0-Byte Session-Dateien, die OSError in cachelib verursachen
try:
    for fname in os.listdir(session_dir):
        fpath = os.path.join(session_dir, fname)
        if os.path.isfile(fpath) and os.path.getsize(fpath) == 0:
            os.remove(fpath)
except Exception:
    pass

app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = session_dir
app.config["SESSION_FILE_THRESHOLD"] = 1000
app.config["SECRET_KEY"] = "cdejgkhjkaltkhjdmhtrjklejdklrklgf665gd4f35g735g735g7d57df4ges!7357g74g54th ggfjsdfzjkgfkjgfwerhjukvrtht"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=10)
Session(app)


app.register_blueprint(back, url_prefix="/api")

socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

app.secret_key = "UDCuJKjkHJKFHKHE$(O(OVE(OWKLJJHjkHVRFHJKHGVRZEGHzV SRGFIUIOVHJKRJKJKFJR"
register_socketio(socketio)


UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Max 10 MB

# ------------------------ Online-User Tracking ------------------------
online_users = set()


#-----------------------------------------------------------------------------------------------------------------------------------------------before request--------------------------------------------------------------------------------
@app.before_request
def protect():
    rpath = request.path

    if "static" in rpath:
        return

    if "socket.io" in rpath or "EIO" in request.args:
        return

    if "login" in rpath:
        return

    if rpath.startswith("/pin"):
        return

    if "/api" in rpath:
        return

    if session.get("auth") != True:
        return redirect("/" + path +"/login")


@app.route("/")
def index():
    user = session["user"] if session.get("user") else ""
    user_row = sqlq("SELECT id, kontacts FROM users WHERE username = %s", (user,), "one")
    kontacts = []
    groups = []

    if user_row:
        user_id, raw_k = user_row[0], user_row[1]
        try:
            raw_kontacts = json.loads(raw_k or "[]")
        except Exception:
            raw_kontacts = []

        if raw_kontacts:
            format_strings = ','.join(['%s'] * len(raw_kontacts))
            rows = sqlq(f"SELECT username FROM users WHERE id IN ({format_strings})", tuple(raw_kontacts), "all")
            if rows:
                kontacts = [r[0] for r in rows if r[0]]

        try:
            group_rows = sqlq("SELECT id, name FROM `groups` WHERE owner_id = %s OR members LIKE %s", (user_id, f"%{user_id}%"), "all")
            if group_rows:
                groups = [{"id": r[0], "name": r[1]} for r in group_rows]
        except Exception:
            groups = []

    return render_template("index.html", kontacts=kontacts, groups=groups)



@app.route("/chat/<receiver>")
def chat(receiver):
    user = session["user"] if session.get("user") else ""

    id_u = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]
    id_r = sqlq("SELECT id FROM users WHERE username = %s", (receiver,), "one")[0]

    # Nachrichten abrufen inklusive status, file_url, file_type
    msg = sqlq(
        """SELECT id, content, time, COALESCE(edited,0), status, file_url, file_type 
           FROM msg 
           WHERE (id = %s AND receiver = %s) OR (id = %s AND receiver = %s) 
           ORDER BY time ASC""",
        (id_u, id_r, id_r, id_u), "all"
    )

    # Automatisch empfangene ungelesene Nachrichten als 'read' markieren
    sqlq("UPDATE msg SET status = 'read' WHERE id = %s AND receiver = %s AND status != 'read'", (id_r, id_u), "none")

    return render_template("chat.html", user=id_u, receiver=id_r, receiver_name=receiver, msg=msg)

@app.route("/kontakt/<art>/<id>")
@app.route("/kontakt")
def kontakt(art=None,id=None):

    user = session["user"] if session.get("user") else ""
    id_u = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]

    if id == None:
        data = sqlq("SELECT id,username FROM users WHERE id != %s",(session.get("user"),),"all")
        return render_template("kontakt.html",daten=data)
    elif id != None:
        if art == "1":
            pass
        elif art == "2":
            id = sqlq("SELECT id FROM users WHERE username = %s",(id,),"one")[0]
        kontakte = ast.literal_eval( sqlq("SELECT kontacts FROM users WHERE id = %s",(id_u,),"one")[0] or "[]" )
        if not int(id) in kontakte:
            kontakte.append(int(id))
        sqlq("UPDATE users SET kontacts = %s WHERE username = %s", (str(kontakte), session.get("user")), "none")
        return redirect("/" + path + "/kontakt")
    return redirect("/" + path + "/kontakt")

@app.route("/msg/<receiver>",methods=["POST"])
@app.route("/msg/<receiver>/<msg>")
def msg(receiver,msg=None):
    user = session["user"] if session.get("user") else ""

    if msg == None:
        msg = str(request.form.get("msg"))

    id = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]
    receiver_name = sqlq("SELECT username FROM users WHERE id = %s", (receiver,), "one")[0]

    ids = sorted([int(id), int(receiver)])
    room = f"{ids[0]}_{ids[1]}"

    sqlq("INSERT INTO msg (id, receiver, content, status) VALUES (%s, %s, %s, 'sent')", (id, receiver, msg), "none")

    socketio.emit("msg", {"content": msg, "sender": user, "sender_id": id, "status": "sent"}, room=room)

    return redirect("/" + path + "/chat/" + receiver_name + "")

# ------------------------ Feature: File-Upload ------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    user = session.get("user")
    if not user:
        return jsonify({"code": 401, "error": "Nicht eingeloggt"}), 401

    receiver_id = request.form.get("receiver_id")
    group_id = request.form.get("group_id")
    file = request.files.get("file")

    if not file or file.filename == '':
        return jsonify({"code": 400, "error": "Keine Datei ausgewählt"}), 400

    my_id = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()

    # Bestimme Dateityp (image, audio, document)
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        file_type = 'image'
    elif ext in ['.mp3', '.wav', '.ogg', '.m4a', '.webm']:
        file_type = 'audio'
    else:
        file_type = 'document'

    unique_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(file_path)

    file_url = f"/chat/static/uploads/{unique_name}"
    content = filename

    if group_id:
        group_id = int(group_id)
        sqlq(
            "INSERT INTO msg (id, receiver, conv, content, file_url, file_type, status) VALUES (%s, 0, %s, %s, %s, %s, 'sent')",
            (my_id, group_id, content, file_url, file_type), "none"
        )
        room = f"group_{group_id}"
        socketio.emit("msg", {
            "content": content,
            "sender": user,
            "sender_id": my_id,
            "file_url": file_url,
            "file_type": file_type,
            "status": "sent"
        }, room=room)
    elif receiver_id:
        receiver_id = int(receiver_id)
        sqlq(
            "INSERT INTO msg (id, receiver, content, file_url, file_type, status) VALUES (%s, %s, %s, %s, %s, 'sent')",
            (my_id, receiver_id, content, file_url, file_type), "none"
        )
        ids = sorted([int(my_id), receiver_id])
        room = f"{ids[0]}_{ids[1]}"
        socketio.emit("msg", {
            "content": content,
            "sender": user,
            "sender_id": my_id,
            "file_url": file_url,
            "file_type": file_type,
            "status": "sent"
        }, room=room)

    return jsonify({"code": 200, "file_url": file_url, "file_type": file_type})

# ------------------------ Feature: Gruppen-Chat ------------------------
@app.route("/create_group", methods=["POST"])
def create_group():
    user = session.get("user")
    if not user:
        return jsonify({"code": 401, "error": "Nicht eingeloggt"}), 401

    data = request.get_json(silent=True) or {}
    group_name = data.get("name", "").strip()
    member_ids = data.get("members", [])

    if not group_name:
        return jsonify({"code": 400, "error": "Gruppenname erforderlich"}), 400

    my_id = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]
    if my_id not in member_ids:
        member_ids.append(my_id)

    members_json = json.dumps(member_ids)
    sqlq("INSERT INTO `groups` (name, owner_id, members) VALUES (%s, %s, %s)", (group_name, my_id, members_json), "none")

    group_id_row = sqlq("SELECT LAST_INSERT_ID()", (), "one")
    group_id = group_id_row[0] if group_id_row else None

    return jsonify({"code": 201, "group": {"id": group_id, "name": group_name}})


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = str(request.form.get("username"))
        password = str(request.form.get("password"))
        email = str(request.form.get("email"))

        user = sqlq("SELECT id FROM users WHERE username = %s",(name,),"one")
        if not user:
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            img = Image.new('RGB', (1000, 1000), (127, 127, 127))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 100)
                draw.text((400, 450), name, fill=(255, 0, 0), font=font)
            except:
                draw.text((400, 450), name, fill=(255, 0, 0))
            img.save("static/img/profil/" + name + ".png")

            sqlq("INSERT INTO users (username, password,email) VALUES (%s, %s,%s)", (name, password_hash,email),"none")
            return redirect("/" + path +"/login")
        else:
            return render_template("register.html", daten="Benutzername existiert bereits")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        passw = request.form.get("password")
        req = auth(user, passw)
        if req["data"] == 1:
            session.permanent = True
            session["auth"] = True
            session["user"] = user

            if not os.path.exists("static/img/profil/" + user + ".png"):
                img = Image.new('RGB', (1000, 1000), (127, 127, 127))
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 100)
                    draw.text((400, 450), user, fill=(255, 0, 0), font=font)
                except:
                    draw.text((400, 450), user, fill=(255, 0, 0))
                img.save("static/img/profil/" + user + ".png")

            return redirect("/" + path)
    return render_template("login.html")


@app.route("/logout")
def logout():
    session["auth"] = False
    session["user"] = ""
    session.clear()
    session.pop("user", None)
    return redirect("/" + path + "/login")


# ------------------------ Feature 1: Nachrichten-Suche ------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if len(q) < 1:
        return jsonify({"results": []})

    user = session.get("user")
    if not user:
        return jsonify({"results": []})

    my_id = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")
    if not my_id:
        return jsonify({"results": []})
    my_id = my_id[0]

    like = f"%{q}%"
    rows = sqlq(
        """SELECT m.id, m.content, m.time, u.username
           FROM msg m
           JOIN users u ON u.id = m.id
           WHERE (m.id = %s OR m.receiver = %s)
             AND m.content LIKE %s
           ORDER BY m.time DESC
           LIMIT 50""",
        (my_id, my_id, like), "all"
    )

    results = []
    if rows:
        for r in rows:
            results.append({
                "msg_id": r[0],
                "content": r[1][:100],
                "time": str(r[2]),
                "other_user": r[3]
            })

    return jsonify({"results": results})


# ------------------------ Feature 2: Typing Event ------------------------
@socketio.on('typing')
def on_typing(data):
    my_id = data.get("user_id")
    target_id = data.get("receiver")
    if not my_id or not target_id:
        return
    ids = sorted([int(my_id), int(target_id)])
    room = f"{ids[0]}_{ids[1]}"
    emit("typing", {"user_id": my_id}, room=room, include_self=False)

@socketio.on('stop_typing')
def on_stop_typing(data):
    my_id = data.get("user_id")
    target_id = data.get("receiver")
    if not my_id or not target_id:
        return
    ids = sorted([int(my_id), int(target_id)])
    room = f"{ids[0]}_{ids[1]}"
    emit("stop_typing", {"user_id": my_id}, room=room, include_self=False)


# ------------------------ Feature 3: Read Receipts ------------------------
@socketio.on('mark_read')
def on_mark_read(data):
    my_id = data.get("user_id")
    sender_id = data.get("sender_id")
    if not my_id or not sender_id:
        return

    sqlq("UPDATE msg SET status = 'read' WHERE id = %s AND receiver = %s AND status != 'read'", (sender_id, my_id), "none")

    ids = sorted([int(my_id), int(sender_id)])
    room = f"{ids[0]}_{ids[1]}"
    emit("messages_read", {"reader_id": my_id, "sender_id": sender_id}, room=room)


# ------------------------ Feature 4: Nachricht bearbeiten & löschen ------------------------
@app.route("/edit_msg", methods=["POST"])
def edit_msg():
    data = request.get_json(silent=True) or {}
    msg_id = data.get("msg_id")
    new_content = data.get("content", "").strip()
    user = session.get("user")

    if not msg_id or not new_content or not user:
        return jsonify({"code": 400, "error": "Fehlende Parameter"}), 400

    my_id = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")
    if not my_id:
        return jsonify({"code": 401, "error": "Nicht eingeloggt"}), 401
    my_id = my_id[0]

    row = sqlq("SELECT id, receiver FROM msg WHERE id = %s AND msg_id = %s", (my_id, msg_id), "one")
    if not row:
        return jsonify({"code": 403, "error": "Nicht deine Nachricht"}), 403

    sqlq("UPDATE msg SET content = %s, edited = 1 WHERE msg_id = %s", (new_content, msg_id), "none")

    ids = sorted([int(row[0]), int(row[1])])
    room = f"{ids[0]}_{ids[1]}"
    socketio.emit("msg_edited", {"msg_id": msg_id, "content": new_content}, room=room)

    return jsonify({"code": 200})


@app.route("/delete_msg", methods=["POST"])
def delete_msg():
    data = request.get_json(silent=True) or {}
    msg_id = data.get("msg_id")
    user = session.get("user")

    if not msg_id or not user:
        return jsonify({"code": 400, "error": "Fehlende Parameter"}), 400

    my_id = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")
    if not my_id:
        return jsonify({"code": 401, "error": "Nicht eingeloggt"}), 401
    my_id = my_id[0]

    row = sqlq("SELECT id, receiver FROM msg WHERE id = %s AND msg_id = %s", (my_id, msg_id), "one")
    if not row:
        return jsonify({"code": 403, "error": "Nicht deine Nachricht"}), 403

    deleted_text = "🗑️ Nachricht gelöscht"
    sqlq("UPDATE msg SET content = %s, edited = 0 WHERE msg_id = %s", (deleted_text, msg_id), "none")

    ids = sorted([int(row[0]), int(row[1])])
    room = f"{ids[0]}_{ids[1]}"
    socketio.emit("msg_deleted", {"msg_id": msg_id, "content": deleted_text}, room=room)

    return jsonify({"code": 200})


# ------------------------ Socket.IO Events ------------------------
@socketio.on('join')
def on_join(data):
    token = data.get("token")
    my_id = None
    try:
        if token:
            from backend import verify_jwt_token
            my_id, my_name = verify_jwt_token(token)
        else:
            my_name = session.get("user")
            if not my_name:
                return
            row = sqlq("SELECT id FROM users WHERE username = %s", (my_name,), "one")
            if row:
                my_id = row[0]

        if my_id is None:
            return

        group_id = data.get("group_id")
        if group_id:
            join_room(f"group_{group_id}")
            return

        target_id = data.get("receiver")
        if not target_id:
            return

        try:
            ids = sorted([int(my_id), int(target_id)])
            room = f"{ids[0]}_{ids[1]}"
            join_room(room)
        except ValueError:
            pass

    except Exception as e:
        pass


@socketio.on_error_default
def default_error_handler(e):
    pass

@socketio.on('connect')
def on_connect():
    user = session.get("user")
    if user:
        online_users.add(user)
        socketio.emit("online_update", {"users": list(online_users)})

@socketio.on('disconnect')
def on_disconnect():
    user = session.get("user")
    if user and user in online_users:
        online_users.discard(user)
        socketio.emit("online_update", {"users": list(online_users)})


if __name__ == "__main__":

    set_config()
    socketio.run(
        app,
        host="0.0.0.0",
        port=7000,
        debug=True,
        allow_unsafe_werkzeug=True
    )


#         ssl_context=("https/cert.pem", "https/key.pem"),