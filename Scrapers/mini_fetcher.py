import sys
import json
import time
from playwright.sync_api import sync_playwright

def fetch(url):
    try:
        with sync_playwright() as p:
            # 🛡️ LINUX SERVER GÜVENLİ BAŞLATMA AYARLARI
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage", 
                    "--disable-gpu"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 720}
            )
            
            page = context.new_page()
            
            # Stealth yüklemesi varsa kullan
            try:
                from playwright_stealth import stealth
                stealth(page)
            except:
                pass
                
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5) 
            
            # Engel kontrolü
            page_title = page.title()
            if "Just a moment" in page_title or "cloudflare" in page.content().lower():
                browser.close()
                return {"error": "Cloudflare Blocked: Streamlit Cloud IP is restricted by Otodom."}

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
                    if clean_src not in imgs: imgs.append(clean_src)
                if len(imgs) >= 5: break
            
            browser.close()
            return {"description": desc, "image_urls": imgs}
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(fetch(sys.argv[1])))
