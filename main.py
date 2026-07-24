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

domain = str(get_conf("domain"))
path = str(get_conf("path"))

app = Flask(__name__)

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "flask_session")
app.config["SECRET_KEY"] = "cdejgkhjkaltkhjdmhtrjklejdklrklgf665gd4f35g735g735g7d57df4ges!7357g74g54th ggfjsdfzjkgfkjgfwerhjukvrtht"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=10)
Session(app)

app.register_blueprint(back, url_prefix="/api")

socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")


app.secret_key = "UDCuJKjkHJKFHKHE$(O(OVE(OWKLJJHjkHVRFHJKHGVRZEGHzV SRGFIUIOVHJKRJKJKFJR"
app.config['SECRET_KEY'] = 'uvdhvmdmhuhroiubvioevhevihwoioruiouicbjkw88rtvcn jkamYcjkvmdf'
register_socketio(socketio)




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
    raw_kontacts = json.loads(sqlq("SELECT kontacts FROM users WHERE username = %s", (user,), "one")[0])
    kontacts = []
    for kotankt in raw_kontacts:
        raw = sqlq("SELECT username FROM users WHERE id = %s", (kotankt,), "one")
        raw = raw[0] if isinstance(raw, tuple) else raw
        kontacts.append(raw) if raw != None else None


    return render_template("index.html",kontacts=kontacts)

@app.route("/chat/<receiver>")
def chat(receiver):
    user = session["user"] if session.get("user") else ""

    id_u = sqlq("SELECT id FROM users WHERE username = %s", (user,), "one")[0]
    id_r = sqlq("SELECT id FROM users WHERE username = %s", (receiver,), "one")[0]

    msg = sqlq("SELECT id,content,time FROM msg WHERE id = %s AND receiver = %s OR id= %s AND receiver = %s ORDER BY time ASC", (id_u,id_r,id_r,id_u),"all")


    return render_template("chat.html", user=id_u, receiver=id_r,receiver_name=receiver, msg=msg)

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
        kontakte = ast.literal_eval( sqlq("SELECT kontacts FROM users WHERE id = %s",(id_u,),"one")[0] )
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

    sqlq("INSERT INTO msg (id, receiver, content) VALUES (%s, %s, %s)", (id,receiver,msg),"none")

    socketio.emit("msg", {"content": msg, "sender": user, "sender_id": id}, room=room)



    return redirect("/" + path + "/chat/" + receiver_name + "")


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
            draw.text((400, 450), name, fill=(255, 0, 0), size=100)
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
                draw.text((400, 450), user, fill=(255, 0, 0), font_size=100)
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


@socketio.on('join')
def on_join(data):
    # Unterstützt Web-Sessions UND JWT-Token (für Android-App)
    token = data.get("token")
    my_id = None
    try:
        if token:
            from backend import verify_jwt_token
            my_id, my_name = verify_jwt_token(token)
        else:
            # Web-Session Fallback
            my_name = session.get("user")
            if not my_name:
                return
            row = sqlq("SELECT id FROM users WHERE username = %s", (my_name,), "one")
            if row:
                my_id = row[0]

        if my_id is None:
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
    pass

@socketio.on('disconnect')
def on_disconnect():
    pass


if __name__ == "__main__":

    set_config()
    #socketio.start_background_task(background)
    socketio.run(
        app,
        host="0.0.0.0",
        port=7000,
        debug=True,
        allow_unsafe_werkzeug=True
    )

#         ssl_context=("https/cert.pem", "https/key.pem"),
