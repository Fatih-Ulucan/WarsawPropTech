import os
import re
import random
import logging
import time
import urllib.parse
import unicodedata
import hashlib
from datetime import datetime
from playwright.sync_api import sync_playwright
from Scrapers.config import LOCATION_MAP, SCRAPE_TARGETS, USER_AGENTS, QUEUE_FLUSH_LIMIT, EXPANDER_LINK

try:
    from Scrapers.notifier import EmailManager
except ImportError:
    pass

logger = logging.getLogger(__name__)

class OtodomSniper:
    def __init__(self, db_manager, ai_analyzer, notifier):
        self.db = db_manager
        self.ai = ai_analyzer
        self.notif = notifier
        self.ai_queue = []
        self.stats = {"scanned": 0, "added": 0, "bargains": 0, "price_drops": 0, "error_count": 0, "errors": [], "start_time": datetime.now()}

        try:
            sender_email = os.environ.get("SENDER_EMAIL")
            sender_password = os.environ.get("SENDER_PASSWORD")
            self.email_manager = EmailManager(sender_email, sender_password)
        except Exception as e:
            logger.warning(f"Email Manager failed to initialize (Missing env variables?): {e}")
            self.email_manager = None

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
        logger.info(f"🧠 AI ENGINE: Processing {len(self.ai_queue)} items in queue...")
        detail_page = context.new_page()

        for item in self.ai_queue:
            is_analyzed = False
            alert_sent = False
            row_id = None
            try:
                existing = self.db.check_existing_listing(item['url'])
                if existing:
                    is_analyzed = existing.get('ai_analyzed', False)
                    alert_sent = existing.get('alert_sent', False)
                    row_id = existing.get('id')
            except Exception: pass

            if is_analyzed or alert_sent:
                logger.info(f"⏭️ Skipping {item['url']} (Already processed).")
                continue

            try:
                response = detail_page.goto(item['url'], timeout=30000, wait_until="domcontentloaded")
                current_url = detail_page.url

                if not response or response.status == 404 or "otodom.pl/pl/oferta/" not in current_url:
                    if row_id:
                        self.db.mark_as_sold(row_id)
                    logger.info(f"🧟 ZOMBIE KILLED (Redirect/404): {item['url']}")
                    continue

                try:
                    page_content = detail_page.locator('body').inner_text().lower()
                    if "nie jest już dostępne" in page_content or "ogłoszenie nieaktualne" in page_content or "nie znaleziono strony" in page_content:
                        if row_id:
                            self.db.mark_as_sold(row_id)
                        logger.info(f"🧟 ZOMBIE KILLED (Banner Detected): {item['url']}")
                        continue
                except Exception:
                    pass

            except Exception:
                logger.warning(f"⚠️ Could not reach {item['url']}, skipping for now.")
                continue

            description = ""
            contact_phone = "Not Available / Hidden"
            image_urls = []

            try:
                phone_button = detail_page.locator(
                    'button[data-cy="ad-contact-phone"], '
                    'button[data-testid="contact-phone-button"], '
                    'button:has-text("Pokaż numer"), '
                    'button:has-text("Pokaż"), '
                    'button:has-text("pokaż"), '
                    'div[data-cy="ad-contact-phone"] button, '
                    'button.css-11y9s82'
                ).first

                if phone_button.is_visible(timeout=5000):
                    phone_button.click(force=True)
                    logger.info(f"📞 Show Number clicked for: {item['url']}")
                    detail_page.wait_for_timeout(2500)

                    try:
                        phone_links = detail_page.locator('a[href^="tel:"]').all()
                        if phone_links:
                            contact_phone = phone_links[0].inner_text().strip()
                        else:
                            contact_phone = detail_page.locator('[data-cy="ad-contact-phone"]').inner_text().strip()

                        if "pokaż" in contact_phone.lower():
                            contact_phone = "Not Available / Hidden"

                    except Exception:
                        logger.debug("⚠️ Phone text extraction failed.")
            except Exception as e:
                logger.debug(f"⚠️ Phone button interaction failed: {e}")

            try:
                desc_selectors = [
                    '[data-cy="adPageAdDescription"]',
                    '[data-testid="ad-description"]',
                    '.css-1qzszy5'
                ]
                for selector in desc_selectors:
                    if detail_page.locator(selector).count() > 0:
                        description = detail_page.locator(selector).first.inner_text()
                        break

                if not description:
                    if detail_page.locator('article').count() > 0:
                        description = detail_page.locator('article').first.inner_text()
            except Exception:
                logger.debug("⚠️ Targeted description extraction failed, trying body fallback.")
                try:
                    description = detail_page.locator('body').inner_text()[:2500]
                except:
                    pass

            try:
                images = detail_page.locator('picture source').all()
                for img in images:
                    src = img.get_attribute('srcset')
                    if src and "http" in src:
                        clean_url = src.split(' ')[0]
                        if clean_url not in image_urls:
                            image_urls.append(clean_url)
                logger.info(f"📸 Extracted {len(image_urls)} images.")
            except Exception as e:
                logger.debug(f"⚠️ Image extraction failed: {e}")

            category = item.get('category', 'Apartment - Sale')
            sqm_val = item.get('data', {}).get('sqm', 0)

            if description or image_urls:
                if image_urls:
                    ai_report = self.ai.analyze_with_vision(description, image_urls, category=category, sqm=sqm_val)
                else:
                    ai_report = self.ai.analyze_description(description, category=category)
                self.db.mark_as_analyzed(item['url'])
            else:
                ai_report = "AI Analysis unavailable (Source data could not be extracted from page)."

            loc_id_val = item.get('data', {}).get('loc_id')
            m_speed = self.db.get_market_speed_rank(loc_id_val) if loc_id_val else "Unknown ⚪"

            final_report = f"🏙️ <b>Market Speed:</b> {m_speed}\n" + ai_report
            alert = item['alert_template'].format(ai_report=final_report, contact_phone=contact_phone)
            self.notif.send_message(alert)

            try:
                self._notify_users(item, final_report)
            except Exception as e:
                logger.error(f"❌ Error occurred while sending user notifications: {e}")

            time.sleep(4)

        detail_page.close()
        self.ai_queue.clear()

    def cleanup_dead_listings(self, context):
        logger.info("🧹 ZOMBIE CLEANUP: Initializing check for inactive listings...")
        try:
            count = self.db.cleanup_old_listings(days_old=3)
            logger.info(f"✅ ZOMBIE CLEANUP COMPLETE: {count} properties moved to SOLD archive.")
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

    def send_mission_report(self):
        duration = datetime.now() - self.stats["start_time"]
        minutes = duration.total_seconds() / 60

        report = (
            f"📊 *MISSION AFTER-ACTION REPORT*\n"
            f"⏱️ Duration: {minutes:.1f} mins\n"
            f"🔍 Scanned: {self.stats['scanned']}\n"
            f"✅ Added/Updated: {self.stats['added']}\n"
            f"🔥 Bargains Found: {self.stats['bargains']}\n"
            f"📉 Price Drops: {self.stats['price_drops']}\n\n"
        )

        if self.stats["error_count"] == 0:
            report += "🟢 *Status: PERFECT EXECUTION* (0 Errors)"
        else:
            report += f"🔴 *Status: COMPLETED WITH ERRORS*\n❌ Total Errors: {self.stats['error_count']}\n\n⚠️ *Error Log (Sample):*\n"
            for err in self.stats["errors"]:
                report += f"- `{err}`\n"
            if self.stats["error_count"] > len(self.stats["errors"]):
                report += "...\n*(Remaining errors truncated to save space)*"

        try:
            self.notif.send_message(report)
        except Exception as e:
            logger.error(f"Failed to send mission report to Telegram: {e}")

    def run_mission(self):
        market_stats = self.db.get_market_averages()
        logger.info("INFO: Starting Mission in AI-POWERED SNIPER MODE...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)}
            )
            self.cleanup_dead_listings(context)
            page = context.new_page()

            logger.info("INFO: Accessing Otodom Warsaw...")
            page.goto("https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/mazowieckie/warszawa/warszawa/warszawa")

            try:
                cookie_button = page.locator("#onetrust-accept-btn-handler")
                cookie_button.wait_for(timeout=5000)
                cookie_button.click()
                logger.info("SUCCESS: Cookie consent accepted.")
            except: pass

            for target in SCRAPE_TARGETS:
                logger.info(f"\n🚀 TARGET ACQUIRED: {target['label']}")

                for page_num in range(1, 21):
                    target_url = f"https://www.otodom.pl/pl/wyniki/{target['url_part']}/mazowieckie/warszawa/warszawa/warszawa?direction=ASC&sorting=PRICE&page={page_num}"

                    try:
                        page.goto(target_url, timeout=60000, wait_until="domcontentloaded")

                        try:
                            page.wait_for_selector('[data-cy="listing-item"], [data-testid="listing-item"], [data-sentry-component="AdvertCard"]', timeout=10000)
                        except:
                            logger.info(f"🛑 SCAN COMPLETE: End of {target['label']} or No Listings Found.")
                            break

                        for _ in range(3):
                            scroll_amount = random.randint(300, 800)
                            page.mouse.wheel(0, scroll_amount)
                            time.sleep(random.uniform(0.2, 0.6))

                        all_listing = page.locator('[data-cy="listing-item"], [data-testid="listing-item"], [data-sentry-component="AdvertCard"]').all()

                        for index, listing in enumerate(all_listing):
                            self.stats["scanned"] += 1
                            try:
                                raw_url = ""
                                url_nodes = listing.locator('a[data-cy="listing-item-link"], a').all()
                                if url_nodes:
                                    raw_url = url_nodes[0].get_attribute('href')

                                if not raw_url: continue
                                full_url = raw_url if raw_url.startswith("http") else f"https://www.otodom.pl{raw_url.replace('/hpr','')}"

                                full_url = full_url.split('?')[0]

                                prop_id_match = re.search(r'ID([A-Za-z0-9]+)(?:\.html|\?|$)', full_url)
                                if prop_id_match:
                                    property_id = prop_id_match.group(1)
                                else:
                                    fallback_match = re.search(r'-(\d{7,15})(?:\.html|\?|$)', full_url)
                                    if fallback_match:
                                        property_id = fallback_match.group(1)
                                    else:
                                        property_id = hashlib.md5(full_url.encode('utf-8')).hexdigest()[:12]

                                card_text = listing.inner_text()
                                lower_card_text = card_text.lower()

                                if "nieaktualne" in lower_card_text or "rezerwacja" in lower_card_text or "zarezerwowane" in lower_card_text:
                                    existing = self.db.check_existing_listing(full_url)
                                    if existing:
                                        self.db.mark_as_sold(existing.get('id'))
                                        logger.info(f"🧟 ZOMBIE KILLED (Badge on Search): {full_url}")
                                    continue

                                location = ""
                                loc_nodes = listing.locator('[data-sentry-component="Address"], p.css-19dke2r, p[data-testid="advert-card-address"]').all()
                                if loc_nodes:
                                    location = loc_nodes[0].inner_text()
                                else:
                                    for line in card_text.split('\n'):
                                        if 'Warszawa' in line or 'mazowieckie' in line:
                                            location = line
                                            break
                                    if not location:
                                        location = card_text

                                raw_price = ""
                                price_nodes = listing.locator('[data-sentry-element="MainPrice"], span.css-1cwlsje, [data-testid="advert-card-price"]').all()
                                if price_nodes:
                                    raw_price = price_nodes[0].inner_text()
                                else:
                                    match = re.search(r'([\d\s]+(?:,[\d]+)?)\s*zł', card_text)
                                    if match: raw_price = match.group(0)

                                try:
                                    price_text = raw_price.split(',')[0].split('zł')[0]
                                    clean_price = int(re.sub(r'[^\d]', '', price_text))
                                except: clean_price = 0

                                sqm = None
                                try:
                                    clean_text_for_area = re.sub(r'(\d)\s+(\d)', r'\1\2', card_text.replace('\xa0', ' ').lower())
                                    sqm_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:m²|m2|m\s*kw|mkw)', clean_text_for_area)
                                    if sqm_match:
                                        sqm = float(sqm_match.group(1).replace(',', '.'))
                                except Exception: pass

                                rooms_match = re.search(r'(\d+)\s*(pok|pokoje|pokoi)', lower_card_text)
                                rooms = int(rooms_match.group(1)) if rooms_match else 0

                                price_per_sqm = round(clean_price / sqm, 2) if sqm and sqm > 0 else 0.0
                                matched_loc_id = self.find_loc_id(location)

                                agency_id = "Private/Unknown"
                                try:
                                    seller_info = listing.locator('[data-sentry-element="SellerInfoWrapper"]')
                                    if seller_info.count() > 0:
                                        raw_agency = seller_info.first.inner_text().strip()
                                        if raw_agency:
                                            agency_id = raw_agency.replace('\n', ' - ')[:50]
                                except Exception: pass

                                clean_price = clean_price if clean_price else 0
                                sqm = sqm if sqm else 0.0
                                price_per_sqm = price_per_sqm if price_per_sqm else 0.0
                                agency_id = agency_id if agency_id else "Unknown"

                                logger.info(f"[P:{page_num} - {index + 1}] 💰 {clean_price:,} PLN | 📏 {sqm}m² | 🚪 {rooms}R | 📍 Loc: {matched_loc_id}")

                                payload = {
                                    "price_pln": clean_price, "url_link": full_url, "source_platform": "Otodom",
                                    "is_active": True, "trans_id": target['trans_id'], "type_id": target['type_id'],
                                    "sqm": sqm, "rooms": rooms, "price_per_sqm": price_per_sqm, "loc_id": matched_loc_id,
                                    "property_id": property_id, "agency_id": agency_id,
                                    "ai_analyzed": False,
                                    "status": "ACTIVE",
                                    "updated_at": datetime.utcnow().isoformat() + "Z"
                                }

                                db_status = self.db.save_listing(payload)

                                if db_status not in [200, 201, 204, 409]:
                                    logger.error(f"❌ SUPABASE REJECTION for {property_id} - HTTP Status: {db_status} - URL: {full_url}")

                                if db_status in [200, 201, 204]:
                                    self.stats["added"] += 1
                                    self.db.log_price_history(property_id, clean_price)
                                elif db_status == 409:
                                    existing = self.db.check_existing_listing(full_url)
                                    if existing:
                                        row_id = existing.get('id')
                                        db_price = existing.get('price_pln')

                                        self.db.update_last_seen(row_id)

                                        update_payload = {}
                                        if not existing.get('property_id') and property_id: update_payload["property_id"] = property_id
                                        if not existing.get('agency_id') and agency_id: update_payload["agency_id"] = agency_id
                                        if not existing.get('loc_id') and matched_loc_id: update_payload["loc_id"] = matched_loc_id

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
                                                alert_template = self.notif.create_price_drop_alert(drop_amount)
                                                self.ai_queue.append({
                                                    'url': full_url,
                                                    'alert_template': alert_template,
                                                    'category': target['label'],
                                                    'property_id': property_id,
                                                    'alert_type': 'price_drop',
                                                    'data': {'sqm': sqm, 'loc_id': matched_loc_id}
                                                })

                                        if update_payload:
                                            self.db.update_listing(row_id, update_payload)

                                is_bargain = False
                                profit_margin = 0
                                avg_sqm_price = 0
                                deal_score = 0

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
                                        'flip_flag_text': flip_flag_text, 'score_icon': score_icon, 'deal_score': deal_score,
                                        'location': location, 'label': target['label'], 'clean_price': clean_price,
                                        'sqm': sqm, 'rooms': rooms, 'avg_sqm_price': avg_sqm_price, 'profit_margin': profit_margin,
                                        'trans_id': target['trans_id'], 'true_profit': true_profit, 'roi_percent': roi_percent,
                                        'full_url': full_url
                                    }

                                    alert_template = self.notif.create_deal_alert(deal_data)
                                    self.ai_queue.append({
                                        'url': full_url,
                                        'alert_template': alert_template,
                                        'category': target['label'],
                                        'property_id': property_id,
                                        'alert_type': 'bargain',
                                        'data': {'sqm': sqm, 'loc_id': matched_loc_id}
                                    })

                                if len(self.ai_queue) >= QUEUE_FLUSH_LIMIT:
                                    self.flush_queue(context)

                            except Exception as e:
                                self.stats["error_count"] += 1
                                logger.debug(f"⚠️ Listing processing skipped: {e}")
                                if len(self.stats["errors"]) < 15:
                                    self.stats["errors"].append(f"Pg {page_num}, Itm {index + 1}: {str(e)[:60]}")
                                continue

                    except Exception as e:
                        logger.error(f"ERROR: Page {page_num} failed: {e}")

                    time.sleep(random.uniform(1.5, 3.0))

            self.flush_queue(context)
            browser.close()

            self.send_mission_report()

            return self.stats

    def _notify_users(self, item, ai_report):
        if not hasattr(self.db, 'client'):
            return

        property_id = item.get('property_id')
        alert_type = item.get('alert_type')
        data = item.get('data')

        if not property_id or not alert_type:
            return

        try:
            response = self.db.client.table('favorites').select('user_email').eq('property_id', property_id).execute()
            tracked_users = [row['user_email'] for row in response.data] if response.data else []

            if not tracked_users:
                return

            if alert_type == 'price_drop':
                title = "🚨 Price Drop Alert!"
                msg_ui = f"Discount! Property ID {property_id} dropped to {data.get('current_price', 'N/A')} PLN."
                content_lines = [
                    f"Great news! A property you are tracking has a new price.",
                    f"<b>Location:</b> {data.get('location', 'Unknown')}",
                    f"<b>New Price:</b> {data.get('current_price', 'N/A')} PLN",
                    f"<b>AI Note:</b> {ai_report}"
                ]
            elif alert_type == 'bargain':
                title = "🔥 VIP Deal Found!"
                msg_ui = f"Hot deal found! {data.get('clean_price', 'N/A')} PLN in {data.get('location', 'Unknown')}"
                content_lines = [
                    f"We found a highly profitable property matching your criteria.",
                    f"<b>Location:</b> {data.get('location', 'Unknown')}",
                    f"<b>Price:</b> {data.get('clean_price', 'N/A')} PLN",
                    f"<b>AI Note:</b> {ai_report}"
                ]
            else:
                return

            if self.email_manager:
                html_body = self.email_manager.create_html_template(title, content_lines, item['url'])

            for email in tracked_users:
                self.db.add_notification(email, msg_ui)

                if self.email_manager:
                    self.email_manager.send_user_email(email, title, html_body)

        except Exception as e:
            logger.error(f"❌ User Notification Error: {e}")