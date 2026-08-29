#!/usr/bin/env python3
"""
Send Moodle messages — single or batch from users.db.

Usage:
  # Single — by user ID
  python send.py single 422 --message "Olá!"

  # Batch — todos os utilizadores da DB
  python send.py batch --message "Olá {name}!"
  python send.py batch --message "Olá {name}!" --limit 50 --delay 2 --dry-run

  # Batch — IDs específicos (comma-separated)
  python send.py batch --ids 422,380,163 --message "Olá!"
"""

import argparse
import os
import sqlite3
import sys
import time

from dotenv import load_dotenv

from client import MoodleClient

load_dotenv()

DB_PATH = "users.db"


def get_credentials() -> tuple[str, str]:
    username = os.getenv("MOODLE_USER") or input("Username: ").strip()
    password = os.getenv("MOODLE_PASS") or input("Password: ").strip()
    return username, password


def load_from_db(ids: list[int] | None = None, limit: int | None = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    if ids:
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT id, fullname FROM users WHERE id IN ({placeholders})", ids
        ).fetchall()
    else:
        query = "SELECT id, fullname FROM users ORDER BY id"
        if limit:
            query += f" LIMIT {limit}"
        rows = conn.execute(query).fetchall()
    conn.close()
    return [{"userid": r[0], "name": r[1]} for r in rows]


def do_send(client: MoodleClient, recipients: list[dict], message: str, delay: float, dry_run: bool) -> None:
    total = len(recipients)
    sent = errors = 0

    for i, r in enumerate(recipients, 1):
        uid  = r["userid"]
        name = r["name"]
        first_name = name.split()[0]
        msg  = message.replace("{name}", first_name).replace("{fullname}", name)

        print(f"[{i:4d}/{total}] {name} (id={uid})", end="  ")

        if dry_run:
            print("[DRY RUN]")
            continue

        try:
            resp = client.send_message(uid, msg)
            print(f"✓ msg_id={resp.get('id')}")
            sent += 1
        except Exception as e:
            print(f"✗ {e}")
            errors += 1

        if i < total:
            time.sleep(delay)

    print(f"\nDone — sent={sent} errors={errors}" + (" [DRY RUN]" if dry_run else ""))


def cmd_single(args, client):
    msg = args.message
    if not msg:
        print("Enter message (Ctrl+D to finish):")
        msg = sys.stdin.read().strip()

    # Resolve name from DB if available
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT fullname FROM users WHERE id=?", (args.userid,)).fetchone()
    conn.close()
    name = row[0] if row else str(args.userid)

    print(f"→ {name} (id={args.userid})")
    if args.dry_run:
        print(f"[DRY RUN] msg: {msg!r}")
        return

    resp = client.send_message(args.userid, msg)
    print(f"✓ sent — msg_id={resp.get('id')}")


def cmd_batch(args, client):
    ids = [int(x) for x in args.ids.split(",")] if args.ids else None
    recipients = load_from_db(ids=ids, limit=args.limit)

    if not recipients:
        print("No recipients found.")
        sys.exit(1)

    msg = args.message
    if not msg and args.message_file:
        with open(args.message_file, encoding="utf-8") as f:
            msg = f.read().strip()
    if not msg:
        print("Enter message (Ctrl+D to finish):")
        msg = sys.stdin.read().strip()

    print(f"{len(recipients)} recipients")
    print(f"Preview: {msg[:120]!r}\n")

    if not args.dry_run:
        confirm = input(f"Send to {len(recipients)} users? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)

    do_send(client, recipients, msg, delay=args.delay, dry_run=args.dry_run)


def main():
    parser = argparse.ArgumentParser(description="Send Moodle messages")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # single
    p1 = sub.add_parser("single", help="Send to one user by ID")
    p1.add_argument("userid", type=int)
    p1.add_argument("--message", "-m")
    p1.add_argument("--dry-run", action="store_true")

    # batch
    p2 = sub.add_parser("batch", help="Send to multiple users from DB")
    p2.add_argument("--ids", help="Comma-separated user IDs (default: all in DB)")
    p2.add_argument("--limit", type=int, help="Max recipients")
    p2.add_argument("--message", "-m")
    p2.add_argument("--message-file", help="Read message from file")
    p2.add_argument("--delay", type=float, default=1.0, help="Seconds between sends (default: 1)")
    p2.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    client = MoodleClient()
    print("Logging in…")
    client.login(*get_credentials())
    print(f"Logged in as userid={client.userid}\n")

    {"single": cmd_single, "batch": cmd_batch}[args.cmd](args, client)


if __name__ == "__main__":
    main()
