import requests
import logging
import time
import urllib.parse
from datetime import datetime
from Scrapers.config import CACHE_TTL

logger = logging.getLogger(__name__)

class SupabaseManager:
    def __init__(self, url, key):
        self.url = url.strip("/")
        self.key = key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        self.market_stats_cache = {}
        self.last_fetch_time = 0

    def get_market_averages(self):
        if time.time() - self.last_fetch_time < CACHE_TTL and self.market_stats_cache:
            logger.info("⚡ CACHE: Using cached market data.")
            return self.market_stats_cache

        logger.info("🧠 AI ENGINE: Fetching real-time market averages from Supabase...")
        table_url = f"{self.url}/rest/v1/district_market_stats"
        get_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}"
        }

        try:
            response = requests.get(table_url, headers=get_headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                market_dict = {}
                for row in data:
                    if row.get('avg_price_per_sqm'):
                        key = (row['loc_id'], row['trans_id'], row['type_id'])
                        market_dict[key] = row['avg_price_per_sqm']

                self.market_stats_cache = market_dict
                self.last_fetch_time = time.time()
                logger.info(f"✅ AI ENGINE: Successfully loaded {len(market_dict)} market categories.")
                return market_dict
        except Exception as e:
            logger.error(f"❌ AI ENGINE ERROR: Failed to fetch market stats: {e}")

        return self.market_stats_cache

    def save_listing(self, data):
        table_url = f"{self.url}/rest/v1/listings"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if "status" not in data:
                    data["status"] = "ACTIVE"

                response = requests.post(table_url, json=data, headers=self.headers, timeout=10)
                return response.status_code
            except Exception:
                time.sleep(2)
        return None

    def log_price_history(self, property_id, price_pln):
        if not property_id or not price_pln: return
        table_url = f"{self.url}/rest/v1/price_history"
        hist_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        try:
            requests.post(table_url, json={"property_id": property_id, "price_pln": price_pln}, headers=hist_headers, timeout=5)
        except:
            pass

    def check_existing_listing(self, full_url):
        safe_url = urllib.parse.quote(full_url)
        get_url = f"{self.url}/rest/v1/listings?url_link=eq.{safe_url}&select=id,price_pln,property_id,agency_id,ai_analyzed,alert_sent,status"

        get_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}"
        }

        try:
            resp = requests.get(get_url, headers=get_headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data[0] if data else None
        except Exception:
            pass
        return None

    def update_listing(self, row_id, update_payload):
        patch_url = f"{self.url}/rest/v1/listings?id=eq.{row_id}"
        patch_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        try:
            requests.patch(patch_url, json=update_payload, headers=patch_headers, timeout=5)
        except Exception as e:
            logger.error(f"Price Update Check Error: {e}")

    def mark_as_analyzed(self, full_url):
        safe_url = urllib.parse.quote(full_url)
        patch_url = f"{self.url}/rest/v1/listings?url_link=eq.{safe_url}"
        patch_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        try:
            requests.patch(patch_url, json={"ai_analyzed": True, "alert_sent": True}, headers=patch_headers, timeout=5)
        except:
            pass

    def update_last_seen(self, row_id):
        """Updates the 'updated_at' timestamp and ensures status is ACTIVE."""
        patch_url = f"{self.url}/rest/v1/listings?id=eq.{row_id}"
        patch_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        current_time = datetime.utcnow().isoformat()
        try:
            requests.patch(patch_url, json={"updated_at": current_time, "status": "ACTIVE"}, headers=patch_headers, timeout=5)
        except Exception as e:
            logger.error(f"Last Seen Update Error: {e}")

    def mark_as_sold(self, row_id):
        """Marks a listing as SOLD instead of deleting it to preserve historical data."""
        patch_url = f"{self.url}/rest/v1/listings?id=eq.{row_id}"
        patch_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        current_time = datetime.utcnow().isoformat()
        try:
            requests.patch(patch_url, json={"status": "SOLD", "sold_date": current_time}, headers=patch_headers, timeout=5)
            logger.info(f"🏷️ STATUS UPDATE: Listing ID {row_id} marked as SOLD.")
        except Exception as e:
            logger.error(f"Mark as Sold Error: {e}")