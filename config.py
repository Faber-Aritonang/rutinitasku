"""
NaraTask AI - Configuration Module
Loads environment variables and provides app configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = Path(os.getenv("WORKSPACE_DIR", "./data/uploads"))
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", "./data/workspace"))
DB_PATH = Path(os.getenv("DATABASE_PATH", "./data/memory.db"))

# Create directories if they don't exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Anthropic Claude Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# NaraRouter Configuration (Fallback)
NARAROUTER_API_KEY = os.getenv("NARAROUTER_API_KEY")
NARAROUTER_BASE_URL = os.getenv("NARAROUTER_BASE_URL", "https://router.bynara.id/v1")
NARAROUTER_MODEL = os.getenv("NARAROUTER_MODEL", "anthropic/claude-sonnet-4-20250514")

# Email Configuration
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Google Calendar Configuration
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")

# Application Settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "7860"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = 30

# LLM Settings
MAX_TOKENS = 4096
TEMPERATURE = 0.7

def validate_config():
    """Validate that required configuration is present."""
    errors = []

    if not ANTHROPIC_API_KEY and not NARAROUTER_API_KEY:
        errors.append("At least one LLM API key is required (ANTHROPIC_API_KEY or NARAROUTER_API_KEY)")

    if EMAIL_ADDRESS and not EMAIL_PASSWORD:
        errors.append("EMAIL_PASSWORD is required when EMAIL_ADDRESS is set")

    return errors

def get_llm_config():
    """Get LLM configuration with fallback logic."""
    return {
        "primary": {
            "provider": "anthropic",
            "api_key": ANTHROPIC_API_KEY,
            "model": ANTHROPIC_MODEL,
            "available": bool(ANTHROPIC_API_KEY)
        },
        "fallback": {
            "provider": "nararouter",
            "api_key": NARAROUTER_API_KEY,
            "base_url": NARAROUTER_BASE_URL,
            "model": NARAROUTER_MODEL,
            "available": bool(NARAROUTER_API_KEY)
        }
    }