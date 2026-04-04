import os
import time
import requests
import logging
import re
import random
import sys
import unicodedata
import urllib.parse
from io import StringIO
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import google.generativeai as genai

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not SUPABASE_URL or not TELEGRAM_TOKEN:
    logger.error(f"❌ CRITICAL ERROR: Missing environment variables! URL: {SUPABASE_URL}")
    sys.exit()

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("⚠️ GEMINI_API_KEY not found. AI Analysis will be skipped.")

last_fetch_time = 0
CACHE_TTL = 600
market_stats_cache = {}

stats = {"scanned": 0, "added": 0, "bargains": 0, "price_drops": 0, "start_time": datetime.now()}

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
    {"url_part": "wynajem/lokal", "trans_id": 2, "type_id": 3, "label": "🏬 COMMERCIAL RENT"}
]

def analyze_description_with_ai(description):

    if not GEMINI_API_KEY:
        return "AI Analysis unavailable (No Key)."

    try:
        time.sleep(2)
        model = genai.GenerativeModel('models/gemini-flash-lite-latest')

        prompt = f"""
        Analyze this Polish real estate description. Provide 3 short bullet points in English:
        1. Condition (Renovated? New? Needs work?)
        2. Seller Motivation (Is it urgent? Any room for negotiation?)
        3. Risks/Notes (Legal issues, lack of elevator, or noisy area?)

        Description:
        {description[:1500]}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "AI Analysis failed to generate for this listing."

def normalize(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower()

def get_market_average():
    global last_fetch_time, market_stats_cache

    if time.time() - last_fetch_time < CACHE_TTL and market_stats_cache:
        logger.info("⚡ CACHE: Using saved market data (No API call needed).")
        return market_stats_cache

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
            market_stats_cache = market_dict
            last_fetch_time = time.time()
            logger.info(f"✅ AI ENGINE: Successfully loaded {len(market_dict)} market categories!")
            return market_dict
    except Exception as e:
        logger.error(f"❌ AI ENGINE ERROR: Failed to fetch market stats: {e}")
    return market_stats_cache

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
    normalized_location = normalize(location_text)
    for district, loc_id in LOCATION_MAP.items():
        if normalize(district) in normalized_location:
            return loc_id
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

def log_price_history(property_id, price_pln):
    if not property_id or not price_pln: return
    clean_url = SUPABASE_URL.strip("/")
    table_url = f"{clean_url}/rest/v1/price_history"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    try: requests.post(table_url, json={"property_id": property_id, "price_pln": price_pln}, headers=headers, timeout=5)
    except: pass

def check_and_update_price(property_id, current_price, price_per_sqm, full_url, location, sqm, rooms, card_text, matched_loc_id, target, market_stats, agency_id):
    global stats
    if not current_price: return
    clean_url = SUPABASE_URL.strip("/")
    safe_url = urllib.parse.quote(full_url)

    get_url = f"{clean_url}/rest/v1/listings?url_link=eq.{safe_url}&select=id,price_pln,property_id,agency_id"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

    try:
        resp = requests.get(get_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                db_price = data[0].get('price_pln')
                row_id = data[0].get('id')
                db_prop_id = data[0].get('property_id')
                db_agency_id = data[0].get('agency_id')

                update_payload = {}

                if not db_prop_id and property_id:
                    update_payload["property_id"] = property_id

                if not db_agency_id and agency_id:
                    update_payload["agency_id"] = agency_id

                if db_price and current_price != db_price:
                    update_payload["price_pln"] = current_price
                    update_payload["price_per_sqm"] = price_per_sqm
                    log_price_history(property_id, current_price)

                    if current_price < db_price:
                        stats["price_drops"] += 1
                        drop_amount = db_price - current_price

                        avg_sqm_price = 0
                        profit_margin = 0
                        if matched_loc_id and price_per_sqm:
                            avg_sqm_price = market_stats.get((matched_loc_id, target['trans_id'], target['type_id']))
                            if avg_sqm_price and avg_sqm_price > 0:
                                profit_margin = round(((avg_sqm_price - price_per_sqm) / avg_sqm_price) * 100, 1)

                        ai_report = analyze_description_with_ai(card_text) if current_price < db_price else "AI skipped."

                        alert = f"🚨 <b>PRICE DROP ALERT!</b> 🚨\n" \
                                f"━━━━━━━━━━━━━━━━━━━━\n" \
                                f"🔻 <b>Discount:</b> -{drop_amount:,} PLN\n" \
                                f"📉 <b>Old Price:</b> {db_price:,} PLN\n" \
                                f"━━━━━━━━━━━━━━━━━━━━\n" \
                                f"📍 <b>District:</b> {location}\n" \
                                f"💰 <b>Total Price:</b> {current_price:,} PLN\n" \
                                f"📐 <b>Size:</b> {sqm} m² | 🚪 <b>Rooms:</b> {rooms}\n" \
                                f"📈 <b>Margin vs Avg:</b> %{profit_margin}\n" \
                                f"━━━━━━━━━━━━━━━━━━━━\n" \
                                f"🧠 <b>AI ANALYSIS (Gemini):</b>\n" \
                                f"{ai_report}\n" \
                                f"━━━━━━━━━━━━━━━━━━━━\n" \
                                f"🔗 <a href='{full_url}'>View Listing</a>"

                        send_telegram(alert)
                        logger.info(f"🚨 PRICE DROP DETECTED: -{drop_amount} PLN for ID {property_id}")

                if update_payload:
                    patch_url = f"{clean_url}/rest/v1/listings?id=eq.{row_id}"
                    requests.patch(patch_url, json=update_payload, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"})
    except Exception as e:
        logger.error(f"Price Update Check Error: {e}")

def test_scraper():
    global stats

    market_stats = get_market_average()
    logger.info("INFO: Bot is waking up in AI-POWERED SNIPER MODE...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

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
                page.goto(target_url, timeout=60000, wait_until="domcontentloaded")

                try:
                    try:
                        page.wait_for_selector('[data-sentry-component="AdvertCard"]', timeout=10000)
                    except:
                        logger.info(f"🛑 END OF CATEGORY: {target['label']}")
                        break

                    for _ in range(4):
                        scroll_amount = random.randint(300,800)
                        page.mouse.wheel(0, scroll_amount)
                        time.sleep(random.uniform(0.5,1.5))

                    all_listing = page.locator('[data-sentry-component="AdvertCard"]').all()

                    for index, listing in enumerate(all_listing):
                        stats["scanned"] += 1
                        try:
                            raw_url = listing.locator('[data-cy="listing-item-link"]').first.get_attribute('href')
                            if not raw_url: continue
                            full_url = raw_url if raw_url.startswith("http") else f"https://www.otodom.pl{raw_url.replace('/hpr','')}"

                            prop_id_match = re.search(r'ID([^./?]+)', full_url)
                            property_id = prop_id_match.group(1) if prop_id_match else None

                            card_text = listing.inner_text()
                            location = listing.locator('[data-sentry-component="Address"]').first.inner_text()
                            raw_price = listing.locator('[data-sentry-element="MainPrice"]').first.inner_text()

                            try:
                                clean_price = int(re.sub(r'[^\d]', '', raw_price))
                            except: clean_price = 0

                            sqm = None
                            try:
                                clean_text_for_area = re.sub(r'(\d)\s+(\d)', r'\1\2', card_text.replace('\xa0', ' ').lower())
                                sqm_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:m²|m2|m\s*kw|mkw)', clean_text_for_area)
                                ha_match = re.search(r'(\d+(?:[.,]\d+)?)\s*ha\b', clean_text_for_area)
                                ar_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:ar|a)\b', clean_text_for_area)

                                if sqm_match:
                                    sqm = float(sqm_match.group(1).replace(',', '.'))
                                elif ha_match:
                                    sqm = float(ha_match.group(1).replace(',', '.')) * 10000
                                elif ar_match:
                                    sqm = float(ar_match.group(1).replace(',', '.')) * 100
                            except Exception: pass

                            rooms_match = re.search(r'(\d+)\s*pok', card_text)
                            rooms = int(rooms_match.group(1)) if rooms_match else None

                            price_per_sqm = round(clean_price / sqm, 2) if sqm and sqm > 0 else None
                            matched_loc_id = find_loc_id(location)

                            agency_id = "Private/Unknown"
                            try:
                                seller_info = listing.locator('[data-sentry-element="SellerInfoWrapper"]')
                                if seller_info.count() > 0:
                                    raw_agency = seller_info.first.inner_text().strip()
                                    if raw_agency:
                                        agency_id = raw_agency.replace('\n', ' - ')
                            except Exception: pass

                            logger.info(f"[P:{page_num} - {index + 1}] 💰 {clean_price:,} PLN | 📏 {sqm}m² | 🚪 {rooms} P | 📍 ID: {matched_loc_id} | 🏢 Agency: {agency_id}")

                            payload = {
                                "price_pln": clean_price, "url_link": full_url, "source_platform": "Otodom",
                                "is_active": True, "trans_id": target['trans_id'], "type_id": target['type_id'],
                                "sqm": sqm, "rooms": rooms, "price_per_sqm": price_per_sqm, "loc_id": matched_loc_id,
                                "property_id": property_id, "agency_id": agency_id
                            }

                            db_status = save_to_supabase(payload)

                            if db_status in [200, 201, 204]:
                                stats["added"] += 1
                                log_price_history(property_id, clean_price)
                            elif db_status == 409:
                                check_and_update_price(property_id, clean_price, price_per_sqm, full_url, location, sqm, rooms, card_text, matched_loc_id, target, market_stats, agency_id)

                            is_bargain = False
                            profit_margin = 0
                            avg_sqm_price = 0
                            deal_score = 0

                            if matched_loc_id and price_per_sqm:
                                avg_sqm_price = market_stats.get((matched_loc_id, target['trans_id'], target['type_id']))
                                if avg_sqm_price and avg_sqm_price > 0:
                                    if price_per_sqm <= (avg_sqm_price * 0.75):
                                        if sqm and sqm >= 25 and clean_price > 100000:
                                            is_bargain = True
                                            profit_margin = round(((avg_sqm_price - price_per_sqm) / avg_sqm_price) * 100, 1)

                                            profit_score = min(profit_margin * 3.33, 100)
                                            size_score = 100 if sqm >= 50 else (75 if sqm >= 35 else 50)
                                            room_score = 100 if (rooms and rooms >= 3) else (75 if (rooms and rooms == 2) else 50)
                                            price_score = 100 if clean_price <= 600000 else (75 if clean_price <= 900000 else 50)

                                            text_score = 50
                                            lower_card_text = card_text.lower()
                                            if any(k in lower_card_text for k in ["remoncie", "standard", "nowe"]): text_score += 20
                                            if any(k in lower_card_text for k in ["remontu", "stary"]): text_score -= 20

                                            deal_score = min(int((profit_score * 0.40) + (size_score * 0.20) + (room_score * 0.15) + (price_score * 0.15) + (text_score * 0.10)), 100)

                            if is_bargain:
                                stats["bargains"] += 1
                                score_icon = "🔥" if deal_score >= 80 else ("⚡" if deal_score >= 60 else "📊")

                                ai_report = analyze_description_with_ai(card_text)

                                est_monthly_rent = 0
                                roi_percent = 0
                                if target['trans_id'] == 1 and matched_loc_id and sqm:
                                    avg_rent_sqm = market_stats.get((matched_loc_id, 2, target['type_id']))
                                    if avg_rent_sqm and avg_rent_sqm > 0:
                                        est_monthly_rent = sqm * avg_rent_sqm
                                        roi_percent = round(((est_monthly_rent * 12 * 0.8) / clean_price) * 100, 1)

                                alert = f"{score_icon} <b>INVESTMENT SCORE: {deal_score}/100</b>\n" \
                                        f"━━━━━━━━━━━━━━━━━━━━\n" \
                                        f"📍 <b>District:</b> {location}\n" \
                                        f"🏢 <b>Category:</b> {target['label']}\n" \
                                        f"💰 <b>Total Price:</b> {clean_price:,} PLN\n" \
                                        f"📐 <b>Size:</b> {sqm} m² | 🚪 <b>Rooms:</b> {rooms}\n" \
                                        f"📈 <b>Market Avg:</b> {avg_sqm_price:,.0f} PLN\n" \
                                        f"💎 <b>PROFIT MARGIN:</b> %{profit_margin}\n" \
                                        f"━━━━━━━━━━━━━━━━━━━━\n" \
                                        f"🧠 <b>AI ANALYSIS (Gemini):</b>\n" \
                                        f"{ai_report}\n"

                                if roi_percent > 0:
                                    alert += f"━━━━━━━━━━━━━━━━━━━━\n" \
                                             f"🔮 <b>Est. ROI:</b> %{roi_percent} / Year\n"

                                alert += f"━━━━━━━━━━━━━━━━━━━━\n" \
                                         f"🔗 <a href='{full_url}'>View Listing</a>"
                                send_telegram(alert)

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
             f"🔥 <b>AI Deals Found:</b> {stats['bargains']}\n" \
             f"📉 <b>Price Drops Detected:</b> {stats['price_drops']}\n" \
             f"━━━━━━━━━━━━━━━━━━━━"
    send_telegram(report)
    for k in ["scanned", "added", "bargains", "price_drops"]: stats[k] = 0

def start_endless_bot():
    send_telegram("🚀 <b>System Boot:</b> Warsaw AI PropTech Radar is LIVE with Sniper AI Mode!")
    while True:
        try:
            test_scraper()
            send_daily_report()
            time.sleep(600)
        except Exception as e:
            logger.error(f"CRITICAL: {e}")
            time.sleep(60)

if __name__ == "__main__":
    logger.info("INFO: System initializing with AI Sniper Mode...")
    send_telegram("🤖 <b>AI WAKING UP:</b> Connection is OK. Gemini Sniper Mode enabled.")
    start_endless_bot()