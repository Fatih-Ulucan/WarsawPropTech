import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from io import StringIO

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

from Scrapers.config import MAX_SCANS_BEFORE_REBOOT
from Scrapers.database import SupabaseManager
from Scrapers.ai_engine import GeminiAnalyzer
from Scrapers.notifier import TelegramBot
from Scrapers.scraper import OtodomSniper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def initialize_system():
    """Initializes environment variables and core system components."""
    BASE_DIR = Path(__file__).resolve().parent.parent
    ENV_PATH = BASE_DIR / ".env"

    try:
        with open(ENV_PATH, "r", encoding="utf-8-sig") as f:
            clean_content = f.read()
        load_dotenv(stream=StringIO(clean_content), override=True)
    except Exception as e:
        logger.error(f"❌ Failed to read .env file: {e}")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    if not SUPABASE_URL or not TELEGRAM_TOKEN:
        logger.error(f"❌ CRITICAL ERROR: Missing environment variables! URL: {SUPABASE_URL}")
        sys.exit()

    db = SupabaseManager(SUPABASE_URL, SUPABASE_KEY)
    ai = GeminiAnalyzer(GEMINI_API_KEY)
    bot = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

    return OtodomSniper(db, ai, bot)

def start_engine():
    """Starts the main scanning engine with auto-restart and anti-zombie logic."""
    logger.info("INFO: System initializing with AI Arbitrage Engine...")

    sniper = initialize_system()

    sniper.notif.send_message("🤖 <b>AI WAKING UP:</b> Connection is OK. Anti-Bot & Arbitrage Engine enabled.")
    sniper.notif.send_message("🚀 <b>System Boot:</b> Warsaw AI PropTech Radar is LIVE with Arbitrage Engine!")

    while True:
        try:
            final_stats = sniper.run_mission()

            sniper.notif.send_daily_report(final_stats)

            if final_stats.get("scanned", 0) > MAX_SCANS_BEFORE_REBOOT:
                logger.warning(f"♻️ {MAX_SCANS_BEFORE_REBOOT}+ ads scanned. Hard restarting to prevent memory leak...")
                sniper.notif.send_message(f"♻️ <b>Auto-Restart:</b> Flushing RAM after {MAX_SCANS_BEFORE_REBOOT/1000}k scans.")
                os.execv(sys.executable, ['python'] + sys.argv)

            logger.info("💤 MISSION COMPLETE: Sleeping for 600 seconds...")
            time.sleep(600)

        except Exception as e:
            logger.error(f"CRITICAL SYSTEM ERROR: {e}")
            try:
                error_msg = str(e)[:200] 
                sniper.notif.send_message(f"🚨 <b>FATAL ENGINE ERROR:</b>\nMain loop crashed. Retrying in 60s.\n\n<i>Reason: {error_msg}</i>")
            except:
                pass
            time.sleep(60)

if __name__ == "__main__":
    start_engine()