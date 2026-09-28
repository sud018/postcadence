"""Every file location in one place, so no module hard-codes paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_FILE = DATA_DIR / "config.json"
STATE_FILE = DATA_DIR / "state.json"
TOPICS_FILE = DATA_DIR / "topics.json"
DRAFTS_FILE = DATA_DIR / "drafts.json"
