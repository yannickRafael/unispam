#!/usr/bin/env python3
"""
Enumerate all Moodle users via message search API and store in SQLite.

Usage:
    python enumerate.py
    python enumerate.py --db users.db --delay 0.3
"""

import argparse
import os
import sqlite3
import time

from dotenv import load_dotenv

from client import MoodleClient

load_dotenv()

# Substring search — single chars cover almost everyone.
# Portuguese alphabet + common accented first letters.
SEARCH_CHARS = list("abcdefghijklmnopqrstuvwxyz") + [
    "á", "â", "ã", "à", "é", "ê", "í", "ó", "ô", "õ", "ú", "ü", "ç",
]

PAGE_SIZE = 51
PAGE_STEP = 50  # overlap by 1 to avoid missing edge cases


def init_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY,
            fullname    TEXT NOT NULL,
            profileurl  TEXT
        )
    """)
    conn.commit()
    return conn


def count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def upsert(conn: sqlite3.Connection, users: list[dict]) -> int:
    new = 0
    for u in users:
        cur = conn.execute(
            "INSERT OR IGNORE INTO users (id, fullname, profileurl) VALUES (?, ?, ?)",
            (u["id"], u["fullname"], u.get("profileurl", "")),
        )
        new += cur.rowcount
    conn.commit()
    return new


def enumerate_users(client: MoodleClient, db_path: str, delay: float) -> None:
    conn = init_db(db_path)
    print(f"DB: {db_path} | starting with {count(conn)} users\n")

    for char in SEARCH_CHARS:
        limitfrom = 0
        char_new = 0

        while True:
            try:
                users = client.search_users(char, limitnum=PAGE_SIZE, limitfrom=limitfrom)
            except Exception as e:
                print(f"  [{char}] offset={limitfrom} ERROR: {e}")
                break

            new = upsert(conn, users)
            char_new += new
            total = count(conn)
            print(f"  [{char}] offset={limitfrom:4d} → {len(users):2d} returned, {new:2d} new | total={total}")

            if len(users) < PAGE_SIZE:
                break

            limitfrom += PAGE_STEP
            time.sleep(delay)

        print(f"  [{char}] done — {char_new} new users\n")
        time.sleep(delay)

    final = count(conn)
    print(f"Enumeration complete. Total users in DB: {final}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Enumerate all Moodle users → SQLite")
    parser.add_argument("--db", default="users.db", help="SQLite output file (default: users.db)")
    parser.add_argument("--delay", type=float, default=0.3, help="Seconds between requests (default: 0.3)")
    args = parser.parse_args()

    username = os.getenv("MOODLE_USER") or input("Username: ").strip()
    password = os.getenv("MOODLE_PASS") or input("Password: ").strip()

    client = MoodleClient()
    print("Logging in…")
    client.login(username, password)
    print(f"Logged in as userid={client.userid}\n")

    enumerate_users(client, args.db, args.delay)


if __name__ == "__main__":
    main()
