#!/usr/bin/env python3
"""DB-Migration: status, conv, file_url, edited in msg; groups Tabelle & Spalte in users."""
import sys
import mysql.connector
from api import get_connection, get_conf

def run_migrations():
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

        # 1c) msg_id (AUTO_INCREMENT PRIMARY KEY) in msg
        cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = 'msg_id'
        """, (db_name,))
        if not cur.fetchone():
            cur.execute("ALTER TABLE `msg` ADD COLUMN `msg_id` INT AUTO_INCREMENT PRIMARY KEY FIRST")

        # 2) status & medien-Spalten in msg
        for col, col_def in [
            ("status", "VARCHAR(20) DEFAULT 'sent'"),
            ("msg_type", "VARCHAR(20) DEFAULT 'text'"),
            ("file_url", "VARCHAR(500) NULL"),
            ("is_encrypted", "TINYINT(1) DEFAULT 0")
        ]:
            cur.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = %s
            """, (db_name, col))
            if not cur.fetchone():
                cur.execute(f"ALTER TABLE `msg` ADD COLUMN `{col}` {col_def}")

        # 3) group_messages Tabelle erstellen
        cur.execute("""
            CREATE TABLE IF NOT EXISTS `group_messages` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                group_id INT NOT NULL,
                sender_id INT NOT NULL,
                message TEXT,
                msg_type VARCHAR(20) DEFAULT 'text',
                file_url VARCHAR(500) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3) groups-Spalte in users (wenn nicht vorhanden)
        cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'groups'
        """, (db_name,))
        if not cur.fetchone():
            cur.execute("ALTER TABLE users ADD COLUMN `groups` TEXT NULL")

        # 4) conv-Spalte in msg (für Gruppen-Nachrichten)
        cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = 'conv'
        """, (db_name,))
        if not cur.fetchone():
            cur.execute("ALTER TABLE msg ADD COLUMN conv INT NULL")

        # 5) edited-Spalte in msg
        cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = 'edited'
        """, (db_name,))
        if not cur.fetchone():
            cur.execute("ALTER TABLE msg ADD COLUMN edited TINYINT DEFAULT 0")

        # 6) file_url & file_type Spalten in msg
        cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = 'file_url'
        """, (db_name,))
        if not cur.fetchone():
            cur.execute("ALTER TABLE msg ADD COLUMN file_url VARCHAR(255) NULL")
            cur.execute("ALTER TABLE msg ADD COLUMN file_type VARCHAR(50) NULL")

        # 7) message_reactions Tabelle für Emoji-Reaktionen
        cur.execute("""
            CREATE TABLE IF NOT EXISTS `message_reactions` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id INT NOT NULL,
                user_id INT NOT NULL,
                emoji VARCHAR(32) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY `unique_user_reaction` (`message_id`, `user_id`, `emoji`)
            )
        """)

        # 8) reply_to_id Spalte in msg (für Antwort/Zitat-Feature)
        cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'msg' AND COLUMN_NAME = 'reply_to_id'
        """, (db_name,))
        if not cur.fetchone():
            cur.execute("ALTER TABLE `msg` ADD COLUMN `reply_to_id` INT NULL DEFAULT NULL")

        conn.commit()
    except Exception as e:
        print(f"FEHLER bei Migration: {e}", file=sys.stderr)
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    run_migrations()