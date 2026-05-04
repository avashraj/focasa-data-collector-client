import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("FOCASA_BASE_URL", "https://api.focasa.xyz")
CONFIG_PATH = Path.home() / ".focasa" / "config.json"
