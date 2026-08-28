from flask import Flask, render_template, request, redirect, session, make_response, jsonify, Response, abort, send_from_directory


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
from migrate import run_migrations


try:
    run_migrations()
except Exception as e:
    print(f"[WARN] Migration beim Start fehlgeschlagen: {e}")

import uuid
import time
from werkzeug.utils import secure_filename




domain = str(get_conf("domain"))
path = str(get_conf("path"))


session_dir = os.path.join(os.getcwd(), "flask_session")
os.makedirs(session_dir, exist_ok=True)


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

socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*", path='/socket.io')

app.secret_key = "UDCuJKjkHJKFHKHE$(O(OVE(OWKLJJHjkHVRFHJKHGVRZEGHzV SRGFIUIOVHJKRJKJKFJR"
register_socketio(socketio)


UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  

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
            like_pattern = f"%{user_id}%"
            group_rows = sqlq(
                "SELECT id, name FROM `groups` WHERE owner_id = %s OR owner = %s OR members LIKE %s",
                (user_id, user_id, like_pattern),
                "all"
            )
            if group_rows:
                groups = [{"id": r[0], "name": r[1]} for r in group_rows]
        except Exception:
            try:
                group_rows = sqlq("SELECT id, name FROM `groups` WHERE members LIKE %s", (like_pattern,), "all")
                if group_rows:
                    groups = [{"id": r[0], "name": r[1]} for r in group_rows]
            except Exception:
                groups = []

    return render_template("index.html", kontacts=kontacts, groups=groups)


@app.route('/users_list')
@app.route('/chat/users_list')
def users_list():
    user = session.get('user')
    if not user:
        return jsonify({"code":401, "users": []})

    rows = sqlq("SELECT id, username FROM users WHERE username != %s ORDER BY username LIMIT 500", (user,), "all")
    users = [{"id": r[0], "username": r[1]} for r in rows] if rows else []
    return jsonify({"code":200, "users": users})



@app.route("/chat/<receiver>")
def chat(receiver):
    user = session["user"] if session.get("user") else ""

    id_u = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]
    id_r = sqlq("SELECT id FROM users WHERE username = %s", (receiver,), "one")[0]

    try:
        msg = sqlq(
            """SELECT m.msg_id, m.content, m.time, COALESCE(m.edited,0), m.status, m.file_url, m.file_type, u.username, m.id
               FROM msg m
               LEFT JOIN users u ON u.id = m.id
               WHERE (m.id = %s AND m.receiver = %s) OR (m.id = %s AND m.receiver = %s)
               ORDER BY m.time ASC""",
            (id_u, id_r, id_r, id_u), "all"
        )
    except Exception:
        msg = sqlq(
            """SELECT m.id, m.content, m.time, COALESCE(m.edited,0), m.status, m.file_url, m.file_type, u.username, m.id
               FROM msg m
               LEFT JOIN users u ON u.id = m.id
               WHERE (m.id = %s AND m.receiver = %s) OR (m.id = %s AND m.receiver = %s)
               ORDER BY m.time ASC""",
            (id_u, id_r, id_r, id_u), "all"
        )

    sqlq("UPDATE msg SET status = 'read' WHERE id = %s AND receiver = %s AND status != 'read'", (id_r, id_u), "none")

    reactions_map = {}
    if msg:
        msg_ids = [m[0] for m in msg if m[0]]
        if msg_ids:
            try:
                format_ids = ','.join(['%s'] * len(msg_ids))
                r_rows = sqlq(f"SELECT message_id, emoji, user_id FROM message_reactions WHERE message_id IN ({format_ids})", tuple(msg_ids), "all")
                if r_rows:
                    for r_msg_id, emo, uid in r_rows:
                        if r_msg_id not in reactions_map:
                            reactions_map[r_msg_id] = {}
                        if emo not in reactions_map[r_msg_id]:
                            reactions_map[r_msg_id][emo] = []
                        reactions_map[r_msg_id][emo].append(uid)
            except Exception:
                pass

    return render_template("chat.html", user=id_u, receiver=id_r, receiver_name=receiver, msg=msg, reactions_map=reactions_map)


@app.route('/group/<int:conv_id>')
def group_chat(conv_id):
    user = session["user"] if session.get("user") else ""
    if not user:
        return redirect("/" + path + "/login")

    my_id = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]


    grp = sqlq("SELECT id, name, members FROM `groups` WHERE id = %s", (conv_id,), "one")
    if not grp:
        return redirect("/" + path)
    group_name = grp[1]
    raw_members = grp[2]

    members = []
    try:
        members = json.loads(raw_members) if raw_members else []
    except Exception:
        try:
            members = ast.literal_eval(raw_members) if raw_members else []
        except Exception:

            try:
                members = [int(x.strip()) for x in str(raw_members).split(",") if x.strip()]
            except Exception:
                members = []

    participant_list = []
    if members:
        try:
            format_strings = ','.join(['%s'] * len(members))
            rows = sqlq(f"SELECT id, username FROM users WHERE id IN ({format_strings})", tuple(members), "all")
            if rows:
                participant_list = [{"id": r[0], "username": r[1]} for r in rows]
        except Exception:
            participant_list = []

    try:
        rows = sqlq(
            "SELECT m.msg_id, m.content, m.time, COALESCE(m.edited,0), m.status, m.file_url, m.file_type, u.username, m.id FROM msg m LEFT JOIN users u ON u.id = m.id WHERE m.conv = %s ORDER BY m.time ASC",
            (conv_id,), "all"
        )
    except Exception:
        rows = sqlq(
            "SELECT m.id, m.content, m.time, COALESCE(m.edited,0), m.status, m.file_url, m.file_type, u.username, m.id FROM msg m LEFT JOIN users u ON u.id = m.id WHERE m.conv = %s ORDER BY m.time ASC",
            (conv_id,), "all"
        )

    reactions_map = {}
    if rows:
        msg_ids = [m[0] for m in rows if m[0]]
        if msg_ids:
            format_ids = ','.join(['%s'] * len(msg_ids))
            r_rows = sqlq(f"SELECT message_id, emoji, user_id FROM message_reactions WHERE message_id IN ({format_ids})", tuple(msg_ids), "all")
            if r_rows:
                for r_msg_id, emo, uid in r_rows:
                    if r_msg_id not in reactions_map:
                        reactions_map[r_msg_id] = {}
                    if emo not in reactions_map[r_msg_id]:
                        reactions_map[r_msg_id][emo] = []
                    reactions_map[r_msg_id][emo].append(uid)

    return render_template("chat.html", user=my_id, receiver=0, receiver_name=group_name, msg=rows, group_id=conv_id, participants=participant_list, reactions_map=reactions_map)


@app.route('/group/<int:gid>/add/<int:uid>')
def add_member(gid, uid):
    user = session.get("user")
    if not user:
        return redirect("/" + path + "/login")

    my_id = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]


    row = sqlq("SELECT members FROM `groups` WHERE id = %s", (gid,), "one")
    if not row:
        return redirect(request.referrer or ("/" + path))

    try:
        members = json.loads(row[0]) if row[0] else []
    except Exception:
        try:
            members = ast.literal_eval(row[0]) if row[0] else []
        except Exception:
            members = []

    if uid not in members:
        members.append(uid)
        sqlq("UPDATE `groups` SET members = %s WHERE id = %s", (json.dumps(members), gid), "none")

    return redirect(request.referrer or ("/" + path + "/group/" + str(gid)))

@app.route("/kontakt/<art>/<id>")
@app.route("/kontakt")
def kontakt(art=None,id=None):
    user = session["user"] if session.get("user") else ""

    if art == "del":
        kontakte = ast.literal_eval(sqlq("SELECT kontacts FROM users WHERE id = %s", (sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0],), "one")[0] or "[]")
        kontakte.remove(int(id))
        sqlq("UPDATE users SET kontacts = %s WHERE username = %s", (str(kontakte), user), "none")
        return redirect("/" + path)


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
    user = session.get("user") if session.get("user") else ""

    group_id = request.form.get("group_id") or request.form.get("conv")

    if msg is None:
        msg = str(request.form.get("msg") or "")

    my = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")
    if not my:
        return redirect("/" + path + "/login")
    my_id = my[0]

    if group_id:
        try:
            gid = int(group_id)
        except Exception:
            return jsonify({"code":400, "error":"Ungültige group_id"}), 400

        sqlq(
            "INSERT INTO msg (id, receiver, conv, content, status) VALUES (%s, %s, %s, %s, 'sent')",
            (my_id, 0, gid, msg), "none"
        )
        msg_id_row = sqlq("SELECT LAST_INSERT_ID()", (), "one")
        msg_id = msg_id_row[0] if msg_id_row else 0

        socketio.emit("msg", {"content": msg, "sender": user, "sender_id": my_id, "status": "sent", "msg_id": msg_id}, room=f"group_{gid}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json or request.headers.get("Accept", "").find("application/json") != -1:
            return jsonify({"code": 200, "message": "Gesendet", "msg_id": msg_id})
        return redirect("/" + path + "/group/" + str(gid))
    try:
        recv_id = int(receiver)
        row = sqlq("SELECT username FROM users WHERE id = %s", (recv_id,), "one")
        if not row:
            return redirect("/" + path)
        receiver_name = row[0]
    except ValueError:
        row = sqlq("SELECT id FROM users WHERE username = %s", (receiver,), "one")
        if not row:
            return redirect("/" + path)
        recv_id = row[0]
        receiver_name = receiver

    ids = sorted([int(my_id), int(recv_id)])
    room = f"{ids[0]}_{ids[1]}"

    sqlq("INSERT INTO msg (id, receiver, content, status) VALUES (%s, %s, %s, 'sent')", (my_id, recv_id, msg), "none")
    msg_id_row = sqlq("SELECT LAST_INSERT_ID()", (), "one")
    msg_id = msg_id_row[0] if msg_id_row else 0

    msg_payload = {"content": msg, "sender": user, "sender_id": my_id, "status": "sent", "msg_id": msg_id}
    print(f"[MSG-EMIT] room={room}, payload={msg_payload}")
    socketio.emit("msg", msg_payload, room=room)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json or request.headers.get("Accept", "").find("application/json") != -1:
        return jsonify({"code": 200, "message": "Gesendet", "msg_id": msg_id})

    return redirect("/" + path + "/chat/" + receiver_name + "")

# ------------------------ File-Upload ------------------------
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
        msg_id_row = sqlq("SELECT LAST_INSERT_ID()", (), "one")
        msg_id = msg_id_row[0] if msg_id_row else 0
        room = f"group_{group_id}"
        socketio.emit("msg", {
            "content": content,
            "sender": user,
            "sender_id": my_id,
            "file_url": file_url,
            "file_type": file_type,
            "status": "sent",
            "msg_id": msg_id
        }, room=room)
    elif receiver_id:
        receiver_id = int(receiver_id)
        sqlq(
            "INSERT INTO msg (id, receiver, content, file_url, file_type, status) VALUES (%s, %s, %s, %s, %s, 'sent')",
            (my_id, receiver_id, content, file_url, file_type), "none"
        )
        msg_id_row = sqlq("SELECT LAST_INSERT_ID()", (), "one")
        msg_id = msg_id_row[0] if msg_id_row else 0
        ids = sorted([int(my_id), receiver_id])
        room = f"{ids[0]}_{ids[1]}"
        socketio.emit("msg", {
            "content": content,
            "sender": user,
            "sender_id": my_id,
            "file_url": file_url,
            "file_type": file_type,
            "status": "sent",
            "msg_id": msg_id
        }, room=room)

    return jsonify({"code": 200, "file_url": file_url, "file_type": file_type})

@app.route("/chat/media/<target_type>/<target_id>", methods=["GET"])
@app.route("/media/<target_type>/<target_id>", methods=["GET"])
@app.route("/api/chat/<target_type>/<target_id>/media", methods=["GET"])
@app.route("/chat/api/chat/<target_type>/<target_id>/media", methods=["GET"])
def get_chat_media(target_type, target_id):
    user = session.get("user")
    if not user:
        return jsonify({"code": 401, "error": "Nicht eingeloggt"}), 401

    my_id_row = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")
    if not my_id_row:
        return jsonify({"code": 401, "error": "Ungültiger Benutzer"}), 401
    my_id = my_id_row[0]

    target_user_id = target_id
    if target_type != "group":
        try:
            target_user_id = int(target_id)
        except ValueError:
            row = sqlq("SELECT id FROM users WHERE username = %s", (str(target_id),), "one")
            if row:
                target_user_id = row[0]

    if target_type == "group":
        rows = sqlq(
            """SELECT msg_id, content, file_url, file_type, time 
               FROM msg 
               WHERE conv = %s AND file_url IS NOT NULL AND file_url != '' 
               ORDER BY time DESC""",
            (int(target_id),), "all"
        )
    else:
        rows = sqlq(
            """SELECT msg_id, content, file_url, file_type, time 
               FROM msg 
               WHERE ((id = %s AND receiver = %s) OR (id = %s AND receiver = %s)) 
                 AND (conv IS NULL OR conv = 0)
                 AND file_url IS NOT NULL AND file_url != '' 
               ORDER BY time DESC""",
            (my_id, target_user_id, target_user_id, my_id), "all"
        )

    media = []
    if rows:
        for r in rows:
            media.append({
                "msg_id": r[0],
                "content": r[1],
                "file_url": r[2],
                "file_type": r[3],
                "time": str(r[4])
            })

    return jsonify({"code": 200, "media": media})


# ------------------------ Reactions API ------------------------
@app.route("/chat/reactions/<int:msg_id>", methods=["POST"])
@app.route("/reactions/<int:msg_id>", methods=["POST"])
@app.route("/api/messages/<int:msg_id>/reactions", methods=["POST"])
@app.route("/chat/api/messages/<int:msg_id>/reactions", methods=["POST"])
def toggle_message_reaction(msg_id):
    user = session.get("user")
    if not user:
        return jsonify({"code": 401, "error": "Nicht eingeloggt"}), 401
    data = request.get_json(silent=True) or {}
    emoji = data.get("emoji")

    if not emoji or not user:
        return jsonify({"code": 400, "error": "Fehlende Parameter"}), 400

    my_id_row = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")
    if not my_id_row:
        return jsonify({"code": 401, "error": "Ungültiger Benutzer"}), 401
    my_id = my_id_row[0]


    msg_exists = sqlq("SELECT msg_id, id, receiver, conv FROM msg WHERE msg_id = %s", (msg_id,), "one")
    if not msg_exists:
        return jsonify({"code": 404, "error": "Nachricht nicht gefunden"}), 404

    existing = sqlq("SELECT id FROM message_reactions WHERE message_id = %s AND user_id = %s AND emoji = %s",
                    (msg_id, my_id, emoji), "one")

    if existing:
        sqlq("DELETE FROM message_reactions WHERE id = %s", (existing[0],), "none")
    else:
        sqlq("INSERT INTO message_reactions (message_id, user_id, emoji) VALUES (%s, %s, %s)",
             (msg_id, my_id, emoji), "none")

    all_reactions = sqlq("SELECT emoji, user_id FROM message_reactions WHERE message_id = %s", (msg_id,), "all")
    reactions_dict = {}
    if all_reactions:
        for emo, uid in all_reactions:
            if emo not in reactions_dict:
                reactions_dict[emo] = []
            reactions_dict[emo].append(uid)

    payload = {"message_id": msg_id, "reactions": reactions_dict}

    sender_id, recv_id, conv_id = msg_exists[1], msg_exists[2], msg_exists[3]
    if conv_id and conv_id != 0:
        socketio.emit("reaction_update", payload, room=f"group_{conv_id}")
    else:
        ids = sorted([int(sender_id), int(recv_id)])
        socketio.emit("reaction_update", payload, room=f"{ids[0]}_{ids[1]}")
        socketio.emit("reaction_update", payload, room=f"user_{sender_id}")
        socketio.emit("reaction_update", payload, room=f"user_{recv_id}")

    return jsonify({"code": 200, "reactions": reactions_dict})

# ------------------------ group Chat ------------------------
@app.route("/create_group", methods=["POST"])
@app.route('/chat/create_group', methods=['POST'])
def create_group():
    user = session.get("user")
    if not user:
        return redirect("/" + path + "/login")

    data = request.get_json(silent=True) or {}
    group_name = str(data.get("name", "")).strip()
    members = data.get("members", [])

    if not group_name:
        return jsonify({"code": 400, "error": "Gruppenname erforderlich"}), 400

    try:
        my_id = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]
    except Exception:
        return jsonify({"code": 401, "error": "Nicht eingeloggt"}), 401

    try:
        members = [int(m) for m in (members or [])]
    except Exception:
        members = []

    if my_id not in members:
        members.append(my_id)

    members_json = json.dumps(members)
    try:
        sqlq("INSERT INTO `groups` (name, owner_id, members) VALUES (%s, %s, %s)", (group_name, my_id, members_json), "none")
    except Exception as e:
        try:
            sqlq("INSERT INTO `groups` (name, owner, members) VALUES (%s, %s, %s)", (group_name, my_id, members_json), "none")
        except Exception as e2:
            raise

    gid_row = sqlq("SELECT LAST_INSERT_ID()", (), "one")
    gid = gid_row[0] if gid_row else None

    return jsonify({"code": 201, "group": {"id": gid, "name": group_name}}), 201




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
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 300)
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


@app.route('/chat/profile/<path:filename>')
def profile_image(filename):
    profile_dir = os.path.join(app.root_path, 'static', 'img', 'profil')
    os.makedirs(profile_dir, exist_ok=True)

    safe_name = secure_filename(filename)
    if not safe_name.lower().endswith('.png'):
        clean_username = safe_name
        safe_name = safe_name + '.png'
    else:
        clean_username = safe_name[:-4]

    file_path = os.path.join(profile_dir, safe_name)
    if not os.path.exists(file_path):
        img = Image.new('RGB', (200, 200), (99, 102, 241))
        draw = ImageDraw.Draw(img)
        initial = clean_username[0].upper() if clean_username else "?"
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 90)
            draw.text((70, 45), initial, fill=(255, 255, 255), font=font)
        except Exception:
            draw.text((90, 80), initial, fill=(255, 255, 255))
        img.save(file_path)

    response = make_response(send_from_directory(profile_dir, safe_name))
    response.headers['Cache-Control'] = 'public, max-age=86400, must-revalidate'
    return response



@app.route("/logout")
def logout():

    session["auth"] = False
    session["user"] = ""
    session.clear()
    session.pop("user", None)
    return redirect("/" + path + "/login")


# ------------------------ Search ------------------------
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


# ------------------------ Typing Event ------------------------
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


# ------------------------ Read Receipts ------------------------
@socketio.on('mark_read')
def on_mark_read(data):
    my_id = data.get("user_id")
    sender_id = data.get("sender_id")
    if not my_id or not sender_id:
        return

    sqlq("UPDATE msg SET status = 'read' WHERE id = %s AND receiver = %s AND status != 'read'", (sender_id, my_id), "none")

    ids = sorted([int(my_id), int(sender_id)])
    room = f"{ids[0]}_{ids[1]}"
    payload = {"reader_id": my_id, "sender_id": sender_id}
    emit("messages_read", payload, room=room)
    emit("messages_read", payload, room=f"user_{sender_id}")


# ------------------------  message edit & del ------------------------
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


# ------------------------ File Upload Endpoint ------------------------
@app.route("/api/upload", methods=["POST"])
def handle_api_upload():
    if "user" not in session or not session.get("auth"):

        return jsonify({"code": 401, "error": "Nicht authentifiziert"}), 401

    if "file" not in request.files:
        return jsonify({"code": 400, "error": "Keine Datei gesendet"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"code": 400, "error": "Leerer Dateiname"}), 400

    filename = secure_filename(file.filename)
    if not filename:
        filename = f"upload_{int(time.time())}.dat"


    upload_dir = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)

    file_url = f"/chat/static/uploads/{unique_name}"


    ext = os.path.splitext(filename)[1].lower()
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        msg_type = "image"
    elif ext in [".mp3", ".ogg", ".wav", ".m4a", ".webm"]:
        msg_type = "audio"
    else:
        msg_type = "document"

    return jsonify({
        "code": 200,
        "file_url": file_url,
        "filename": filename,
        "msg_type": msg_type
    })


# ------------------------ Group Creation Endpoint ------------------------
@app.route("/api/groups/create", methods=["POST"])
def handle_api_create_group():
    if "user" not in session or not session.get("auth"):

        return jsonify({"code": 401, "error": "Nicht authentifiziert"}), 401

    data = request.get_json(silent=True) or {}
    group_name = data.get("name", "").strip()
    member_ids = data.get("members", [])

    if not group_name:
        return jsonify({"code": 400, "error": "Gruppenname erforderlich"}), 400

    user_name = session.get("user")
    owner_row = sqlq("SELECT id FROM users WHERE username = %s", (user_name,), "one")
    if not owner_row:
        return jsonify({"code": 401, "error": "User nicht gefunden"}), 401

    owner_id = owner_row[0]

    if owner_id not in member_ids:
        member_ids.append(owner_id)

    members_json = json.dumps(member_ids)

    sqlq("INSERT INTO `groups` (name, owner_id, members) VALUES (%s, %s, %s)",
         (group_name, owner_id, members_json), "none")

    group_row = sqlq("SELECT id FROM `groups` WHERE name = %s AND owner_id = %s ORDER BY id DESC LIMIT 1",
                     (group_name, owner_id), "one")

    group_id = group_row[0] if group_row else 0

    return jsonify({"code": 200, "group_id": group_id, "name": group_name})


# ------------------------ Socket.IO Events ------------------------

@socketio.on('join')
def on_join(data):
    print(f"[SOCKET-JOIN] data={data}, session_user={session.get('user')}")
    token = data.get("token")
    my_id = None
    try:
        if token:
            from backend import verify_jwt_token
            my_id, my_name = verify_jwt_token(token)
        else:
            my_name = session.get("user")
            if not my_name:
                print("[SOCKET-JOIN] ABBRUCH: kein session user")
                return
            row = sqlq("SELECT id FROM users WHERE username = %s", (my_name,), "one")
            if row:
                my_id = row[0]

        if my_id is None:
            print("[SOCKET-JOIN] ABBRUCH: my_id ist None")
            return

        group_id = data.get("group_id")
        if group_id:
            try:
                gid = int(group_id)
                join_room(f"group_{gid}")
                print(f"[SOCKET-JOIN] joined group_{gid}")
            except Exception:
                pass
            return

        target_id = data.get("receiver")
        if not target_id:
            print("[SOCKET-JOIN] ABBRUCH: kein receiver in data")
            return

        try:
            try:
                target_user_id = int(target_id)
            except ValueError:
                target_row = sqlq("SELECT id FROM users WHERE username = %s", (str(target_id),), "one")
                if target_row:
                    target_user_id = target_row[0]
                else:
                    print(f"[SOCKET-JOIN] ABBRUCH: receiver '{target_id}' nicht gefunden")
                    return

            ids = sorted([int(my_id), int(target_user_id)])
            room = f"{ids[0]}_{ids[1]}"
            join_room(room)
            print(f"[SOCKET-JOIN] user {my_id} joined room {room}")
        except ValueError:
            pass

    except Exception as e:
        print(f"[SOCKET-JOIN] FEHLER: {e}")


@socketio.on_error_default
def default_error_handler(e):
    pass

@socketio.on('connect')
def on_connect():
    user = session.get("user")
    print(f"[SOCKET-CONNECT] user={user}")
    if user:
        online_users.add(user)
        row = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")
        if row:
            join_room(f"user_{row[0]}")
            print(f"[SOCKET-CONNECT] joined user_{row[0]}")
    else:
        print("[SOCKET-CONNECT] WARNUNG: kein session user!")
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