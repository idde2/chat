#!/usr/bin/env python3
"""DB-Migration: status, conv, file_url, edited in msg; groups Tabelle & Spalte in users."""
import sys
import mysql.connector
from api import get_connection, get_conf

try:
    conn = get_connection()
    cur = conn.cursor()
    db_name = get_conf("database", "chat")

    # 1) groups-Tabelle erstellen falls nicht vorhanden
    cur.execute("""
        CREATE TABLE IF NOT EXISTS `groups` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL DEFAULT '',
            owner_id INT NOT NULL DEFAULT 0,
            members TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[OK] Tabelle `groups` geprüft/erstellt.")

    # 1b) Fehlende Spalten in vorhandener groups-Tabelle nachträglich ergänzen
    for col, col_def in [
        ("name",       "VARCHAR(255) NOT NULL DEFAULT ''"),
        ("owner_id",   "INT NOT NULL DEFAULT 0"),
        ("members",    "TEXT NULL"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
    ]:
        cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'groups' AND COLUMN_NAME = %s
        """, (db_name, col))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE `groups` ADD COLUMN `{col}` {col_def}")
            print(f"[OK] groups.{col} hinzugefügt")
        else:
            print(f"[~] groups.{col} existiert bereits")

    # 2) status-Spalte in msg
    cur.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = 'status'
    """, (db_name,))
    if not cur.fetchone():
        cur.execute("ALTER TABLE msg ADD COLUMN status VARCHAR(20) DEFAULT 'sent' NOT NULL")
        print("[OK] msg.status hinzugefügt")
    else:
        print("[~] msg.status existiert bereits")

    # 3) groups-Spalte in users (wenn nicht vorhanden)
    cur.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'groups'
    """, (db_name,))
    if not cur.fetchone():
        cur.execute("ALTER TABLE users ADD COLUMN `groups` TEXT NULL")
        print("[OK] users.groups hinzugefügt")
    else:
        print("[~] users.groups existiert bereits")

    # 4) conv-Spalte in msg (für Gruppen-Nachrichten)
    cur.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = 'conv'
    """, (db_name,))
    if not cur.fetchone():
        cur.execute("ALTER TABLE msg ADD COLUMN conv INT NULL")
        print("[OK] msg.conv hinzugefügt")
    else:
        print("[~] msg.conv existiert bereits")

    # 5) edited-Spalte in msg
    cur.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = 'edited'
    """, (db_name,))
    if not cur.fetchone():
        cur.execute("ALTER TABLE msg ADD COLUMN edited TINYINT DEFAULT 0")
        print("[OK] msg.edited hinzugefügt")
    else:
        print("[~] msg.edited existiert bereits")

    # 6) file_url & file_type Spalten in msg
    cur.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = 'file_url'
    """, (db_name,))
    if not cur.fetchone():
        cur.execute("ALTER TABLE msg ADD COLUMN file_url VARCHAR(255) NULL")
        cur.execute("ALTER TABLE msg ADD COLUMN file_type VARCHAR(50) NULL")
        print("[OK] msg.file_url und msg.file_type hinzugefügt")
    else:
        print("[~] msg.file_url existiert bereits")

    conn.commit()
    print("Migration erfolgreich abgeschlossen.")

except Exception as e:
    print(f"FEHLER bei Migration: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    try:
        cur.close()
        conn.close()
    except Exception:
        pass