import os
import requests
import logging
import time
from datetime import datetime, timedelta
from supabase import create_client, Client
from Scrapers.config import CACHE_TTL

logger = logging.getLogger(__name__)

class SupabaseManager:
    def __init__(self, url, key):
        self.url = url.strip("/")
        self.key = key

        self.client: Client = create_client(self.url, self.key)

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

        try:
            response = self.client.table('district_market_stats').select('*').execute()

            market_dict = {}
            for row in response.data:
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

                if response.status_code not in [200, 201, 204, 409]:
                    logger.error(f"❌ SUPABASE DB ERROR DETAILS: {response.text}")

                return response.status_code
            except Exception as e:
                logger.error(f"Network exception in save_listing: {e}")
                time.sleep(2)
        return None

    def log_price_history(self, property_id, price_pln):
        if not property_id or not price_pln: return
        try:
            # Step 1: Find the actual listing_id from the listings table
            res = self.client.table('listings').select('listing_id').eq('property_id', property_id).execute()
            if res.data:
                db_listing_id = res.data[0]['listing_id']

                # Step 2: Insert into price_history using custom DB column names
                payload = {
                    "listing_id": db_listing_id,
                    "new_price_pln": price_pln,
                    "change_date": datetime.utcnow().isoformat() + "Z"
                }
                self.client.table('price_history').insert(payload).execute()
        except Exception as e:
            logger.error(f"❌ PRICE HISTORY DB ERROR: {e}")

    def check_existing_listing(self, full_url):
        try:
            response = self.client.table('listings') \
                .select('listing_id,price_pln,property_id,agency_id,ai_analyzed,alert_sent,status') \
                .eq('url_link', full_url) \
                .execute()

            if response.data:
                row = response.data[0]
                # Map listing_id to id so the scraper logic continues working seamlessly
                row['id'] = row['listing_id']
                return row
        except Exception as e:
            logger.error(f"❌ CHECK LISTING (GET) ERROR: {e}")
        return None

    def update_listing(self, row_id, update_payload):
        try:
            self.client.table('listings').update(update_payload).eq('listing_id', row_id).execute()
        except Exception as e:
            logger.error(f"Price Update Check Error: {e}")

    def mark_as_analyzed(self, full_url):
        try:
            self.client.table('listings').update({"ai_analyzed": True, "alert_sent": True}).eq('url_link', full_url).execute()
        except Exception:
            pass

    def update_last_seen(self, row_id):
        """Updates the 'updated_at' timestamp safely with UTC format and ensures status is ACTIVE."""
        current_time = datetime.utcnow().isoformat() + "Z"
        try:
            self.client.table('listings').update({
                "updated_at": current_time,
                "status": "ACTIVE",
                "is_active": True
            }).eq('listing_id', row_id).execute()
        except Exception as e:
            logger.error(f"Last Seen Update Error: {e}")

    def cleanup_old_listings(self, days_old=1):
        """Marks listings as SOLD if they haven't been updated in 'days_old' days."""
        cutoff_time = (datetime.utcnow() - timedelta(days=days_old)).isoformat() + "Z"
        current_time = datetime.utcnow().isoformat() + "Z"
        try:
            response = self.client.table('listings').update({
                "status": "SOLD",
                "is_active": False,
                "sold_date": current_time
            }).eq('is_active', True).lt('updated_at', cutoff_time).execute()

            return len(response.data) if response.data else 0
        except Exception as e:
            logger.error(f"Cleanup Error: {e}")
            return 0

    def mark_as_sold(self, row_id):
        """Marks a listing as SOLD instead of deleting it to preserve historical data."""
        current_time = datetime.utcnow().isoformat() + "Z"
        try:
            self.client.table('listings').update({"status": "SOLD", "sold_date": current_time, "is_active": False}).eq('listing_id', row_id).execute()
            logger.info(f"🏷️ STATUS UPDATE: Listing ID {row_id} marked as SOLD.")
        except Exception as e:
            logger.error(f"Mark as Sold Error: {e}")

    def add_notification(self, user_email, message):
        """
        Saves an alert to the database for a specific user.
        This will be fetched and displayed as a sidebar alert in the Streamlit Dashboard.
        """
        if not user_email or not message:
            return

        payload = {
            "user_email": user_email,
            "message": message,
            "is_read": False,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        try:
            self.client.table('user_notifications').insert(payload).execute()
            logger.info(f"🔔 UI NOTIFICATION SAVED FOR: {user_email}")
        except Exception as e:
            logger.error(f"❌ Failed to save user UI notification: {e}")