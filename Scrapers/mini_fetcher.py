import sys
import json
import time
from playwright.sync_api import sync_playwright

def fetch(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                extra_http_headers={
                    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8",
                    "Referer": "https://www.google.pl/"
                }
            )
            
            page = context.new_page()
            
            # Use stealth only if available to prevent crashes
            try:
                from playwright_stealth import stealth
                stealth(page)
            except Exception:
                pass
                
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            time.sleep(2)
            page.mouse.wheel(0, 500)
            time.sleep(1)
            
            desc = ""
            selectors = ['[data-cy="adPageAdDescription"]', '[data-testid="ad-description"]', 'article', '.css-1qzszy5']
            for s in selectors:
                if page.locator(s).count() > 0:
                    desc = page.locator(s).first.inner_text()
                    break
            
            imgs = []
            nodes = page.locator('picture source, picture img').all()
            for n in nodes:
                src = n.get_attribute('srcset') or n.get_attribute('src')
                if src and "http" in src and "static" not in src:
                    clean_src = src.split(' ')[0]
                    if clean_src not in imgs:
                        imgs.append(clean_src)
                if len(imgs) >= 5: break
            
            browser.close()
            return {"description": desc, "image_urls": imgs}
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
        result = fetch(target_url)
        print(json.dumps(result))
