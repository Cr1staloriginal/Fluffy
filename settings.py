"""Backward-compatible settings module.

Importing this module does not abort the process when DISCORD_TOKEN is missing;
main.py validates the token when the application starts.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/database.db")
