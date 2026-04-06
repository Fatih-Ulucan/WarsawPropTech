import re
import random
import logging
import time
import urllib.parse
import unicodedata
from datetime import datetime
from playwright.sync_api import sync_playwright
from Scrapers.config import LOCATION_MAP, SCRAPE_TARGETS, USER_AGENTS, QUEUE_FLUSH_LIMIT

logger = logging.getLogger(__name__)

class OtodomSniper:
    def __init__(self, db_manager, ai_analyzer, notifier):
        self.db = db_manager
        self.ai = ai_analyzer
        self.notif = notifier
        self.ai_queue = []
        self.stats = {"scanned": 0, "added": 0, "bargains": 0, "price_drops": 0, "start_time": datetime.now()}

    def normalize(self, text):
        return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower()

    def find_loc_id(self, location_text):
        if not location_text: return None
        normalized_location = self.normalize(location_text)
        for district, loc_id in LOCATION_MAP.items():
            if self.normalize(district) in normalized_location:
                return loc_id
        return None

    def flush_queue(self, context):
        if not self.ai_queue: return
        logger.info(f"🧠 AI QUEUE FLUSHING: Processing {len(self.ai_queue)} items to clear RAM...")
        detail_page = context.new_page()

        for item in self.ai_queue:
            is_analyzed = False
            alert_sent = False
            try:
                existing = self.db.check_existing_listing(item['url'])
                if existing:
                    is_analyzed = existing.get('ai_analyzed', False)
                    alert_sent = existing.get('alert_sent', False)
            except Exception: pass

            if is_analyzed or alert_sent:
                logger.info(f"⏭️ Skipping {item['url']} (Spam Protection: Already analyzed or sent!).")
                continue

            description = ""
            contact_phone = "Not Available / Hidden"

            try:
                detail_page.goto(item['url'], timeout=30000, wait_until="domcontentloaded")

                try:
                    phone_button = detail_page.locator(
                        'button[data-cy="ad-contact-phone"], '
                        'button:has-text("Pokaż numer"), '
                        'button:has-text("Pokaż"), '
                        'button:has-text("pokaż"), '
                        'div[data-cy="ad-contact-phone"] button'
                    ).first

                    if phone_button.is_visible(timeout=5000):
                        phone_button.click(force=True)
                        logger.info(f"📞 Force-Clicked 'Show Number' button for: {item['url']}")
                        detail_page.wait_for_timeout(2000)
                        try:
                            phone_links = detail_page.locator('a[href^="tel:"]').all()
                            if phone_links:
                                contact_phone = phone_links[0].inner_text().strip()
                        except Exception:
                            logger.debug("⚠️ Phone API timeout/hidden.")
                except Exception as e:
                    logger.debug(f"⚠️ Phone extraction failed: {e}")

                try:
                    detail_page.wait_for_selector('[data-cy="adPageAdDescription"]', timeout=5000)
                    description = detail_page.locator('[data-cy="adPageAdDescription"]').inner_text()
                except:
                    description = detail_page.locator('body').inner_text()
            except Exception as e:
                logger.error(f"Failed to fetch full description: {e}")

            if description:
                ai_report = self.ai.analyze_description(description)
                self.db.mark_as_analyzed(item['url'])
            else:
                ai_report = "AI Analysis unavailable (Could not fetch full description)."

            alert = item['alert_template'].format(ai_report=ai_report, contact_phone=contact_phone)
            self.notif.send_message(alert)
            time.sleep(4)

        detail_page.close()
        self.ai_queue.clear()

    def run_mission(self):
        market_stats = self.db.get_market_averages()
        logger.info("INFO: Bot is waking up in AI-POWERED SNIPER MODE...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)}
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

                    try:
                        page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
                        try:
                            page.wait_for_selector('[data-sentry-component="AdvertCard"]', timeout=10000)
                        except:
                            logger.info(f"🛑 END OF CATEGORY: {target['label']}")
                            break

                        for _ in range(3):
                            scroll_amount = random.randint(300, 800)
                            page.mouse.wheel(0, scroll_amount)
                            time.sleep(random.uniform(0.2, 0.6))

                        all_listing = page.locator('[data-sentry-component="AdvertCard"]').all()

                        for index, listing in enumerate(all_listing):
                            self.stats["scanned"] += 1
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
                                matched_loc_id = self.find_loc_id(location)

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
                                    "property_id": property_id, "agency_id": agency_id,
                                    "ai_analyzed": False
                                }

                                db_status = self.db.save_listing(payload)

                                if db_status in [200, 201, 204]:
                                    self.stats["added"] += 1
                                    self.db.log_price_history(property_id, clean_price)
                                elif db_status == 409:
                                    existing = self.db.check_existing_listing(full_url)
                                    if existing:
                                        db_price = existing.get('price_pln')
                                        row_id = existing.get('id')
                                        db_prop_id = existing.get('property_id')
                                        db_agency_id = existing.get('agency_id')

                                        update_payload = {}
                                        if not db_prop_id and property_id: update_payload["property_id"] = property_id
                                        if not db_agency_id and agency_id: update_payload["agency_id"] = agency_id

                                        if db_price and clean_price != db_price:
                                            update_payload["price_pln"] = clean_price
                                            update_payload["price_per_sqm"] = price_per_sqm
                                            self.db.log_price_history(property_id, clean_price)

                                            if clean_price < db_price:
                                                self.stats["price_drops"] += 1
                                                drop_amount = db_price - clean_price

                                                avg_sqm_price = 0
                                                profit_margin = 0
                                                if matched_loc_id and price_per_sqm:
                                                    avg_sqm_price = market_stats.get((matched_loc_id, target['trans_id'], target['type_id']))
                                                    if avg_sqm_price and avg_sqm_price > 0:
                                                        profit_margin = round(((avg_sqm_price - price_per_sqm) / avg_sqm_price) * 100, 1)

                                                drop_data = {
                                                    'drop_amount': drop_amount,
                                                    'db_price': db_price,
                                                    'location': location,
                                                    'current_price': clean_price,
                                                    'sqm': sqm,
                                                    'rooms': rooms,
                                                    'profit_margin': profit_margin,
                                                    'full_url': full_url
                                                }
                                                alert_template = self.notif.create_price_drop_alert(drop_data)
                                                self.ai_queue.append({'url': full_url, 'alert_template': alert_template})
                                                logger.info(f"💎 DEAL DETECTED! Added to AI Queue: {full_url}")
                                                logger.info(f"🚨 PRICE DROP QUEUED: -{drop_amount} PLN for ID {property_id}")

                                        if update_payload:
                                            self.db.update_listing(row_id, update_payload)

                                is_bargain = False
                                profit_margin = 0
                                avg_sqm_price = 0
                                deal_score = 0

                                lower_card_text = card_text.lower()
                                flip_flag_text = ""
                                if "remontu" in lower_card_text or "odświeżenia" in lower_card_text:
                                    flip_flag_text = "🛠️ <b>FLIP POTENTIAL DETECTED!</b>\n━━━━━━━━━━━━━━━━━━━━\n"

                                if matched_loc_id and price_per_sqm:
                                    avg_sqm_price = market_stats.get((matched_loc_id, target['trans_id'], target['type_id']))
                                    if avg_sqm_price and avg_sqm_price > 0:

                                        threshold = 0.80 if target['trans_id'] == 1 else 0.70

                                        if price_per_sqm <= (avg_sqm_price * threshold):

                                            if sqm and sqm >= 25 and clean_price > 100000:
                                                is_bargain = True
                                                profit_margin = round(((avg_sqm_price - price_per_sqm) / avg_sqm_price) * 100, 1)

                                                profit_score = min(profit_margin * 3.33, 100)
                                                size_score = 100 if sqm >= 50 else (75 if sqm >= 35 else 50)
                                                room_score = 100 if (rooms and rooms >= 3) else (75 if (rooms and rooms == 2) else 50)
                                                price_score = 100 if clean_price <= 600000 else (75 if clean_price <= 900000 else 50)

                                                text_score = 50
                                                if any(k in lower_card_text for k in ["remoncie", "standard", "nowe"]): text_score += 20
                                                if any(k in lower_card_text for k in ["remontu", "stary"]): text_score -= 20

                                                urgency_bonus = 0
                                                if any(k in lower_card_text for k in ["pilna", "natychmiast", "wyjazd", "okazja", "szybko"]):
                                                    urgency_bonus = 15

                                                deal_score = min(int((profit_score * 0.40) + (size_score * 0.20) + (room_score * 0.15) + (price_score * 0.15) + (text_score * 0.10) + urgency_bonus), 100)

                                if is_bargain:
                                    self.stats["bargains"] += 1
                                    score_icon = "🔥" if deal_score >= 80 else ("⚡" if deal_score >= 60 else "📊")

                                    est_monthly_rent = 0
                                    roi_percent = 0
                                    true_profit = 0

                                    if target['trans_id'] == 1 and matched_loc_id and sqm:
                                        avg_rent_sqm = market_stats.get((matched_loc_id, 2, target['type_id']))
                                        if avg_rent_sqm and avg_rent_sqm > 0:
                                            est_monthly_rent = sqm * avg_rent_sqm
                                            roi_percent = round(((est_monthly_rent * 12 * 0.8) / clean_price) * 100, 1)

                                        reno_cost_per_sqm = random.randint(1500, 2500) if flip_flag_text else random.randint(500, 1000)
                                        renovation_cost = sqm * reno_cost_per_sqm
                                        market_value = avg_sqm_price * sqm
                                        true_profit = market_value - clean_price - renovation_cost

                                    deal_data = {
                                        'flip_flag_text': flip_flag_text,
                                        'score_icon': score_icon,
                                        'deal_score': deal_score,
                                        'location': location,
                                        'label': target['label'],
                                        'clean_price': clean_price,
                                        'sqm': sqm,
                                        'rooms': rooms,
                                        'avg_sqm_price': avg_sqm_price,
                                        'profit_margin': profit_margin,
                                        'trans_id': target['trans_id'],
                                        'true_profit': true_profit,
                                        'roi_percent': roi_percent,
                                        'full_url': full_url
                                    }

                                    alert_template = self.notif.create_deal_alert(deal_data)
                                    self.ai_queue.append({
                                        'url': full_url,
                                        'alert_template': alert_template
                                    })
                                    logger.info(f"💎 DEAL DETECTED! Added to AI Queue: {full_url}")

                                if len(self.ai_queue) >= QUEUE_FLUSH_LIMIT:
                                    self.flush_queue(context)

                            except Exception as e:
                                logger.debug(f"⚠️ Listing processing skipped: {e}")
                                continue
                    except Exception as e:
                        logger.error(f"ERROR: Page {page_num} failed: {e}")

                    time.sleep(random.uniform(1.5, 3.0))

            self.flush_queue(context)
            browser.close()
            return self.stats