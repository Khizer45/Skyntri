"""
Small admin command-line tool.

    python -m app.cli make-admin you@example.com
    python -m app.cli remove-admin you@example.com
    python -m app.cli list-admins

With Docker:
    docker compose exec backend python -m app.cli make-admin you@example.com
"""

from __future__ import annotations

import argparse
import sys

from app.db.database import SessionLocal
from app.db.models import User


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("make-admin", "remove-admin"):
        cmd = sub.add_parser(name)
        cmd.add_argument("email")
    sub.add_parser("list-admins")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        if args.command == "list-admins":
            admins = db.query(User).filter(User.role == "admin").all()
            for user in admins:
                print(f"{user.email}  ({user.full_name})")
            if not admins:
                print("No admins yet.")
            return 0

        email = args.email.strip().lower()
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"No account with e-mail {email}. Sign up in the app first, then run this again.")
            return 1

        user.role = "admin" if args.command == "make-admin" else "user"
        db.commit()
        print(f"{email} is now {'an admin' if user.role == 'admin' else 'a normal user'}. "
              "Log out and log in again in the browser.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
