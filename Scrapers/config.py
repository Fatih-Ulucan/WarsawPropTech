"""
This file contains all the static configuration settings, 
target lists, and Anti-Bot strategies for the system.
"""

LOCATION_MAP = {
    'Mokotów': 1, 'Praga-Południe': 2, 'Ursynów': 3, 'Wola': 4,
    'Białołęka': 5, 'Bielany': 6, 'Bemowo': 7, 'Targówek': 8,
    'Śródmieście': 9, 'Wawer': 10, 'Ochota': 11, 'Ursus': 12,
    'Praga-Północ': 13, 'Włochy': 14, 'Wilanów': 15, 'Wesoła': 16,
    'Żoliborz': 17, 'Rembertów': 18
}

SCRAPE_TARGETS = [
    {"url_part": "sprzedaz/mieszkanie", "trans_id": 1, "type_id": 1, "label": "🏠 APARTMENT SALE"},
    {"url_part": "wynajem/mieszkanie", "trans_id": 2, "type_id": 1, "label": "🔑 APARTMENT RENT"},
    {"url_part": "sprzedaz/kawalerka", "trans_id": 1, "type_id": 1, "label": "🛋️ STUDIO SALE"},
    {"url_part": "wynajem/kawalerka", "trans_id": 2, "type_id": 1, "label": "🛌 STUDIO RENT"},
    {"url_part": "sprzedaz/dom", "trans_id": 1, "type_id": 2, "label": "🏡 HOUSE SALE"},
    {"url_part": "wynajem/dom", "trans_id": 2, "type_id": 2, "label": "🏠 HOUSE RENT"},
    {"url_part": "sprzedaz/lokal", "trans_id": 1, "type_id": 3, "label": "🏢 COMMERCIAL SALE"},
    {"url_part": "wynajem/lokal", "trans_id": 2, "type_id": 3, "label": "🏬 COMMERCIAL RENT"}
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

CACHE_TTL = 600
QUEUE_FLUSH_LIMIT = 100
MAX_AI_CALLS = 10
MAX_SCANS_BEFORE_REBOOT = 10000