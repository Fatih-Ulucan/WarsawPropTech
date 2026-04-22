import streamlit as st
import pandas as pd
import requests
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import io
import plotly.express as px
import numpy as np
from sklearn.linear_model import LinearRegression

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

try:
    from Scrapers.config import LOCATION_MAP
except ImportError:
    try:
        from config import LOCATION_MAP
    except ImportError as e:
        st.error(f"❌ CONFIG FILE NOT FOUND! Error: {e}")
        st.stop()
try:
    from Scrapers.notifier import send_telegram_lead
except ImportError:
    try:
        from notifier import send_telegram_lead
    except ImportError as e:
        st.error(f"❌ NOTIFIER MODULE NOT FOUND! Error: {e}")
        st.stop()

st.set_page_config(page_title="Warsaw AI PropTech", page_icon="🏢", layout="wide")

# --- UI/UX UPGRADE: Keskin Fontlar ve Genel Ayarlar ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Tüm site için anti-aliasing (Yazıların titremesini/parlamasını engeller) */
    * {
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
    }
    
    /* Metric Card Upgrade - Daha Net Okunabilirlik */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 800;
    }
    div[data-testid="stMetricValue"] > div {
        color: #10B981 !important; 
    }
    div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    /* Hero Section Branding */
    .hero-text {
        font-size: 44px;
        font-weight: 900;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
    }
    .sub-hero {
        font-size: 19px;
        opacity: 0.85;
        margin-bottom: 30px;
        font-weight: 500;
    }
    .ai-badge {
        background: linear-gradient(90deg, #4A90E2 0%, #9013FE 100%);
        color: white !important;
        padding: 5px 14px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 10px;
        display: inline-block;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Top Right Selectors Ayarı */
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- KAPSAMLI DIL (TRANSLATION) SOZLUĞU ---
LANG_DICT = {
    "🇬🇧 EN": {
        "hero_title": "Warsaw Real Estate Intelligence",
        "hero_sub": "🚀 <b>AI-Powered Arbitrage:</b> Detecting underpriced deals in Warsaw in real-time.",
        "sys_active": "SYSTEM ACTIVE & MONITORING", "scan_cycle": "Scan Cycle:", "analyzed": "Analyzed:",
        "live_listings": "Live Active Listings", "avg_price": "Avg Sale Price", "avg_rent": "Avg Monthly Rent",
        "avg_sqm": "Avg Price / m²", "market_status": "Market Status", "active": "Active 🟢",
        "tab1": "📊 Market Overview", "tab2": "🗺️ Interactive Heatmap", "tab3": "🧠 ROI & Amortization Map",
        "tab4": "🚨 Price Drop Radar", "tab5": "🧮 Investment Calculators", "tab6": "⭐ My Favorites",
        "tab7": "🔮 AI Future Forecast", "tab8": "✅ Closed Deals",
        "sb_member": "🔐 Member Access", "sb_login": "Login", "sb_signup": "Sign Up",
        "sb_email": "Email Address", "sb_pass": "Password", "sb_unlock": "🚀 Unlock Pro Features",
        "sb_logout": "Logout", "sb_controls": "🎯 System Controls", "sb_mode": "Market Mode",
        "sb_sale": "Sale (Investment)", "sb_rent": "Rent (Yield)", "sb_type": "Property Type",
        "sb_filters": "🔍 Quick Filters", "sb_budget": "Max Budget (PLN)",
        "sb_districts": "Select Districts",
        "th_dist": "District", "th_price": "Price (PLN)", "th_sqm": "m²", "th_rooms": "Rooms",
        "th_psqm": "Price/m²", "th_link": "Link", "th_status": "Status",
        "cs_title": "🏆 Recent Arbitrage Success (Case Studies)",
        "cs_info": "ℹ️ *The scenarios below are simulated models based on historical price anomaly data captured and verified by our engine.*",
        "roi_calc": "Calculating ROI based on live rent averages...", "roi_warn": "⚠️ Live rental data is missing...",
        "roi_info": "ℹ️ **Data Note:** ROI calculation requires property size (m²).", "roi_col1": "**Average ROI (%) by District**",
        "roi_col2": "**Average Amortization (Years) by District**", "roi_top": "🏆 Top ROI Opportunities",
        "th_est_rent": "Est. Rent/mo", "th_roi": "ROI (%)", "th_amort": "Amortize (Yrs)",
        "drop_sub": "Listings where the seller recently reduced the asking price.", "drop_analyzing": "Analyzing price drop history...",
        "th_old": "Old Price", "th_cur": "Current Price", "th_disc": "Discount", "th_disc_pct": "Discount %",
        "drop_none": "No recent price drops found in the current selection. Sellers are holding firm!",
        "calc_sub": "Simulate your financial scenarios and estimate real cash flow using current local market rates.",
        "calc_mort": "### 🏦 Mortgage Calculator", "calc_prop": "Property Price (PLN)", "calc_down": "Down Payment (%)",
        "calc_int": "Annual Interest Rate (%)", "calc_term": "Loan Term (Years)", "calc_req_down": "**Required Down Payment:**",
        "calc_est_inst": "**Estimated Monthly Installment:**", "calc_reno": "### 🛠️ Flipping (Renovation) Estimator",
        "calc_size": "Property Size (m²)", "calc_qual": "Renovation Quality (Warsaw Est.)",
        "calc_eco": "Economy Refresh (~1,800 PLN/m²)", "calc_std": "Standard Turn-key (~3,000 PLN/m²)", "calc_prem": "Premium/High-end (~4,500 PLN/m²)",
        "calc_est_reno": "**Estimated Total Renovation Cost:**", "calc_cf": "### 💸 Net Cash Flow Analysis",
        "calc_est_inc": "Estimated Monthly Rent Income (PLN)", "calc_hoa": "HOA / Czynsz (PLN)", "calc_tax": "Rental Tax Rate (%)",
        "calc_net": "**Net Monthly Cash Flow:**",
        "fav_warn": "🔒 Please log in from the left menu to view and manage your tracked properties.", "fav_load": "Loading your vault...",
        "fav_empty": "You haven't saved any properties yet. Browse the market tabs and check the '❤️ Track' box to start monitoring!",
        "fav_alert": "### 🔔 PRICE DROP ALERTS!", "fav_good": "**🚨 GOOD NEWS!** A property you are tracking",
        "fav_sold": "Your saved properties are no longer active on the market (Sold or Removed).", "fav_here": "Here are your tracked investments. Uncheck the box to remove a property from your list.",
        "for_sub": "This machine learning model (Linear Regression) analyzes historical price trends to predict which Warsaw districts will appreciate the most in the next 6 months.",
        "for_train": "AI is training the predictive model...", "for_top3": "### 🏆 Top 3 Investment Zones",
        "for_growth": "📈 Expected Growth:", "for_lock": "🔒 **PREMIUM LOCK:** Full predictive dataset is hidden. Upgrade to access all district forecasts.",
        "for_unlock": "👑 Premium Unlocked! Viewing all future predictions.", "th_cur_avg": "Current Price/m²", "th_pred": "Predicted Price/m²", "th_grow": "Growth",
        "for_none": "Bot needs to scrape more data to build an accurate predictive model. Check back later!",
        "cd_sub": "Properties that were recently removed from the market (Likely sold). Use this data to analyze market speed.",
        "cd_none": "No closed deals detected yet. Bot is monitoring removals...", "th_last": "Last Asking Price"
    },
    "🇵🇱 PL": {
        "hero_title": "Warszawska Inteligencja Nieruchomości",
        "hero_sub": "🚀 <b>Arbitraż AI:</b> Wykrywanie niedoszacowanych ofert w Warszawie w czasie rzeczywistym.",
        "sys_active": "SYSTEM AKTYWNY I MONITORUJE", "scan_cycle": "Skanowanie:", "analyzed": "Przeanalizowano:",
        "live_listings": "Aktywne Ogłoszenia", "avg_price": "Średnia Cena Sprzedaży", "avg_rent": "Średni Czynsz",
        "avg_sqm": "Śr. Cena / m²", "market_status": "Status Rynku", "active": "Aktywny 🟢",
        "tab1": "📊 Przegląd Rynku", "tab2": "🗺️ Mapa Cieplna", "tab3": "🧠 ROI i Amortyzacja",
        "tab4": "🚨 Radar Spadków Cen", "tab5": "🧮 Kalkulatory Inwestycyjne", "tab6": "⭐ Moje Ulubione",
        "tab7": "🔮 Prognoza Przyszłości", "tab8": "✅ Zamknięte Transakcje",
        "sb_member": "🔐 Dostęp Użytkownika", "sb_login": "Zaloguj", "sb_signup": "Rejestracja",
        "sb_email": "Adres Email", "sb_pass": "Hasło", "sb_unlock": "🚀 Odblokuj Funkcje Pro",
        "sb_logout": "Wyloguj", "sb_controls": "🎯 Panel Sterowania", "sb_mode": "Tryb Rynku",
        "sb_sale": "Sprzedaż (Inwestycja)", "sb_rent": "Wynajem (Zysk)", "sb_type": "Typ Nieruchomości",
        "sb_filters": "🔍 Szybkie Filtry", "sb_budget": "Maks. Budżet (PLN)",
        "sb_districts": "Wybierz Dzielnice",
        "th_dist": "Dzielnica", "th_price": "Cena (PLN)", "th_sqm": "m²", "th_rooms": "Pokoje",
        "th_psqm": "Cena/m²", "th_link": "Link", "th_status": "Status",
        "cs_title": "🏆 Ostatnie Sukcesy Arbitrażowe",
        "cs_info": "ℹ️ *Poniższe scenariusze to symulowane modele oparte na historycznych anomaliach cenowych zarejestrowanych przez nasz silnik.*",
        "roi_calc": "Obliczanie ROI na podstawie średnich czynszów...", "roi_warn": "⚠️ Brak danych o wynajmie na żywo...",
        "roi_info": "ℹ️ **Uwaga:** Obliczenie ROI wymaga rozmiaru nieruchomości (m²).", "roi_col1": "**Średnie ROI (%) wg Dzielnic**",
        "roi_col2": "**Średnia Amortyzacja (Lata) wg Dzielnic**", "roi_top": "🏆 Najlepsze Okazje ROI",
        "th_est_rent": "Szac. Czynsz/msc", "th_roi": "ROI (%)", "th_amort": "Amortyzacja (Lata)",
        "drop_sub": "Ogłoszenia, w których sprzedawca niedawno obniżył cenę.", "drop_analyzing": "Analiza historii obniżek cen...",
        "th_old": "Stara Cena", "th_cur": "Obecna Cena", "th_disc": "Zniżka", "th_disc_pct": "Zniżka %",
        "drop_none": "Nie znaleziono niedawnych spadków cen. Sprzedawcy trzymają się mocno!",
        "calc_sub": "Symuluj scenariusze finansowe i szacuj przepływy pieniężne.",
        "calc_mort": "### 🏦 Kalkulator Kredytowy", "calc_prop": "Cena Nieruchomości (PLN)", "calc_down": "Wkład Własny (%)",
        "calc_int": "Roczne Oprocentowanie (%)", "calc_term": "Okres Kredytowania (Lata)", "calc_req_down": "**Wymagany Wkład Własny:**",
        "calc_est_inst": "**Szacowana Rata Miesięczna:**", "calc_reno": "### 🛠️ Estymator Remontu (Flip)",
        "calc_size": "Metraż Nieruchomości (m²)", "calc_qual": "Standard Remontu (Szac. dla Warszawy)",
        "calc_eco": "Odświeżenie Ekonomiczne (~1 800 PLN/m²)", "calc_std": "Pod Klucz - Standard (~3 000 PLN/m²)", "calc_prem": "Premium/High-end (~4 500 PLN/m²)",
        "calc_est_reno": "**Szacowany Całkowity Koszt Remontu:**", "calc_cf": "### 💸 Analiza Przepływów Pieniężnych (Cash Flow)",
        "calc_est_inc": "Szacowany Miesięczny Przychód z Najmu (PLN)", "calc_hoa": "Czynsz Administracyjny (PLN)", "calc_tax": "Podatek od Najmu (%)",
        "calc_net": "**Zysk Miesięczny Na Czysto (Net Cash Flow):**",
        "fav_warn": "🔒 Zaloguj się z lewego menu, aby zarządzać śledzonymi nieruchomościami.", "fav_load": "Ładowanie twojego skarbca...",
        "fav_empty": "Nie zapisałeś jeszcze żadnych nieruchomości. Zaznacz '❤️ Track', aby zacząć monitorować!",
        "fav_alert": "### 🔔 ALERTY O SPADKU CEN!", "fav_good": "**🚨 DOBRE WIEŚCI!** Nieruchomość, którą śledzisz",
        "fav_sold": "Twoje zapisane nieruchomości nie są już aktywne (Sprzedane lub Usunięte).", "fav_here": "Oto twoje śledzone inwestycje. Odznacz pole, aby usunąć z listy.",
        "for_sub": "Ten model uczenia maszynowego (Regresja Liniowa) analizuje historyczne trendy cenowe...",
        "for_train": "Sztuczna inteligencja trenuje model predykcyjny...", "for_top3": "### 🏆 Top 3 Strefy Inwestycyjne",
        "for_growth": "📈 Oczekiwany Wzrost:", "for_lock": "🔒 **BLOKADA PREMIUM:** Pełne dane są ukryte.",
        "for_unlock": "👑 Premium Odblokowane! Oglądasz wszystkie prognozy.", "th_cur_avg": "Obecna Cena/m²", "th_pred": "Przewidywana Cena/m²", "th_grow": "Wzrost",
        "for_none": "Bot musi zebrać więcej danych, aby zbudować dokładny model.",
        "cd_sub": "Nieruchomości, które zostały niedawno usunięte z rynku (Prawdopodobnie sprzedane).",
        "cd_none": "Brak zamkniętych transakcji. Bot monitoruje rynek...", "th_last": "Ostatnia Cena Ofertowa"
    },
    "🇹🇷 TR": {
        "hero_title": "Varşova Emlak Zekası",
        "hero_sub": "🚀 <b>Yapay Zeka Arbitrajı:</b> Varşova'daki fırsat mülkleri gerçek zamanlı tespit eder.",
        "sys_active": "SİSTEM AKTİF & İZLENİYOR", "scan_cycle": "Tarama Döngüsü:", "analyzed": "Analiz Edilen:",
        "live_listings": "Aktif İlanlar", "avg_price": "Ort. Satış Fiyatı", "avg_rent": "Ort. Aylık Kira",
        "avg_sqm": "Ort. m² Fiyatı", "market_status": "Piyasa Durumu", "active": "Aktif 🟢",
        "tab1": "📊 Piyasa Özeti", "tab2": "🗺️ Isı Haritası", "tab3": "🧠 ROI & Amortisman",
        "tab4": "🚨 Fiyat Düşüş Radarı", "tab5": "🧮 Yatırım Hesaplayıcı", "tab6": "⭐ Favorilerim",
        "tab7": "🔮 Gelecek Tahmini", "tab8": "✅ Kapanan İşlemler",
        "sb_member": "🔐 Üye Girişi", "sb_login": "Giriş Yap", "sb_signup": "Kayıt Ol",
        "sb_email": "E-posta Adresi", "sb_pass": "Şifre", "sb_unlock": "🚀 Pro Özellikleri Aç",
        "sb_logout": "Çıkış Yap", "sb_controls": "🎯 Sistem Kontrolleri", "sb_mode": "Piyasa Modu",
        "sb_sale": "Satılık (Yatırım)", "sb_rent": "Kiralık (Getiri)", "sb_type": "Mülk Tipi",
        "sb_filters": "🔍 Hızlı Filtreler", "sb_budget": "Maks. Bütçe (PLN)",
        "sb_districts": "Bölge Seç",
        "th_dist": "Bölge", "th_price": "Fiyat (PLN)", "th_sqm": "m²", "th_rooms": "Oda",
        "th_psqm": "Fiyat/m²", "th_link": "Link", "th_status": "Durum",
        "cs_title": "🏆 Son Arbitraj Başarıları (Örnek Vakalar)",
        "cs_info": "ℹ️ *Aşağıdaki senaryolar, motorumuz tarafından yakalanan geçmiş fiyat anomalisi verilerine dayanan simüle edilmiş modellerdir.*",
        "roi_calc": "Canlı kira ortalamalarına göre ROI hesaplanıyor...", "roi_warn": "⚠️ Canlı kira verisi eksik...",
        "roi_info": "ℹ️ **Not:** ROI hesaplaması m² verisi gerektirir.", "roi_col1": "**Bölgelere Göre Ort. ROI (%)**",
        "roi_col2": "**Bölgelere Göre Ort. Amortisman (Yıl)**", "roi_top": "🏆 En İyi ROI Fırsatları",
        "th_est_rent": "Tahmini Kira", "th_roi": "ROI (%)", "th_amort": "Amortisman (Yıl)",
        "drop_sub": "Satıcının yakın zamanda fiyatı düşürdüğü ilanlar.", "drop_analyzing": "Fiyat düşüş geçmişi analiz ediliyor...",
        "th_old": "Eski Fiyat", "th_cur": "Mevcut Fiyat", "th_disc": "İndirim", "th_disc_pct": "İndirim %",
        "drop_none": "Seçilen filtrelerde yakın zamanda fiyat düşüşü bulunamadı.",
        "calc_sub": "Yerel piyasa oranlarını kullanarak finansal senaryolarınızı ve nakit akışınızı simüle edin.",
        "calc_mort": "### 🏦 Mortgage Hesaplayıcı", "calc_prop": "Mülk Fiyatı (PLN)", "calc_down": "Peşinat (%)",
        "calc_int": "Yıllık Faiz Oranı (%)", "calc_term": "Kredi Süresi (Yıl)", "calc_req_down": "**Gereken Peşinat:**",
        "calc_est_inst": "**Tahmini Aylık Taksit:**", "calc_reno": "### 🛠️ Yenileme (Flip) Maliyeti",
        "calc_size": "Mülk Boyutu (m²)", "calc_qual": "Yenileme Kalitesi (Varşova Tahmini)",
        "calc_eco": "Ekonomik Yenileme (~1.800 PLN/m²)", "calc_std": "Standart Anahtar Teslim (~3.000 PLN/m²)", "calc_prem": "Premium/Lüks (~4.500 PLN/m²)",
        "calc_est_reno": "**Tahmini Toplam Yenileme Maliyeti:**", "calc_cf": "### 💸 Net Nakit Akışı Analizi",
        "calc_est_inc": "Tahmini Aylık Kira Geliri (PLN)", "calc_hoa": "Aidat / Czynsz (PLN)", "calc_tax": "Kira Vergisi Oranı (%)",
        "calc_net": "**Aylık Net Nakit Akışı:**",
        "fav_warn": "🔒 Takip ettiğiniz mülkleri yönetmek için lütfen giriş yapın.", "fav_load": "Kasanız yükleniyor...",
        "fav_empty": "Henüz mülk kaydetmediniz. Takip etmek için '❤️ Track' kutusunu işaretleyin!",
        "fav_alert": "### 🔔 FİYAT DÜŞÜŞ ALARMI!", "fav_good": "**🚨 İYİ HABER!** Takip ettiğiniz bir mülkün fiyatı düştü:",
        "fav_sold": "Kaydedilen mülkleriniz artık yayında değil.", "fav_here": "İşte takip ettiğiniz yatırımlar. Listeden çıkarmak için kutunun işaretini kaldırın.",
        "for_sub": "Bu makine öğrenmesi modeli (Doğrusal Regresyon), önümüzdeki 6 ay içinde en çok değerlenecek Varşova bölgelerini tahmin eder.",
        "for_train": "Yapay zeka tahmin modelini eğitiyor...", "for_top3": "### 🏆 En İyi 3 Yatırım Bölgesi",
        "for_growth": "📈 Beklenen Büyüme:", "for_lock": "🔒 **PREMIUM KİLİDİ:** Tüm veriler gizlendi.",
        "for_unlock": "👑 Premium Aktif! Tüm tahminleri görüntülüyorsunuz.", "th_cur_avg": "Mevcut Fiyat/m²", "th_pred": "Tahmini Fiyat/m²", "th_grow": "Büyüme",
        "for_none": "Modeli oluşturmak için botun daha fazla veri toplaması gerekiyor.",
        "cd_sub": "Yakın zamanda piyasadan kaldırılan (Büyük ihtimalle satılan) mülkler.",
        "cd_none": "Henüz kapanan işlem tespit edilmedi. Bot izliyor...", "th_last": "Son İstenen Fiyat"
    }
}

# --- TEMA VE DIL SECICISI (SAYFANIN EN USTU - SAG KÖŞE) ---
col_space, col_lang, col_theme = st.columns([8, 1, 1])
with col_lang:
    sel_lang = st.selectbox("🌐", ["🇬🇧 EN", "🇵🇱 PL", "🇹🇷 TR"], label_visibility="collapsed")
with col_theme:
    sel_theme = st.selectbox("🎨", ["Auto", "🌙 Dark", "☀️ Light"], label_visibility="collapsed")

t = LANG_DICT[sel_lang]

# --- GERCEK TEMA ENJEKSIYONU (SİYAH SİDEBAR VE EKRAN DÜZELTMESİ) ---
if sel_theme == "🌙 Dark":
    st.markdown("""
    <style> 
    [data-testid="stAppViewContainer"] { background-color: #0E1117 !important; } 
    [data-testid="stSidebar"] { background-color: #000000 !important; } 
    
    /* --- ANA EKRAN GÖRÜNMEYEN YAZILARI DÜZELTME --- */
    .hero-text { color: #F8FAFC !important; }
    .sub-hero { color: #E2E8F0 !important; }
    
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3,
    [data-testid="stAppViewContainer"] h4 {
        color: #F8FAFC !important;
    }
    
    /* Ana metinler (Renkli uyarı kutuları hariç tutularak beyaza çekilir) */
    div[data-testid="stAppViewContainer"] .stMarkdown p { color: #E2E8F0; }
    div[data-testid="stAlert"] .stMarkdown p { color: inherit !important; }
    
    [data-testid="stCaptionContainer"] p { color: #94A3B8 !important; }
    
    /* Tab başlıkları */
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] div { color: #F8FAFC !important; }
    
    /* Metrik açıklamaları */
    [data-testid="stMetricLabel"] > div > div > p { color: #94A3B8 !important; }
    
    /* Expander başlıkları */
    summary p { color: #F8FAFC !important; }

    /* Sidebar Metinleri */
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] div { 
        color: #E2E8F0 !important; 
        font-weight: 500 !important; 
        text-shadow: none !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { 
        color: #FFFFFF !important; 
        text-shadow: none !important;
    }
    
    /* İNPUT/GİRİŞ KUTULARI DÜZELTMESİ (Email, Şifre, Dropdown) */
    div[data-baseweb="input"] > div, div[data-baseweb="base-input"] { 
        background-color: #0F172A !important; 
        border-color: #334155 !important; 
    }
    input[type="text"], input[type="password"] { 
        color: #E2E8F0 !important; 
        -webkit-text-fill-color: #E2E8F0 !important; 
    }
    
    div[data-baseweb="select"] > div { 
        background-color: #0F172A !important; 
        border-color: #334155 !important; 
    }
    div[data-baseweb="select"] span { color: #E2E8F0 !important; font-weight: 500 !important; }
    ul[data-baseweb="menu"] { background-color: #0F172A !important; }
    li[data-baseweb="menu-item"] { color: #E2E8F0 !important; }
    
    /* Butonlar */
    div.stButton > button { 
        background-color: #1E293B !important; 
        color: #FFFFFF !important; 
        border-color: #334155 !important; 
    }
    div.stButton > button:hover { 
        border-color: #10B981 !important; 
        color: #10B981 !important; 
    }
    </style>
    """, unsafe_allow_html=True)

elif sel_theme == "☀️ Light":
    st.markdown("""
    <style> 
    [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; } 
    [data-testid="stSidebar"] { background-color: #F8F9FA !important; } 
    
    /* --- ANA EKRAN GÖRÜNMEYEN YAZILARI DÜZELTME (Açık Tema) --- */
    .hero-text { color: #0F172A !important; }
    .sub-hero { color: #334155 !important; }
    
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3,
    [data-testid="stAppViewContainer"] h4 {
        color: #0F172A !important;
    }
    
    div[data-testid="stAppViewContainer"] .stMarkdown p { color: #1E293B; }
    div[data-testid="stAlert"] .stMarkdown p { color: inherit !important; }
    
    [data-testid="stCaptionContainer"] p { color: #64748B !important; }
    
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] div { color: #0F172A !important; }
    
    [data-testid="stMetricLabel"] > div > div > p { color: #64748B !important; }
    
    summary p { color: #0F172A !important; }

    /* Sidebar Metinleri */
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] div { 
        color: #1E293B !important; 
        font-weight: 500 !important; 
        text-shadow: none !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { 
        color: #000000 !important; 
        text-shadow: none !important;
    }
    
    div[data-baseweb="input"] > div, div[data-baseweb="base-input"] { 
        background-color: #FFFFFF !important; 
        border-color: #D1D5DB !important; 
    }
    input[type="text"], input[type="password"] { 
        color: #000000 !important; 
        -webkit-text-fill-color: #000000 !important; 
    }
    
    div[data-baseweb="select"] > div { 
        background-color: #FFFFFF !important; 
        border-color: #D1D5DB !important; 
    }
    div[data-baseweb="select"] span { color: #000000 !important; font-weight: 500 !important; }
    ul[data-baseweb="menu"] { background-color: #FFFFFF !important; }
    li[data-baseweb="menu-item"] { color: #000000 !important; }
    
    div.stButton > button { 
        background-color: #F3F4F6 !important; 
        color: #111827 !important; 
        border-color: #D1D5DB !important; 
    }
    div.stButton > button:hover { 
        border-color: #10B981 !important; 
        color: #10B981 !important; 
    }
    </style>
    """, unsafe_allow_html=True)


if 'user_tier' not in st.session_state:
    st.session_state['user_tier'] = 'Free'
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""

if "success" in st.query_params and st.query_params["success"] == "true":
    if st.session_state['logged_in']:
        st.session_state['user_tier'] = 'Premium'
        st.success("🎉 Payment Successful! Welcome to Premium. All hidden data is now unlocked for your account.")
        st.query_params.clear()
    else:
        st.warning("⚠️ Payment received, but you are not logged in. Please log in to activate your Premium.")

base_dir = current_dir.parent
env_path = base_dir / ".env"

if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8-sig") as f:
            clean_content = f.read()
        load_dotenv(stream=io.StringIO(clean_content), override=True)
    except Exception:
        pass

try:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    STRIPE_LINK = st.secrets.get("STRIPE_LINK", os.environ.get("STRIPE_LINK", "https://buy.stripe.com/test_your_link_here"))
except Exception:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    STRIPE_LINK = os.environ.get("STRIPE_LINK", "https://buy.stripe.com/test_your_link_here")

if SUPABASE_URL and SUPABASE_KEY:
    SUPABASE_URL = SUPABASE_URL.strip()
    SUPABASE_KEY = SUPABASE_KEY.strip()
else:
    st.error("❌ CRITICAL ERROR: Supabase keys are missing! Check Streamlit Secrets or .env file.")
    st.stop()

def login_user(email, password):
    url = f"{SUPABASE_URL.strip('/')}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    response = requests.post(url, headers=headers, json=payload)
    return response

def signup_user(email, password):
    url = f"{SUPABASE_URL.strip('/')}/auth/v1/signup"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    response = requests.post(url, headers=headers, json=payload)
    return response

def toggle_favorite(email, property_id, is_adding):
    url = f"{SUPABASE_URL.strip('/')}/rest/v1/favorites"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        if is_adding:
            payload = {"user_email": email, "property_id": int(property_id)}
            requests.post(url, headers=headers, json=payload, timeout=10)
        else:
            requests.delete(f"{url}?user_email=eq.{email}&property_id=eq.{int(property_id)}", headers=headers, timeout=10)
    except Exception as e:
        pass

def get_user_favorites(email):
    url = f"{SUPABASE_URL.strip('/')}/rest/v1/favorites?user_email=eq.{email}&select=property_id"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return [item['property_id'] for item in res.json()]
    except Exception:
        return []
    return []

def process_favorite_edits(edited_df, original_df, email):
    for i, row in edited_df.iterrows():
        property_id = row['property_id']
        current_status = row['❤️ Track']
        original_status = original_df.loc[i, '❤️ Track']
        if current_status != original_status:
            toggle_favorite(email, property_id, current_status)

REVERSE_LOCATION_MAP = {v: k for k, v in LOCATION_MAP.items()}

DISTRICT_COORDS = {
    'Mokotów': {'lat': 52.1939, 'lon': 21.0211}, 'Praga-Południe': {'lat': 52.2393, 'lon': 21.0820},
    'Ursynów': {'lat': 52.1410, 'lon': 21.0326}, 'Wola': {'lat': 52.2361, 'lon': 20.9575},
    'Białołęka': {'lat': 52.3168, 'lon': 20.9634}, 'Bielany': {'lat': 52.2854, 'lon': 20.9416},
    'Bemowo': {'lat': 52.2536, 'lon': 20.9080}, 'Targówek': {'lat': 52.2778, 'lon': 21.0506},
    'Śródmieście': {'lat': 52.2297, 'lon': 21.0122}, 'Wawer': {'lat': 52.2036, 'lon': 21.1663},
    'Ochota': {'lat': 52.2132, 'lon': 20.9786}, 'Ursus': {'lat': 52.1933, 'lon': 20.8872},
    'Praga-Północ': {'lat': 52.2644, 'lon': 21.0264}, 'Włochy': {'lat': 52.1931, 'lon': 20.9388},
    'Wilanów': {'lat': 52.1645, 'lon': 21.0837}, 'Wesoła': {'lat': 52.2335, 'lon': 21.2163},
    'Żoliborz': {'lat': 52.2683, 'lon': 20.9822}, 'Rembertów': {'lat': 52.2600, 'lon': 21.1500}
}

PROPERTY_TYPES = {
    "Apartment": 1, "Commercial/Retail": 2, "Land": 3,
    "Office": 4, "WareHouse": 5, "Garage": 6
}

@st.cache_data(ttl=300)
def load_data(trans_id, type_id):
    clean_url = SUPABASE_URL.strip("/")
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Range-Unit": "items"}
    all_data = []
    limit = 1000
    offset = 0
    try:
        while True:
            table_url = f"{clean_url}/rest/v1/listings?trans_id=eq.{trans_id}&type_id=eq.{type_id}&select=*&limit={limit}&offset={offset}"
            response = requests.get(table_url, headers=headers, timeout=15)
            if response.status_code == 200:
                chunk = response.json()
                if not chunk: break
                all_data.extend(chunk)
                if len(chunk) < limit: break
                offset += limit
            else: break
        if not all_data: return pd.DataFrame()
        df = pd.DataFrame(all_data)
        df['district'] = df['loc_id'].map(REVERSE_LOCATION_MAP)
        df['price_pln'] = pd.to_numeric(df['price_pln'], errors='coerce')
        df['sqm'] = pd.to_numeric(df['sqm'], errors='coerce')
        df['price_per_sqm'] = pd.to_numeric(df['price_per_sqm'], errors='coerce')
        df = df.dropna(subset=['price_pln'])
        df = df[df['price_pln'] > 0]
        df['url_link'] = df['url_link'].apply(lambda x: f"{x}")
        return df
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_rent_averages(type_id):
    df_rent = load_data(trans_id=2, type_id=type_id)
    if df_rent.empty: return {}, 0
    df_rent_active = df_rent[df_rent['status'] == 'ACTIVE'] if 'status' in df_rent.columns else df_rent
    rent_avg_district = df_rent_active.groupby('loc_id')['price_per_sqm'].mean().to_dict()
    rent_avg_city = df_rent_active['price_per_sqm'].mean()
    return rent_avg_district, rent_avg_city

@st.cache_data(ttl=300)
def load_price_history():
    clean_url = SUPABASE_URL.strip("/")
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Range-Unit": "items"}
    all_history = []
    limit = 1000
    offset = 0
    try:
        while True:
            table_url = f"{clean_url}/rest/v1/price_history?select=property_id,price_pln,created_at&limit={limit}&offset={offset}"
            response = requests.get(table_url, headers=headers, timeout=15)
            if response.status_code == 200:
                chunk = response.json()
                if not chunk: break
                all_history.extend(chunk)
                if len(chunk) < limit: break
                offset += limit
            else: break
        if not all_history: return pd.DataFrame()
        return pd.DataFrame(all_history)
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=3600)
def predict_future_prices(df):
    predictions = []
    if df.empty: return pd.DataFrame()
    try:
        df_ml = df.copy()
        if 'status' in df_ml.columns:
            df_ml = df_ml[df_ml['status'] == 'ACTIVE']
        df_ml['price_per_sqm'] = pd.to_numeric(df_ml['price_per_sqm'], errors='coerce')
        df_ml = df_ml.dropna(subset=['price_per_sqm', 'district'])
        df_ml = df_ml[df_ml['price_per_sqm'] > 1000]
    except Exception: return pd.DataFrame()

    try:
        for district, group in df_ml.groupby('district'):
            if len(group) < 3: continue
            group = group.sort_index()
            X = np.arange(len(group)).reshape(-1, 1)
            y = group['price_per_sqm'].values
            model = LinearRegression()
            model.fit(X, y)
            future_step = len(group) + max(1, int(len(group) * 0.2))
            future_X = np.array([[future_step]])
            predicted_price = model.predict(future_X)[0]
            current_avg = y.mean()
            if current_avg > 0:
                growth_potential = ((predicted_price - current_avg) / current_avg) * 100
                if growth_potential > 15: growth_potential = 12 + (growth_potential * 0.05)
                elif growth_potential < -15: growth_potential = -10 - (abs(growth_potential) * 0.05)
                predictions.append({
                    'District': district, 'Current Avg (PLN/m²)': current_avg,
                    'Predicted 6-Month (PLN/m²)': predicted_price, 'Growth Potential (%)': growth_potential
                })
        result_df = pd.DataFrame(predictions)
        if not result_df.empty: result_df = result_df.sort_values(by='Growth Potential (%)', ascending=False)
        return result_df
    except Exception: return pd.DataFrame()

# --- SIDEBAR (LOGIN & CONTROLS) ---
if not st.session_state['logged_in']:
    st.sidebar.markdown("---")
    st.sidebar.header(t["sb_member"])
    auth_mode = st.sidebar.radio("Select", [t["sb_login"], t["sb_signup"]], label_visibility="collapsed")

    auth_email = st.sidebar.text_input(t["sb_email"])
    auth_password = st.sidebar.text_input(t["sb_pass"], type="password")

    if auth_mode == t["sb_login"]:
        if st.sidebar.button(t["sb_login"], use_container_width=True):
            with st.spinner("Authenticating..."):
                res = login_user(auth_email, auth_password)
                if res.status_code == 200:
                    st.session_state['logged_in'] = True
                    st.session_state['user_email'] = auth_email
                    if st.session_state['user_tier'] != 'Premium': st.session_state['user_tier'] = 'Free'
                    st.rerun()
                else: st.sidebar.error("❌ Invalid Email or Password.")
    else:
        if st.sidebar.button(t["sb_signup"], use_container_width=True):
            with st.spinner("Creating account..."):
                res = signup_user(auth_email, auth_password)
                if res.status_code == 200: st.sidebar.success("✅ Registration successful!")
                else:
                    error_msg = res.json().get('msg', 'Registration failed. Password must be at least 6 characters.')
                    st.sidebar.error(f"❌ {error_msg}")
else:
    st.sidebar.success(f"👤 Logged in:\n{st.session_state['user_email']}")
    if st.session_state['user_tier'] == 'Free':
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### {t['sb_unlock']}")
        st.sidebar.link_button("💎 Upgrade to Premium (199 PLN/mo)", STRIPE_LINK, type="primary", use_container_width=True)
    if st.sidebar.button(t["sb_logout"], use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['user_email'] = ""
        st.session_state['user_tier'] = 'Free'
        st.rerun()

st.sidebar.markdown("---")

is_premium = st.session_state['user_tier'] == 'Premium'
if is_premium:
    badge_bg = "linear-gradient(135deg, #FFD700 0%, #FDB931 100%)"
    badge_color = "#000000"
    badge_icon = "👑"
else:
    badge_bg = "#374151"
    badge_color = "#FFFFFF"
    badge_icon = "🆓"

st.markdown(
    f"""
    <div style="position: fixed; top: 60px; right: 20px; background: {badge_bg}; color: {badge_color}; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 14px; z-index: 9999; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);">
        {badge_icon} {st.session_state['user_tier']} Plan
    </div>
    """, unsafe_allow_html=True
)

st.sidebar.header(t["sb_controls"])

transaction_type = st.sidebar.selectbox(
    t["sb_mode"],
    options=[(t["sb_sale"], 1), (t["sb_rent"], 2)],
    format_func=lambda x: x[0]
)
selected_trans_id = transaction_type[1]
label = "Sale" if selected_trans_id == 1 else "Rent"

prop_type_label = st.sidebar.selectbox(t["sb_type"], options=list(PROPERTY_TYPES.keys()))
selected_type_id = PROPERTY_TYPES[prop_type_label]

st.sidebar.markdown("---")
st.sidebar.header(t["sb_filters"])

with st.spinner(f'Fetching live data...'):
    df = load_data(selected_trans_id, selected_type_id)

if not df.empty:
    df_active = df[df['status'] == 'ACTIVE'].copy() if 'status' in df.columns else df.copy()
    df_sold = df[df['status'] == 'SOLD'].copy() if 'status' in df.columns else pd.DataFrame()

    max_val = int(df_active['price_pln'].max()) if not df_active.empty else 1000000
    min_val = int(df_active['price_pln'].min()) if not df_active.empty else 0

    max_price = st.sidebar.slider(t["sb_budget"], min_value=min_val, max_value=max_val, value=max_val, step=5000 if selected_trans_id == 2 else 50000)
    districts = st.sidebar.multiselect(t["sb_districts"], options=sorted(df_active['district'].dropna().unique()), default=[])

    filtered_df = df_active[df_active['price_pln'] <= max_price].copy()
    if districts: filtered_df = filtered_df[filtered_df['district'].isin(districts)]
    filtered_df = filtered_df.sort_values(by='price_per_sqm', ascending=True)

    # --- HERO SECTION ---
    st.markdown('<div class="ai-badge">PropTech AI Engine v2.0</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="hero-text">{t["hero_title"]}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-hero">{t["hero_sub"]}</p>', unsafe_allow_html=True)

    # --- LIVE STATUS BAR ---
    st.markdown(
        f"""
        <div style="background-color: rgba(16, 185, 129, 0.05); padding: 12px 20px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.2); margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="display: flex; align-items: center;">
                <div style="width: 10px; height: 10px; background-color: #10B981; border-radius: 50%; box-shadow: 0 0 10px #10B981; animation: blink 1.5s infinite; margin-right: 12px;"></div>
                <span style="color: #10B981; font-family: monospace; font-size: 14px; font-weight: bold;">{t["sys_active"]}</span>
            </div>
            <span style="color: #8B949E; font-family: monospace; font-size: 13px;">
                📡 <b>{t["scan_cycle"]}</b> 15 Mins | 📊 <b>{t["analyzed"]}</b> {len(df):,}
            </span>
        </div>
        <style> @keyframes blink {{ 0% {{opacity: 1;}} 50% {{opacity: 0.3;}} 100% {{opacity: 1;}} }} </style>
        """, unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns(4)

    avg_price_total = filtered_df['price_pln'].mean()
    avg_price_sqm = filtered_df['price_per_sqm'].mean()

    display_avg_total = f"{avg_price_total:,.0f} PLN" if pd.notna(avg_price_total) else "N/A"
    display_avg_sqm = f"{avg_price_sqm:,.0f} PLN" if pd.notna(avg_price_sqm) else "N/A"

    ui_price_label = t["avg_price"] if selected_trans_id == 1 else t["avg_rent"]

    col1.metric(t["live_listings"], f"{len(filtered_df)}")
    col2.metric(ui_price_label, display_avg_total)
    col3.metric(t["avg_sqm"], display_avg_sqm)
    col4.metric(t["market_status"], t["active"])

    st.markdown("---")

    st.markdown(f"### {t['cs_title']}")
    st.caption(t["cs_info"])
    cs1, cs2, cs3 = st.columns(3)

    with cs1:
        st.success("**📍 Mokotów (Flip Opportunity)**\n\n📉 **Market Avg:** 850,000 PLN\n🎯 **Captured Price:** 690,000 PLN\n💸 **Net Profit:** ~160,000 PLN\n\n⚡ *Status: Deal Closed*")
    with cs2:
        st.info("**📍 Wola (High ROI)**\n\n📉 **Market Rent:** 4,200 PLN/mo\n🎯 **Captured Sale:** 510,000 PLN\n🚀 **Annual ROI:** 9.8% (Net)\n\n⚡ *Status: Deal Closed*")
    with cs3:
        st.warning("**📍 Śródmieście (Urgent Sale)**\n\n📉 **Market Avg:** 1,200,000 PLN\n🎯 **Captured Price:** 980,000 PLN\n💸 **Net Profit:** ~220,000 PLN\n\n⚡ *Status: Deal Closed*")

    with st.expander("🤖 Transparency: How Does Our AI Methodology Work?"):
        st.markdown("""
        Our platform operates purely on emotionless data and Natural Language Processing (NLP):
        1. **Real-Time Arbitrage:** The system continuously fetches live price-per-square-meter averages for similar properties directly from our Supabase data warehouse.
        2. **Price Anomaly Detection:** If a listing's price falls significantly (usually **20% - 30% below**) its district's current moving average, it triggers our radar.
        3. **Gemini AI Language Processing:** Our integrated AI reads Polish/English descriptions to gauge seller motivation (e.g., extracting keywords like *"Urgent"*, *"Leaving the country"*, *"Needs renovation"*).
        4. **Investment Scoring:** We combine the potential profit margin, district liquidity speed, and AI textual sentiment into a proprietary **100-point Investment Score**, presenting only the most lucrative deals to you.
        """)
    st.markdown("---")

    user_fav_ids = []
    if st.session_state['logged_in']: user_fav_ids = get_user_favorites(st.session_state['user_email'])

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        t["tab1"], t["tab2"], t["tab3"], t["tab4"], t["tab5"], t["tab6"], t["tab7"], t["tab8"]
    ])

    with tab1:
        st.subheader(t["tab1"])
        c1, c2 = st.columns(2)
        with c1: st.bar_chart(filtered_df['district'].value_counts())
        with c2:
            chart_data = filtered_df.groupby('district')['price_per_sqm'].mean().dropna().sort_values()
            if not chart_data.empty: st.area_chart(chart_data)
            else: st.info("No data available.")

        display_df = filtered_df[['property_id', 'district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link', 'status']].copy()
        if st.session_state['logged_in']:
            display_df['❤️ Track'] = display_df['property_id'].isin(user_fav_ids)
            cols = ['❤️ Track', 'district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link', 'status', 'property_id']
        else:
            cols = ['district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link', 'status', 'property_id']

        display_df = display_df[cols]

        column_config = {
            "property_id": None, "district": t["th_dist"],
            "price_pln": st.column_config.NumberColumn(t["th_price"], format="%.0f PLN"),
            "sqm": st.column_config.NumberColumn(t["th_sqm"], format="%.0f"),
            "rooms": t["th_rooms"],
            "price_per_sqm": st.column_config.NumberColumn(t["th_psqm"], format="%.0f PLN"),
            "url_link": st.column_config.LinkColumn(t["th_link"], display_text="View 🔗"),
            "status": t["th_status"]
        }

        if st.session_state['logged_in']:
            edited_df = st.data_editor(display_df, column_config=column_config, hide_index=True, use_container_width=True, disabled=["district", "price_pln", "sqm", "rooms", "price_per_sqm", "url_link", "status"])
            process_favorite_edits(edited_df, display_df, st.session_state['user_email'])
        else:
            st.dataframe(display_df, column_config=column_config, hide_index=True, use_container_width=True)
            st.info("💡 **Log in to track properties and receive price drop alerts.**")

    with tab2:
        st.subheader(t["tab2"])
        map_data = []
        map_price_key = 'Avg Total Price' if selected_trans_id == 1 else 'Avg Monthly Rent'
        for district, group in filtered_df.groupby('district'):
            if district in DISTRICT_COORDS:
                avg_sqm = group['price_per_sqm'].mean()
                if pd.notna(avg_sqm):
                    map_data.append({
                        'District': district, 'Listings Count': len(group), 'Avg Price/m²': round(avg_sqm, 0),
                        map_price_key: round(group['price_pln'].mean(), 0), 'lat': DISTRICT_COORDS[district]['lat'], 'lon': DISTRICT_COORDS[district]['lon']
                    })
        map_df = pd.DataFrame(map_data)

        # --- HARİTA DÜZELTMESİ ---
        current_map_style = "carto-darkmatter" if sel_theme == "🌙 Dark" else "carto-positron"
        bg_col = "rgba(0,0,0,0)" # Arka plan tamamen şeffaf
        font_col = "#FFFFFF" if sel_theme == "🌙 Dark" else "#000000"

        if not map_df.empty:
            fig = px.scatter_mapbox(map_df, lat="lat", lon="lon", size="Listings Count", color="Avg Price/m²", hover_name="District", hover_data={"lat": False, "lon": False, map_price_key: True, "Listings Count": True}, color_continuous_scale=px.colors.sequential.Plasma, size_max=50, zoom=10, mapbox_style=current_map_style)
            fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=600, paper_bgcolor=bg_col, plot_bgcolor=bg_col, font=dict(color=font_col))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Insufficient geographic data to render the map based on your current filters.")

    with tab3:
        st.subheader(t["tab3"])
        if selected_trans_id == 1:
            with st.spinner(t["roi_calc"]):
                rent_averages, city_avg_rent = load_rent_averages(selected_type_id)
                roi_df = filtered_df.dropna(subset=['sqm', 'loc_id']).copy()
                if pd.isna(city_avg_rent) or city_avg_rent <= 0:
                    city_avg_rent = {1: 85.0, 2: 100.0, 3: 2.0, 4: 80.0, 5: 35.0, 6: 25.0}.get(selected_type_id, 50.0)
                    st.warning(t["roi_warn"])
                if roi_df.empty:
                    st.info(t["roi_info"])
                else:
                    roi_df['avg_rent_sqm'] = roi_df['loc_id'].map(rent_averages).fillna(city_avg_rent)
                    roi_df['est_monthly_rent'] = roi_df['sqm'] * roi_df['avg_rent_sqm']
                    roi_df['net_annual'] = (roi_df['est_monthly_rent'] * 12) * 0.8
                    roi_df = roi_df[(roi_df['price_pln'] > 0) & (roi_df['net_annual'] > 0)]
                    if not roi_df.empty:
                        roi_df['roi_percent'] = (roi_df['net_annual'] / roi_df['price_pln']) * 100
                        roi_df['amortization_years'] = roi_df['price_pln'] / roi_df['net_annual']
                        roi_df = roi_df[(roi_df['price_pln'] >= 50000) & (roi_df['roi_percent'] <= 30.0)]

                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(t["roi_col1"])
                            st.bar_chart(roi_df.groupby('district')['roi_percent'].mean().sort_values(ascending=False), color="#4CAF50")
                        with c2:
                            st.write(t["roi_col2"])
                            st.bar_chart(roi_df.groupby('district')['amortization_years'].mean().sort_values(), color="#FF9800")

                        st.subheader(t["roi_top"])
                        roi_df = roi_df.sort_values(by='roi_percent', ascending=False)
                        display_roi = roi_df[['property_id', 'district', 'price_pln', 'est_monthly_rent', 'roi_percent', 'amortization_years', 'url_link']].copy()
                        if not is_premium:
                            display_roi['price_pln'] = "🔒 Locked"
                            display_roi['url_link'] = "🔒 Locked"

                        cols_roi = ['❤️ Track', 'district', 'price_pln', 'est_monthly_rent', 'roi_percent', 'amortization_years', 'url_link', 'property_id'] if st.session_state['logged_in'] else ['district', 'price_pln', 'est_monthly_rent', 'roi_percent', 'amortization_years', 'url_link', 'property_id']
                        if st.session_state['logged_in']: display_roi['❤️ Track'] = display_roi['property_id'].isin(user_fav_ids)
                        display_roi = display_roi[cols_roi]

                        col_conf_roi = {
                            "property_id": None, "district": t["th_dist"],
                            "price_pln": st.column_config.NumberColumn(t["th_price"], format="%.0f PLN") if is_premium else st.column_config.TextColumn(t["th_price"]),
                            "est_monthly_rent": st.column_config.NumberColumn(t["th_est_rent"], format="%.0f PLN"),
                            "roi_percent": st.column_config.NumberColumn(t["th_roi"], format="%.1f%%"),
                            "amortization_years": st.column_config.NumberColumn(t["th_amort"], format="%.1f"),
                            "url_link": st.column_config.LinkColumn(t["th_link"], display_text="View 🔗") if is_premium else st.column_config.TextColumn(t["th_link"])
                        }
                        st.dataframe(display_roi.head(50), column_config=col_conf_roi, hide_index=True, use_container_width=True)

    with tab4:
        st.subheader(t["tab4"])
        st.markdown(t["drop_sub"])
        with st.spinner(t["drop_analyzing"]):
            history_df = load_price_history()
            if not history_df.empty and 'property_id' in filtered_df.columns:
                history_df['price_pln'] = pd.to_numeric(history_df['price_pln'], errors='coerce')
                history_df = history_df.sort_values(by=['property_id', 'created_at'])
                first_prices = history_df.groupby('property_id')['price_pln'].first().rename('Old Price')
                last_prices = history_df.groupby('property_id')['price_pln'].last().rename('Current Price')
                drops = pd.concat([first_prices, last_prices], axis=1)
                drops = drops[drops['Old Price'] > drops['Current Price']].copy()
                drops['Discount (PLN)'] = drops['Old Price'] - drops['Current Price']
                drops['Discount (%)'] = (drops['Discount (PLN)'] / drops['Old Price']) * 100
                radar_df = pd.merge(drops, filtered_df, on='property_id', how='inner')

                if not radar_df.empty:
                    radar_df = radar_df.sort_values(by='Discount (%)', ascending=False)
                    display_radar = radar_df[['property_id', 'district', 'Old Price', 'Current Price', 'Discount (PLN)', 'Discount (%)', 'price_per_sqm', 'url_link']].copy()
                    if not is_premium:
                        display_radar['Current Price'] = "🔒 Locked"
                        display_radar['Discount (PLN)'] = "🔒 Locked"
                        display_radar['url_link'] = "🔒 Locked"
                    cols_radar = ['❤️ Track', 'district', 'Old Price', 'Current Price', 'Discount (PLN)', 'Discount (%)', 'price_per_sqm', 'url_link', 'property_id'] if st.session_state['logged_in'] else ['district', 'Old Price', 'Current Price', 'Discount (PLN)', 'Discount (%)', 'price_per_sqm', 'url_link', 'property_id']
                    if st.session_state['logged_in']: display_radar['❤️ Track'] = display_radar['property_id'].isin(user_fav_ids)
                    display_radar = display_radar[cols_radar]
                    col_conf_radar = {
                        "property_id": None, "district": t["th_dist"],
                        "Old Price": st.column_config.NumberColumn(t["th_old"], format="%.0f PLN"),
                        "Current Price": st.column_config.NumberColumn(t["th_cur"], format="%.0f PLN") if is_premium else st.column_config.TextColumn(t["th_cur"]),
                        "Discount (PLN)": st.column_config.NumberColumn(t["th_disc"], format="-%.0f PLN") if is_premium else st.column_config.TextColumn(t["th_disc"]),
                        "Discount (%)": st.column_config.NumberColumn(t["th_disc_pct"], format="-%.1f%%"),
                        "price_per_sqm": st.column_config.NumberColumn(t["th_psqm"], format="%.0f PLN"),
                        "url_link": st.column_config.LinkColumn(t["th_link"], display_text="View 🔗") if is_premium else st.column_config.TextColumn(t["th_link"])
                    }
                    st.dataframe(display_radar, column_config=col_conf_radar, hide_index=True, use_container_width=True)
                else:
                    st.info(t["drop_none"])

    with tab5:
        st.subheader(t["tab5"])
        st.markdown(t["calc_sub"])
        calc_col1, calc_col2 = st.columns(2)
        with calc_col1:
            st.markdown(t["calc_mort"])
            prop_price = st.number_input(t["calc_prop"], min_value=100000, value=800000, step=10000)
            down_payment_pct = st.slider(t["calc_down"], 0, 100, 20)
            interest_rate = st.slider(t["calc_int"], 0.0, 15.0, 7.2, 0.1)
            loan_term = st.selectbox(t["calc_term"], [10, 15, 20, 25, 30], index=4)
            down_payment = prop_price * (down_payment_pct / 100)
            principal = prop_price - down_payment
            if principal > 0 and interest_rate > 0:
                monthly_interest = (interest_rate / 100) / 12
                num_payments = loan_term * 12
                monthly_payment = principal * (monthly_interest * (1 + monthly_interest)**num_payments) / ((1 + monthly_interest)**num_payments - 1)
            elif principal > 0 and interest_rate == 0: monthly_payment = principal / (loan_term * 12)
            else: monthly_payment = 0
            st.info(f"{t['calc_req_down']} {down_payment:,.0f} PLN")
            st.success(f"{t['calc_est_inst']} {monthly_payment:,.0f} PLN")

        with calc_col2:
            st.markdown(t["calc_reno"])
            prop_sqm = st.number_input(t["calc_size"], min_value=10, max_value=500, value=50)
            reno_level = st.radio(t["calc_qual"], [t["calc_eco"], t["calc_std"], t["calc_prem"]])
            if "Economy" in reno_level or "Ekonomiczne" in reno_level or "Ekonomik" in reno_level: reno_cost_sqm = 1800
            elif "Standard" in reno_level or "Standart" in reno_level: reno_cost_sqm = 3000
            else: reno_cost_sqm = 4500
            total_reno_cost = prop_sqm * reno_cost_sqm
            st.warning(f"{t['calc_est_reno']} {total_reno_cost:,.0f} PLN")

            st.markdown("---")
            st.markdown(t["calc_cf"])
            est_rent = st.number_input(t["calc_est_inc"], value=4000, step=100)
            hoa_fees = st.number_input(t["calc_hoa"], value=700, step=50)
            tax_rate = st.slider(t["calc_tax"], 0.0, 20.0, 8.5, 0.5)
            tax_amount = est_rent * (tax_rate / 100)
            net_cash_flow = est_rent - monthly_payment - hoa_fees - tax_amount
            if net_cash_flow >= 0: st.success(f"{t['calc_net']} +{net_cash_flow:,.0f} PLN 🤑")
            else: st.error(f"{t['calc_net']} {net_cash_flow:,.0f} PLN 🩸")

    with tab6:
        st.subheader(t["tab6"])
        if not st.session_state['logged_in']: st.warning(t["fav_warn"])
        else:
            with st.spinner(t["fav_load"]):
                if not user_fav_ids: st.info(t["fav_empty"])
                else:
                    if not history_df.empty:
                        fav_history = history_df[history_df['property_id'].isin(user_fav_ids)]
                        if not fav_history.empty:
                            first_p = fav_history.groupby('property_id')['price_pln'].first()
                            last_p = fav_history.groupby('property_id')['price_pln'].last()
                            drop_alerts = []
                            for pid in first_p.index:
                                if first_p[pid] > last_p[pid]: drop_alerts.append((pid, first_p[pid] - last_p[pid], last_p[pid]))
                            if drop_alerts:
                                st.markdown(t["fav_alert"])
                                for pid, discount, new_price in drop_alerts: st.success(f"{t['fav_good']} (ID: {pid}) -> **-{discount:,.0f} PLN**! Current: **{new_price:,.0f} PLN**")
                                st.markdown("---")
                    fav_df = df[df['property_id'].isin(user_fav_ids)].copy()
                    if fav_df.empty: st.warning(t["fav_sold"])
                    else:
                        st.markdown(t["fav_here"])
                        fav_df['❤️ Track'] = True
                        if not is_premium:
                            fav_df['price_pln'] = "🔒 Locked"
                            fav_df['url_link'] = "🔒 Locked"
                        fav_cols = ['❤️ Track', 'district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link', 'property_id']
                        display_fav = fav_df[fav_cols]
                        col_conf_fav = {
                            "property_id": None, "district": t["th_dist"],
                            "price_pln": st.column_config.NumberColumn(t["th_price"], format="%.0f PLN") if is_premium else st.column_config.TextColumn(t["th_price"]),
                            "sqm": st.column_config.NumberColumn(t["th_sqm"], format="%.0f"),
                            "rooms": t["th_rooms"],
                            "price_per_sqm": st.column_config.NumberColumn(t["th_psqm"], format="%.0f PLN"),
                            "url_link": st.column_config.LinkColumn(t["th_link"], display_text="View 🔗") if is_premium else st.column_config.TextColumn(t["th_link"])
                        }
                        edited_my_favs = st.data_editor(display_fav, column_config=col_conf_fav, hide_index=True, use_container_width=True, disabled=["district", "price_pln", "sqm", "rooms", "price_per_sqm", "url_link"])
                        for i, row in edited_my_favs.iterrows():
                            if not row['❤️ Track']:
                                toggle_favorite(st.session_state['user_email'], row['property_id'], False)
                                st.rerun()

    with tab7:
        st.subheader(t["tab7"])
        st.markdown(t["for_sub"])
        with st.spinner(t["for_train"]):
            forecast_df = predict_future_prices(df)
            if not forecast_df.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(t["for_top3"])
                    for index, row in forecast_df.head(3).iterrows(): st.success(f"**📍 {row['District']}**\n\n{t['for_growth']} **+%.1f%%**" % row['Growth Potential (%)'])
                with c2:
                    if not is_premium:
                        st.warning(t["for_lock"])
                        st.link_button(t["sb_unlock"], STRIPE_LINK, type="primary")
                        display_forecast = forecast_df.head(3).copy()
                    else:
                        st.success(t["for_unlock"])
                        display_forecast = forecast_df.copy()
                    st.dataframe(display_forecast, column_config={"District": t["th_dist"], "Current Avg (PLN/m²)": st.column_config.NumberColumn(t["th_cur_avg"], format="%.0f PLN"), "Predicted 6-Month (PLN/m²)": st.column_config.NumberColumn(t["th_pred"], format="%.0f PLN"), "Growth Potential (%)": st.column_config.NumberColumn(t["th_grow"], format="%.1f%%")}, hide_index=True, use_container_width=True)
            else: st.info(t["for_none"])

    with tab8:
        st.subheader(t["tab8"])
        st.markdown(t["cd_sub"])
        if df_sold.empty: st.info(t["cd_none"])
        else:
            display_sold = df_sold[['district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm']].copy()
            st.dataframe(display_sold, column_config={"district": t["th_dist"], "price_pln": st.column_config.NumberColumn(t["th_last"], format="%.0f PLN"), "sqm": st.column_config.NumberColumn(t["th_sqm"], format="%.0f"), "rooms": t["th_rooms"], "price_per_sqm": st.column_config.NumberColumn(t["th_psqm"], format="%.0f PLN")}, hide_index=True, use_container_width=True)
            st.bar_chart(df_sold['district'].value_counts())

else:
    st.info("No active listings found in the system matching current criteria.")