import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)


def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()
