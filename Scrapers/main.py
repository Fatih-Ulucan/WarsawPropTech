import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from io import StringIO
from datetime import datetime, timedelta
from Scrapers.config import MAX_SCANS_BEFORE_REBOOT
from Scrapers.database import SupabaseManager
from Scrapers.ai_engine import GroqProptechAI
from Scrapers.notifier import TelegramBot, EmailManager
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
    BASE_DIR = Path(__file__).resolve().parent.parent
    ENV_PATH = BASE_DIR / ".env"

    try:
        if ENV_PATH.exists():
            with open(ENV_PATH, "r", encoding="utf-8-sig") as f:
                clean_content = f.read()
            load_dotenv(stream=StringIO(clean_content), override=True)
    except Exception as e:
        logger.error(f"Failed to read .env file: {e}")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    if not SUPABASE_URL or not TELEGRAM_TOKEN:
        logger.error("CRITICAL ERROR: Missing environment variables!")
        sys.exit()

    db = SupabaseManager(SUPABASE_URL, SUPABASE_KEY)
    ai = GroqProptechAI(GROQ_API_KEY)
    bot = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    email_manager = EmailManager()

    return OtodomSniper(db, ai, bot), email_manager

def start_engine():
    logger.info("System initializing with AI Arbitrage Engine...")

    sniper, email_manager = initialize_system()

    sniper.notif.send_message("🤖 <b>AI WAKING UP:</b> Connection is OK. Anti-Bot & Arbitrage Engine enabled.")
    sniper.notif.send_message("🚀 <b>System Boot:</b> Warsaw AI PropTech Radar is LIVE!")

    while True:
        try:
            start_time = datetime.now()
            final_stats = sniper.run_mission()
            final_stats['start_time'] = start_time

            sniper.notif.send_mission_report()

            subscribers = sniper.db.get_subscribers()
            if subscribers:
                report_lines = [
                    f"Ads Scanned: {final_stats['scanned']}",
                    f"New Entries: {final_stats['added']}",
                    f"AI Deals Found: {final_stats['bargains']}",
                    f"Price Drops Detected: {final_stats['price_drops']}"
                ]
                email_html = email_manager.create_html_template("Market Summary Report", report_lines, EXPANDER_LINK)
                for sub in subscribers:
                    email_manager.send_user_email(sub['email'], "Warsaw Market Daily Summary", email_html)

            if final_stats.get("scanned", 0) > MAX_SCANS_BEFORE_REBOOT:
                logger.warning(f"Hard restarting after {MAX_SCANS_BEFORE_REBOOT} scans...")
                sniper.notif.send_message("♻️ <b>Auto-Restart:</b> Flushing RAM.")
                os.execv(sys.executable, ['python'] + sys.argv)

            logger.info("MISSION COMPLETE: Sleeping for 600 seconds...")
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