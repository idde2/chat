import mysql.connector
import configparser
import os
from flask import request, session
import bcrypt

socketio = None
def register_socketio(sio):
    global socketio
    socketio = sio

def set_config():
    config = configparser.ConfigParser()
    conf = "config.ini"
    if os.path.isfile(conf):
        config.read(conf)
    else:
        config["DEFAULT"] = {
            "host": "localhost",
            "user": "",
            "password": "",
            "database": "chat",
            "emailpw": "",
            "-------": "------",
            "domain": "eddi.cowdie.com/chat/"
        }
    with open(conf, "w") as f:
        config.write(f)


def get_connection():
    return mysql.connector.connect(
        host=get_conf("host"),
        user=get_conf("user"),
        password=get_conf("password"),
        database=get_conf("database")
    )


config = configparser.ConfigParser()
conf = "config.ini"
if os.path.isfile(conf):
    config.read(conf)

def get_conf(option, fallback=None):
    return config["DEFAULT"].get(option, fallback)


def log(username, name, wert, action):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        user_ip = request.remote_addr
    except Exception:
        user_ip = "GUI"


    cursor.execute(
        "INSERT INTO log (ip,username, name, wert, action) VALUES (%s,%s, %s, %s, %s)",
        (user_ip,username, name, wert, action)
    )

    conn.commit()
    cursor.close()
    conn.close()




def sqlq(query,values,type="all"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query,values)

    if type == "all":
        ans = cursor.fetchall()
    elif type == "one":
        ans = cursor.fetchone()
    elif type == "count":
        ans = cursor.rowcount
    elif type == "none":
        conn.commit()
        ans = ""


    cursor.close()
    conn.close()

    return ans

def auth(username=None,password=None):
    daten = {}

    hash = sqlq("SELECT password FROM users WHERE username = %s",(username,),"one")
    stored_hash = hash[0] if isinstance(hash, tuple) else hash
    if bcrypt.checkpw(password.encode('utf-8'),stored_hash.encode('utf-8')):
        daten["data"] = 1
        daten["code"] = 200
    else:
        daten["data"] = 0
        daten["code"] = 401

    return daten


def background():
    while True:

        socketio.emit("msg", 1)


def send_mail(email,msg):
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    USERNAME = "verifikation.eddi@gmail.com"
    DESTINATION = email
    APP_PASSWORD = get_conf("emailpw")

    msg = MIMEText(msg, "plain")
    msg["Subject"] = "verification"
    msg["From"] = USERNAME
    msg["To"] = DESTINATION

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(USERNAME, APP_PASSWORD)
        server.send_message(msg)

