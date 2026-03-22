import os
import time
import requests
from playwright.sync_api import sync_playwright

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
    {"url_part": "sprzedaz", "trans_id": 1, "label": "FOR SALE (Sprzedaż)"},
    {"url_part": "wynajem", "trans_id": 2, "label": "FOR RENT (Wynajem)"}
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

    try:
        response = requests.post(table_url, json=data, headers=headers, timeout=10)
        if response.status_code == 400:
            print(f"      ❌ SERVER REJECTED (400): {response.text}")

        return response.status_code
    except Exception as e:
        print(f"      ❌ CONNECTION ERROR: {e}")
        return None

def test_scraper():
    print("INFO: Bot is waking up and launching the browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("INFO: Navigating to Otodom to clear cookies...")
        page.goto("https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/mazowieckie/warszawa/warszawa/warszawa")

        print("INFO: Looking for the Cookie banner...")
        try:
            cookie_button = page.locator("#onetrust-accept-btn-handler")
            cookie_button.wait_for(timeout=5000)
            cookie_button.click()
            print("SUCCESS: Cookie banner destroyed! The view is clear.")
        except Exception:
            print("INFO: No Cookie banner found, moving on.")

        for target in SCRAPE_TARGETS:
            print(f"\n{'='*70}")
            print(f"🚀 INITIATING MISSION: {target['label']}")
            print(f"{'='*70}")

            for page_num in range(1, 16):
                print(f"\n============================================================")
                print(f"📄 SCRAPING INITIATED: PAGE {page_num} [{target['label']}]")
                print(f"============================================================")

                target_url = f"https://www.otodom.pl/pl/wyniki/{target['url_part']}/mieszkanie/mazowieckie/warszawa/warszawa/warszawa?direction=ASC&sorting=PRICE&page={page_num}"
                page.goto(target_url)

                print("INFO: Scanning for real estate listings...")

                try:
                    page.wait_for_selector('[data-sentry-component="AdvertCard"]', timeout=10000)

                    print("INFO: Scrolling down to trick 'Lazy Loading' (3 times)...")
                    for _ in range(3):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1.5)

                    all_listing = page.locator('[data-sentry-component="AdvertCard"]').all()

                    print(f"INFO: Hurricane Mode active! Found {len(all_listing)} listings on page {page_num}. Extracting...\n")
                    print("="*70)

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

                            print(f"[P:{page_num} - {index + 1}] 💰 {display_price} PLN | 📌 {title} | 📍 District ID: {matched_loc_id}\n 🔗 Link: {full_url}\n")

                            payload = {
                                "price_pln": clean_price,
                                "url_link": full_url,
                                "source_platform": "Otodom",
                                "is_active": True,
                                "trans_id": target['trans_id'],  
                                "type_id": 1
                            }

                            if matched_loc_id is not None:
                                payload["loc_id"] = matched_loc_id

                            db_status = save_to_supabase(payload)

                            if db_status in [200, 201, 204]:
                                print(f"      ✅ DB SYNC SUCCESS (New Listing Added)")
                            elif db_status == 409:
                                print(f"      🔄 ALREADY EXISTS (Skipped)")
                            else:
                                print(f"      ❌ DB ERROR (Code: {db_status})")

                        except Exception:
                            print(f"[{index + 1}] ⚠ WARNING: Missing data skipped (likely a hidden sponsored ad).")
                            continue

                    print("="*70 + "\n")

                except Exception as e:
                    print(f"ERROR: Failed to extract listing data for Page {page_num}. Details: {e}")

                print(f"INFO: Page {page_num} completed. Resting for 5 seconds to avoid IP ban...")
                time.sleep(5)

        time.sleep(3)
        browser.close()
        print("INFO: ALL MISSIONS COMPLETE! Operation complete, browser closed safely.")

if __name__ == "__main__":
    print("INFO: System initializing...")
    test_scraper()