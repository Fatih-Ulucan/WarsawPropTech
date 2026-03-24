import os
import time
import requests
import logging
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

SUPABASE_URL = "https://mvappdsdacsamgvkrcmb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im12YXBwZHNkYWNzYW1ndmtyY21iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQxMjcyOTQsImV4cCI6MjA4OTcwMzI5NH0.jJ4G_l21Njm-aNPoqJ9LijnsotQCsoEpiJHS4uzIzK8"

LOCATION_MAP = {
    'Mokotów': 1, 'Praga-Południe': 2, 'Ursynów': 3, 'Wola': 4,
    'Białołęka': 5, 'Bielany': 6, 'Bemowo': 7, 'Targówek': 8,
    'Śródmieście': 9, 'Wawer': 10, 'Ochota': 11, 'Ursus': 12,
    'Praga-Północ': 13, 'Włochy': 14, 'Wilanów': 15, 'Wesoła': 16,
    'Żoliborz': 17, 'Rembertów': 18
}

SCRAPE_TARGETS = [
    # --- Mieszkania (Apartments) type_id: 1 ---
    {"url_part": "sprzedaz/mieszkanie", "trans_id": 1, "type_id": 1, "label": "APARTMENT SALE"},
    {"url_part": "wynajem/mieszkanie", "trans_id": 2, "type_id": 1, "label": "APARTMENT RENT"},

    # --- Kawalerki (Studios) type_id: 1 (Still Apartments) ---
    {"url_part": "sprzedaz/kawalerka", "trans_id": 1, "type_id": 1, "label": "STUDIO SALE"},
    {"url_part": "wynajem/kawalerka", "trans_id": 2, "type_id": 1, "label": "STUDIO RENT"},

    # --- Domy (Houses) type_id: 2 ---
    {"url_part": "sprzedaz/dom", "trans_id": 1, "type_id": 2, "label": "HOUSE SALE"},
    {"url_part": "wynajem/dom", "trans_id": 2, "type_id": 2, "label": "HOUSE RENT"},

    # --- Lokale użytkowe (Commercial) type_id: 3 ---
    {"url_part": "sprzedaz/lokal", "trans_id": 1, "type_id": 3, "label": "COMMERCIAL SALE"},
    {"url_part": "wynajem/lokal", "trans_id": 2, "type_id": 3, "label": "COMMERCIAL RENT"},

    # --- Garaże (Garages) type_id: 4 --- 
    {"url_part": "sprzedaz/garaz", "trans_id": 1, "type_id": 4, "label": "GARAGE SALE"},
    {"url_part": "wynajem/garaz", "trans_id": 2, "type_id": 4, "label": "GARAGE RENT"},

    # --- Działki (Plots) type_id: 5 (Assuming type_id 5 for plots) ---
    {"url_part": "sprzedaz/dzialka", "trans_id": 1, "type_id": 5, "label": "PLOT SALE"}
]

def find_loc_id(location_text):
    """Check the address text, finds the district, and returns its ID."""
    if not location_text:
        return None
    for district, loc_id in LOCATION_MAP.items():
        if district in location_text:
            return loc_id
    return None

def save_to_supabase(data):
    """Sends extracted data to the 'listings' table."""
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
            if response.status_code == 400:
                logger.error(f"      ❌ SERVER REJECTED (400): {response.text}")

            return response.status_code
        except Exception as e:
            logger.warning(f"      ❌ CONNECTION ERROR (Attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2) 

    return None 

def test_scraper():
    logger.info("INFO: Bot is waking up and launching the browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        logger.info("INFO: Navigating to Otodom to clear cookies...")
        page.goto("https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/mazowieckie/warszawa/warszawa/warszawa")

        logger.info("INFO: Looking for the Cookie banner...")
        try:
            cookie_button = page.locator("#onetrust-accept-btn-handler")
            cookie_button.wait_for(timeout=5000)
            cookie_button.click()
            logger.info("SUCCESS: Cookie banner destroyed! The view is clear.")
        except Exception:
            logger.info("INFO: No Cookie banner found, moving on.")

        for target in SCRAPE_TARGETS:
            logger.info(f"\n{'='*70}")
            logger.info(f"🚀 INITIATING MEGA MISSION: {target['label']}")
            logger.info(f"{'='*70}")

            for page_num in range(1, 16):
                logger.info(f"\n============================================================")
                logger.info(f"📄 SCRAPING INITIATED: PAGE {page_num} [{target['label']}]")
                logger.info(f"============================================================")

                target_url = f"https://www.otodom.pl/pl/wyniki/{target['url_part']}/mazowieckie/warszawa/warszawa/warszawa?direction=ASC&sorting=PRICE&page={page_num}"
                page.goto(target_url)

                logger.info("INFO: Scanning for real estate listings...")

                try:
                    page.wait_for_selector('[data-sentry-component="AdvertCard"]', timeout=10000)

                    logger.info("INFO: Scrolling down to trick 'Lazy Loading' (3 times)...")
                    for _ in range(3):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1.5)

                    all_listing = page.locator('[data-sentry-component="AdvertCard"]').all()

                    logger.info(f"INFO: Hurricane Mode active! Found {len(all_listing)} listings on page {page_num}. Extracting...\n")
                    logger.info("="*70)

                    for index, listing in enumerate(all_listing):
                        try:
                            title = listing.locator('[data-cy="listing-item-link"]').first.inner_text()
                            location = listing.locator('[data-sentry-component="Address"]').first.inner_text()
                            raw_price = listing.locator('[data-sentry-element="MainPrice"]').first.inner_text()

                            try:
                                clean_price = int(raw_price.replace("zł","").replace(" ","").replace("\xa0",""))
                            except ValueError:
                                clean_price = 0

                            raw_url = listing.locator('[data-cy="listing-item-link"]').first.get_attribute('href')

                            if not raw_url:
                                continue
                            if raw_url.startswith("/hpr"):
                                raw_url = raw_url.replace("/hpr", "")
                            if raw_url.startswith("http"):
                                full_url = raw_url
                            else:
                                full_url = f"https://www.otodom.pl{raw_url}"

                            display_price = f"{clean_price:,}".replace(","," ")

                            matched_loc_id = find_loc_id(location)

                            logger.info(f"[P:{page_num} - {index + 1}] 💰 {display_price} PLN | 📌 {title} | 📍 District ID: {matched_loc_id}\n 🔗 Link: {full_url}\n")

                            payload = {
                                "price_pln": clean_price,
                                "url_link": full_url,
                                "source_platform": "Otodom",
                                "is_active": True,
                                "trans_id": target['trans_id'],
                                "type_id": target['type_id']
                            }

                            if matched_loc_id is not None:
                                payload["loc_id"] = matched_loc_id

                            db_status = save_to_supabase(payload)

                            if db_status in [200, 201, 204]:
                                logger.info(f"      ✅ DB SYNC SUCCESS (New Listing Added)")
                            elif db_status == 409:
                                logger.info(f"      🔄 ALREADY EXISTS (Skipped)")
                            else:
                                logger.error(f"      ❌ DB ERROR (Code: {db_status})")

                        except Exception:
                            logger.warning(f"[{index + 1}] ⚠ WARNING: Missing data skipped (likely a hidden sponsored ad).")
                            continue

                    logger.info("="*70 + "\n")

                except Exception as e:
                    logger.error(f"ERROR: Failed to extract listing data for Page {page_num}. Details: {e}")

                logger.info(f"INFO: Page {page_num} completed. Resting for 5 seconds to avoid IP ban...")
                time.sleep(5)

        time.sleep(3)
        browser.close()
        logger.info("INFO: ALL MISSIONS COMPLETE! Operation complete, browser closed safely.")


def start_endless_bot():
    """Runs your exact test_scraper() function in a 24/7 continuous loop."""
    logger.info("🔥 ENDLESS DATA BEAST MODE ACTIVATED! 🔥")
    cycle_count = 1

    while True:
        logger.info(f"\n{'*'*50}\nSTARTING CYCLE #{cycle_count}\n{'*'*50}")

        test_scraper()

        logger.info("INFO: Cycle finished. System is cooling down for 10 minutes to avoid bans...")
        time.sleep(600)

        cycle_count += 1

if __name__ == "__main__":
    logger.info("INFO: System initializing...")
    start_endless_bot()