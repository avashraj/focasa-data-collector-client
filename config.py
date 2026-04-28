import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("FOCASA_BASE_URL", "http://localhost:8000")
CONFIG_PATH = Path.home() / ".focasa" / "config.json"
