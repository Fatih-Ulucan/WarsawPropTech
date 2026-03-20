import os 
import time 
from playwright.sync_api import sync_playwright

def test_scraper():
    print("INFO: Bot is waking up and launching the browser... ")
    
    with sync_playwright() as p:
        
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("INFO: Navigating to Otodom Warsaw real estate listing... ")
        
        page.goto("https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/mazowieckie/warszawa/warszawa/warszawa")
        
        print("INFO: Looking for the Cookie banner...")
        try:
            
            cookie_button = page.locator("#onetrust-accept-btn-handler")
            cookie_button.wait_for(timeout=5000)
            cookie_button.click()
            print("SUCCESS: Cookie banner destroyed! The view is clear.")
        except Exception:
            
            print("INFO: No Cookie banner found, moving on.")
            
            
        print("INFO: Scaning for real estate listing...")
        
        try:
            page.wait_for_selector('[data-sentry-component="AdvertCard"]', timeout=10000)
            
            first_listing = page.locator('[data-sentry-component="AdvertCard"]').first
            
            listing_data = first_listing.inner_text()
            
            print("\n" + "="*50)
            print("BOOM FIRST LISTING CAPTURED:")
            print(listing_data)
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"ERROR: Failed to extract listing data. Details: {e}")
        
        time.sleep(3)
        
        browser.close()
        print("INFO: Operation complete ,browser closed safely.")
        
if __name__ == "__main__":
    print("INFO: System initializing...")
    test_scraper()
    