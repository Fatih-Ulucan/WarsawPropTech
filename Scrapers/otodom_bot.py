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
        
        time.sleep(5)
        
        page_title = page.title()
        print(f"SUCCESS: Extracted page title -> {page_title}")
        
        browser.close()
        print("INFO: Operation complete ,browser closed safely.")
        
if __name__ == "__main__":
    print("INFO: System initializing...")
    test_scraper()
    