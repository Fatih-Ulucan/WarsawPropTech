import os
import time
import requests
import logging
import re
import random
import sys
from io import StringIO
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

if not SUPABASE_URL or not TELEGRAM_TOKEN:
    logger.error(f"❌ CRITICAL ERROR: Missing environment variables! URL: {SUPABASE_URL}")
    sys.exit()


stats = {"scanned": 0, "added": 0, "bargains": 0, "start_time": datetime.now()}

LOCATION_MAP = {
    'Mokotów': 1, 'Praga-Południe': 2, 'Ursynów': 3, 'Wola': 4,
    'Białołęka': 5, 'Bielany': 6, 'Bemowo': 7, 'Targówek': 8,
    'Śródmieście': 9, 'Wawer': 10, 'Ochota': 11, 'Ursus': 12,
    'Praga-Północ': 13, 'Włochy': 14, 'Wilanów': 15, 'Wesoła': 16,
    'Żoliborz': 17, 'Rembertów': 18
}

SCRAPE_TARGETS = [
    {"url_part": "sprzedaz/mieszkanie", "trans_id": 1, "type_id": 1, "label": "🏠 APARTMENT SALE"},
    {"url_part": "wynajem/mieszkanie", "trans_id": 2, "type_id": 1, "label": "🔑 APARTMENT RENT"},
    {"url_part": "sprzedaz/kawalerka", "trans_id": 1, "type_id": 1, "label": "🛋️ STUDIO SALE"},
    {"url_part": "wynajem/kawalerka", "trans_id": 2, "type_id": 1, "label": "🛌 STUDIO RENT"},
    {"url_part": "sprzedaz/dom", "trans_id": 1, "type_id": 2, "label": "🏡 HOUSE SALE"},
    {"url_part": "wynajem/dom", "trans_id": 2, "type_id": 2, "label": "🏠 HOUSE RENT"},
    {"url_part": "sprzedaz/lokal", "trans_id": 1, "type_id": 3, "label": "🏢 COMMERCIAL SALE"},
    {"url_part": "wynajem/lokal", "trans_id": 2, "type_id": 3, "label": "🏬 COMMERCIAL RENT"},
    {"url_part": "sprzedaz/garaz", "trans_id": 1, "type_id": 4, "label": "🚗 GARAGE SALE"},
    {"url_part": "wynajem/garaz", "trans_id": 2, "type_id": 4, "label": "🅿️ GARAGE RENT"},
    {"url_part": "sprzedaz/dzialka", "trans_id": 1, "type_id": 5, "label": "🌳 PLOT SALE"}
]

SEEN_URLS = set()

def get_market_average():
    logger.info("🧠 AI ENGINE: Fetching real-time market averages from Supabase...")
    clean_url = SUPABASE_URL.strip("/")
    table_url = f"{clean_url}/rest/v1/district_market_stats"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        response = requests.get(table_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            market_dict = {}
            for row in data:
                if row.get('avg_price_per_sqm'):
                    market_dict[(row['loc_id'], row['trans_id'], row['type_id'])] = row['avg_price_per_sqm']
            logger.info(f"✅ AI ENGINE: Successfully loaded {len(market_dict)} market categories!")
            return market_dict
    except Exception as e:
        logger.error(f"❌ AI ENGINE ERROR: Failed to fetch market stats: {e}")
    return{}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
        if response.status_code != 200:
            logger.error(f"❌ TELEGRAM API ERROR: {response.text}")
        else:
            logger.info("✅ TELEGRAM MESSAGE SENT SUCCESSFULLY!")
    except Exception as e:
        logger.error(f"❌ Telegram Network Failed: {e}")

def find_loc_id(location_text):
    if not location_text: return None
    for district, loc_id in LOCATION_MAP.items():
        if district in location_text: return loc_id
    return None

def save_to_supabase(data):
    clean_url = SUPABASE_URL.strip("/")
    table_url = f"{clean_url}/rest/v1/listings"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(table_url, json=data, headers=headers, timeout=10)
            return response.status_code
        except Exception as e:
            time.sleep(2)
    return None

def test_scraper():
    global stats
    
    market_stats = get_market_average()
    
    logger.info("INFO: Bot is waking up and launching the browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        logger.info("INFO: Navigating to Otodom...")
        page.goto("https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/mazowieckie/warszawa/warszawa/warszawa")

        try:
            cookie_button = page.locator("#onetrust-accept-btn-handler")
            cookie_button.wait_for(timeout=5000)
            cookie_button.click()
            logger.info("SUCCESS: Cookie banner destroyed!")
        except: pass

        for target in SCRAPE_TARGETS:
            logger.info(f"\n🚀 MISSION: {target['label']}")

            for page_num in range(1, 101):
                target_url = f"https://www.otodom.pl/pl/wyniki/{target['url_part']}/mazowieckie/warszawa/warszawa/warszawa?direction=ASC&sorting=PRICE&page={page_num}"
                page.goto(target_url)

                try:
                    try:
                        page.wait_for_selector('[data-sentry-component="AdvertCard"]', timeout=10000)
                    except:
                        logger.info(f"🛑 END OF CATEGORY: {target['label']}")
                        break

                    for _ in range(3):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1.5)

                    all_listing = page.locator('[data-sentry-component="AdvertCard"]').all()

                    for index, listing in enumerate(all_listing):
                        stats["scanned"] += 1
                        try:
                            raw_url = listing.locator('[data-cy="listing-item-link"]').first.get_attribute('href')
                            if not raw_url: continue
                            full_url = raw_url if raw_url.startswith("http") else f"https://www.otodom.pl{raw_url.replace('/hpr','')}"

                            if full_url in SEEN_URLS:
                                logger.info(f"[{index + 1}] ⏭️ SKIPPED")
                                continue

                            card_text = listing.inner_text()
                            title = listing.locator('[data-cy="listing-item-link"]').first.inner_text()
                            location = listing.locator('[data-sentry-component="Address"]').first.inner_text()
                            raw_price = listing.locator('[data-sentry-element="MainPrice"]').first.inner_text()

                            try:
                                clean_price = int(re.sub(r'[^\d]', '', raw_price))
                            except: clean_price = 0

                            sqm_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m²', card_text)
                            sqm = float(sqm_match.group(1).replace(',', '.')) if sqm_match else None

                            rooms_match = re.search(r'(\d+)\s*pok', card_text)
                            rooms = int(rooms_match.group(1)) if rooms_match else None

                            price_per_sqm = round(clean_price / sqm, 2) if sqm and sqm > 0 else None
                            matched_loc_id = find_loc_id(location)

                            display_p_m2 = f"{price_per_sqm:,.2f}".replace(",", " ") if price_per_sqm else "None"
                            logger.info(f"[P:{page_num} - {index + 1}] 💰 {clean_price:,} PLN | 📏 {sqm}m² | 📊 {display_p_m2} PLN/m² | 🚪 {rooms} Rooms | 📍 ID: {matched_loc_id}")

                            payload = {
                                "price_pln": clean_price, "url_link": full_url, "source_platform": "Otodom",
                                "is_active": True, "trans_id": target['trans_id'], "type_id": target['type_id'],
                                "sqm": sqm, "rooms": rooms, "price_per_sqm": price_per_sqm, "loc_id": matched_loc_id
                            }

                            db_status = save_to_supabase(payload)

                            if db_status in [200, 201, 204]:
                                stats["added"] += 1
                                SEEN_URLS.add(full_url)
                                logger.info("      ✅ DB SYNC SUCCESS")

                                is_bargain = False
                                profit_margin = 0
                                avg_sqm_price = 0

                                if matched_loc_id and price_per_sqm:
                                    avg_sqm_price = market_stats.get((matched_loc_id, target['trans_id'], target['type_id']))

                                    if avg_sqm_price and avg_sqm_price > 0:
                                        if price_per_sqm <= (avg_sqm_price * 0.85):
                                            is_bargain = True
                                            profit_margin = round(((avg_sqm_price - price_per_sqm) / avg_sqm_price) * 100, 1)

                                if is_bargain:
                                    stats["bargains"] += 1
                                    alert = f"🤖 <b>AI DEAL DETECTED!</b> 💎\n" \
                                            f"━━━━━━━━━━━━━━━━━━━━\n" \
                                            f"📍 <b>District:</b> {location}\n" \
                                            f"🏢 <b>Category:</b> {target['label']}\n" \
                                            f"💰 <b>Total Price:</b> {clean_price:,} PLN\n" \
                                            f"📐 <b>Size:</b> {sqm} m²\n" \
                                            f"📊 <b>This Listing:</b> {price_per_sqm:,.0f} PLN/m²\n" \
                                            f"📈 <b>District Avg:</b> {avg_sqm_price:,.0f} PLN/m²\n" \
                                            f"🔥 <b>PROFIT MARGIN:</b> %{profit_margin} (Under Market)\n" \
                                            f"━━━━━━━━━━━━━━━━━━━━\n" \
                                            f"🔗 <a href='{full_url}'>View Listing</a>"
                                    send_telegram(alert)

                            elif db_status == 409:
                                SEEN_URLS.add(full_url)

                        except Exception: continue

                except Exception as e:
                    logger.error(f"ERROR: Page {page_num} failed: {e}")

                time.sleep(random.uniform(3, 7))

        browser.close()

def send_daily_report():
    uptime = datetime.now() - stats['start_time']
    report = f"📊 <b>WARSAW MARKET REPORT</b>\n" \
             f"━━━━━━━━━━━━━━━━━━━━\n" \
             f"⏱ <b>Uptime:</b> {str(uptime).split('.')[0]}\n" \
             f"🧐 <b>Ads Scanned:</b> {stats['scanned']}\n" \
             f"✅ <b>New Entries:</b> {stats['added']}\n" \
             f"🔥 <b>Bargains Found:</b> {stats['bargains']}\n" \
             f"━━━━━━━━━━━━━━━━━━━━"
    send_telegram(report)
    for k in ["scanned", "added", "bargains"]: stats[k] = 0

def start_endless_bot():
    send_telegram("🚀 <b>System Boot:</b> Warsaw PropTech Radar is LIVE!")
    while True:
        try:
            test_scraper()
            send_daily_report()
            time.sleep(600)
        except Exception as e:
            logger.error(f"CRITICAL: {e}")
            time.sleep(60)

if __name__ == "__main__":
    logger.info("INFO: System initializing...")
    send_telegram("🔔 <b>TEST MESSAGE:</b> Connection is OK. Hunting for bargains now!")
    start_endless_bot()