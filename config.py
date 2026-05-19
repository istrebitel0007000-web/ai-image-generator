import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Directories ────────────────────────────────────────────────────────
OUTPUT_DIR   = Path("generated_images")
UPSCALE_DIR  = Path("upscaled_images")
WATERMARK_DIR = Path("watermarked_images")

for _d in [OUTPUT_DIR, UPSCALE_DIR, WATERMARK_DIR]:
    _d.mkdir(exist_ok=True)

# ── Data files ─────────────────────────────────────────────────────────
USERS_FILE    = Path("users.json")
SHARES_FILE   = Path("shares.json")
STATS_FILE    = Path("stats.json")
API_KEYS_FILE = Path("api_keys.json")
GUEST_FILE    = Path("guest_history.json")

# ── App config ─────────────────────────────────────────────────────────
SECRET_KEY       = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_USERNAME   = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD   = os.getenv("ADMIN_PASSWORD", "admin123")
DAILY_FREE_LIMIT = int(os.getenv("DAILY_FREE_LIMIT", "10"))
DAILY_PRO_LIMIT  = int(os.getenv("DAILY_PRO_LIMIT", "100"))

# ── Google OAuth ───────────────────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "")
