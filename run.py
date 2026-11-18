"""One-command launcher and small maintenance utilities for the local app.

Usage:
    python run.py                 # start the web application
    python run.py hash-password   # generate a new admin password hash
    python run.py check           # verify local files / configuration
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

from app.config import BASE_DIR, settings
from app.security import hash_password


def check() -> None:
    print(f"Project root        : {BASE_DIR}")
    print(f"Model file          : {settings.MODEL_PATH}  [{'OK' if settings.MODEL_PATH.exists() else 'MISSING'}]")
    print(f"Class names         : {settings.CLASS_NAMES_PATH}  [{'OK' if settings.CLASS_NAMES_PATH.exists() else 'MISSING'}]")
    print(f"Disease library     : {settings.DISEASES_PATH}  [{'OK' if settings.DISEASES_PATH.exists() else 'MISSING'}]")
    print(f"Database            : {settings.DB_PATH}")
    print(f"Gemini configured   : {bool(settings.GEMINI_API_KEY)} ({settings.GEMINI_MODEL})")
    print(f"Admin configured    : {bool(settings.ADMIN_PASSWORD_HASH)}")
    print(f"Start with          : python run.py")


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "run"
    if command == "check":
        check()
    elif command == "hash-password":
        password = getpass.getpass("New admin password: ")
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            return
        print("\nCopy this into .env as ADMIN_PASSWORD_HASH:")
        print(hash_password(password))
    elif command == "run":
        import uvicorn

        print(f"Starting {settings.APP_NAME} at http://{settings.HOST}:{settings.PORT}")
        uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
    else:
        print(f"Unknown command: {command}")
        print("Use: python run.py [run|check|hash-password]")


if __name__ == "__main__":
    main()
