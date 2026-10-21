"""Centralized optional configuration values.

The bot's primary settings are environment variables documented in .env.example.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/database.db")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
GUILD_ID = int(os.getenv("GUILD_ID", "0") or 0)
