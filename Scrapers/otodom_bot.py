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
            
            print("INFO: Scrolling down to trick 'Lazy Loading'...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            all_listing = page.locator('[data-sentry-component="AdvertCard"]').all()
            
            print(f"INFO: Hurricane Mode active! Found {len(all_listing)} listing on the page. Extracting...\n")
            
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
                    full_url = f"https://www.otodom.pl{raw_url}"
                    
                    print(f"[{index + 1}] {clean_price} PLN | {title} | {location}\n Link: {full_url}\n")
                    
                except Exception:
                    print(f"[{index + 1}] WARNING: Missing data skipped (likely a hidden sponsored ad).")
                    continue
            
            print("="*70 + "\n")
            
        except Exception as e:
            print(f"ERROR: Failed to extract listing data. Details: {e}")
            
        time.sleep(3)
        
        browser.close()
        print("INFO: Operation complete ,browser closed safely.")
        
if __name__ == "__main__":
    print("INFO: System initializing...")
    test_scraper()
    