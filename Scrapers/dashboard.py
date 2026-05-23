import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv
import io
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression
import pydeck as pdk
from supabase import create_client, Client
from datetime import timedelta
from Scrapers.notifier import send_telegram_lead, EmailManager
from Scrapers.config import LOCATION_MAP


FREE_TABLE_LIMIT = 5
FREE_TOOL_USAGE_LIMIT = 3
EXPANDER_LINK = "https://proptech.produktyfinansowe.pl/e/lead/327?source=lt"

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

base_dir = current_dir.parent
env_path = base_dir / ".env"

if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8-sig") as f:
            clean_content = f.read()
        load_dotenv(stream=io.StringIO(clean_content), override=True)
    except Exception:
        pass

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

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

st.set_page_config(page_title="Warsaw AI PropTech", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Hide only the Deploy button, DO NOT TOUCH stToolbar so the left arrow doesn't break */
        .stDeployButton {display: none;}
        
        .lock-overlay {
            background-color: rgba(255, 75, 75, 0.05);
            border: 2px dashed #ff4b4b;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            margin-top: 15px;
        }
        /* ... the rest of your code continues the same way ... */
    .premium-text { color: #ff4b4b; font-weight: bold; }

    * {
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
    }
    
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
    
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

LANG_DICT = {
    "🇬🇧 EN": {
        "hero_title": "Warsaw Real Estate Intelligence",
        "hero_sub": "🚀 <b>AI-Powered Arbitrage:</b> Detecting underpriced deals in Warsaw in real-time.",
        "sys_active": "SYSTEM ACTIVE & MONITORING", "scan_cycle": "Scan Cycle:", "analyzed": "Analyzed:",
        "live_listings": "Live Active Listings", "avg_price": "Avg Sale Price", "avg_rent": "Avg Monthly Rent",
        "avg_sqm": "Avg Price / m²", "market_status": "Market Status", "active": "Active 🟢",
        "tab1": "📊 Market Overview", "tab2": "🗺️ Interactive Heatmap", "tab3": "🧠 ROI & Amortization Map",
        "tab4": "🚨 Price Drop Radar", "tab5": "🧮 Investment Calculators", "tab6": "⭐ My Favorites",
        "tab7": "🔮 AI Future Forecast", "tab8": "✅ Closed Deals", "tab9": "📈 Historical Price Trends",
        "sb_member": "🔐 Member Access", "sb_login": "Login", "sb_signup": "Sign Up", "sb_forgot": "Forgot Password?",
        "sb_back": "⬅ Back", "prof_info": "👤 Profile Info", "prof_name": "Full Name", "prof_sub": "Subscription",
        "sb_fn": "First Name", "sb_ln": "Last Name", "sb_confirm": "Confirm Password",
        "sb_update": "Update Profile", "msg_updated": "Profile updated successfully!",
        "err_pass_len": "Password must be at least 8 characters.", "err_pass_match": "Passwords do not match.",
        "msg_reset": "Reset link sent! Check your email.",
        "sb_email": "Email Address", "sb_pass": "Password", "sb_unlock": "🚀 Unlock Pro Features",
        "sb_logout": "Logout", "sb_controls": "🎯 System Controls", "sb_mode": "Market Mode",
        "sb_sale": "Sale (Investment)", "sb_rent": "Rent (Yield)", "sb_type": "Property Type",
        "sb_filters": "🔍 Quick Filters", "sb_budget": "Max Budget (PLN)",
        "sb_districts": "Select Districts",
        "th_dist": "District", "th_price": "Price (PLN)", "th_sqm": "m²", "th_rooms": "Rooms",
        "th_psqm": "Price/m²", "th_link": "Link", "th_status": "Status", "th_trend": "Price Trend",
        "cs_title": "🏆 Top Live Arbitrage Opportunities",
        "cs_info": "ℹ️ *The listings below are live anomalies detected by comparing asking price vs district average.*",
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
        "fav_warn": "🔒 Please log in to view and manage your tracked properties.", "fav_load": "Loading your vault...",
        "fav_empty": "You haven't saved any properties yet. Browse the market tabs and check the '❤️ Track' box to start monitoring!",
        "fav_alert": "### 🔔 PRICE DROP ALERTS!", "fav_good": "**🚨 GOOD NEWS!** A property you are tracking",
        "fav_sold": "Your saved properties are no longer active on the market (Sold or Removed).", "fav_here": "Here are your tracked investments. Uncheck the box to remove a property from your list.",
        "for_sub": "This machine learning model (Linear Regression) analyzes historical price trends to predict which Warsaw districts will appreciate the most in the next 6 months.",
        "for_train": "AI is training the predictive model...", "for_top3": "### 🏆 Top 3 Investment Zones",
        "for_growth": "📈 Expected Growth:", "for_lock": "🔒 **PREMIUM LOCK:** Full predictive dataset is hidden. Upgrade to access all district forecasts.",
        "for_unlock": "👑 Premium Unlocked! Viewing all future predictions.", "th_cur_avg": "Current Price/m²", "th_pred": "Predicted Price/m²", "th_grow": "Growth",
        "for_none": "Bot needs to scrape more data to build an accurate predictive model. Check back later!",
        "cd_sub": "Properties that were recently removed from the market (Likely sold). Use this data to analyze market speed.",
        "cd_none": "No closed deals detected yet. Bot is monitoring removals...", "th_last": "Last Asking Price",
        "vip_title": "🏆 Find the Best Mortgage Offer in Poland",
        "vip_desc": "Let <b>Expander</b> experts compare 20+ banks for you free of charge and secure the lowest interest rate.",
        "vip_btn": "🏢 Get Free Expert Advice (20+ Banks) ➡️",
        "calc_exp_btn": "🏦 Expander: Check Your Best Mortgage Limit ➡️",
        "calc_exp_sub": "ℹ️ Expander experts will find the best offer from 20 banks for you, completely free.",
        "tab2_title": "📍 District Intelligence & Location Analytics",
        "tab2_rankings": "### 📊 Market Rankings",
        "tab2_map": "### 🗺️ Geographic Distribution",
        "th_active_ads": "Active Ads",
        "th_avg_price_sqm": "Avg Price/m²",
        "ai_audit_title": "### 🤖 Groq AI Real-Time Audit & Negotiation",
        "ai_audit_sub": "Enter any Otodom URL for an instant visual and financial investment audit via Llama 4 Vision.",
        "ai_paste_url": "🔗 Paste Otodom URL",
        "ai_size_calc": "📏 Size for Calculation (m²)",
        "ai_btn_search": "🧠 Start Live Groq Deep Search",
        "ai_spinner": "🚀 Groq AI Sniper is flying to the property page...",
        "ai_local_found": "⚡ Listing found in local intelligence. Generating fresh Groq analysis...",
        "ai_success": "✅ **AI Live Audit Result:**",
        "ai_error": "❌ Failed to reach the property. Link might be broken or protected.",
        "ai_warn_empty": "Please enter a link first.",
        "lock_msg": f"🔓 <b>Showing only {FREE_TABLE_LIMIT} results.</b> <span class='premium-text'>Upgrade to Premium</span> to see all data.",
        "limit_reached": f"🛑 **Limit Reached:** You have used your {FREE_TOOL_USAGE_LIMIT} free daily AI audits.",
        "upgrade_btn": "💎 Get Unlimited Access",
        "audits_left": "💡 You have {} free audits left for today.",
        "locked": "🔒 Locked", "locked_link": "🔒 Upgrade to View",
        "roi_only_sale": "💡 **ROI Map is restricted.** Switch 'Market Mode' to 'Sale (Investment)' on the left menu to view return on investment data.",
        "settings_menu": "⚙️ Settings",
        "ht_title": "📈 Deep Dive: Historical Price Trends",
        "ht_sub": "Enter an Otodom URL to visualize the property's historical price changes mapped against district averages.",
        "ht_btn": "📊 Generate Price Trend Map",
        "ht_spinner": "Mining historical databases...",
        "ht_err_url": "Please enter a valid Otodom link.",
        "ht_err_not_found": "No historical data found for this property.",
        "ht_chart_title": "Price History: Property vs. District Average",
        "ht_sim_note": "💡 *Note: Showing AI-simulated trailing market data for enhanced trend visualization.*",
        "ht_ai_title": "🤖 Groq AI Trend & Valuation Report",
        "ht_ai_spin": "Groq AI is analyzing market signals...",
        "email_btn": "📧 Send to Email",
        "email_success": "✅ Email sent successfully!",
        "email_fail": "❌ Failed to send email."
    },
    "🇵🇱 PL": {
        "hero_title": "Warszawska Inteligencja Nieruchomości",
        "hero_sub": "🚀 <b>Arbitraż AI:</b> Wykrywanie niedoszacowanych ofert w Warszawie w czasie rzeczywistym.",
        "sys_active": "SYSTEM AKTYWNY I MONITORUJE", "scan_cycle": "Skanowanie:", "analyzed": "Przeanalizowano:",
        "live_listings": "Aktywne Ogłoszenia", "avg_price": "Średnia Cena Sprzedaży", "avg_rent": "Średni Czynsz",
        "avg_sqm": "Śr. Cena / m²", "market_status": "Status Rynku", "active": "Aktywny 🟢",
        "tab1": "📊 Przegląd Rynku", "tab2": "🗺️ Mapa Cieplna", "tab3": "🧠 ROI i Amortyzacja",
        "tab4": "🚨 Radar Spadków Cen", "tab5": "🧮 Kalkulatory Inwestycyjne", "tab6": "⭐ Moje Ulubione",
        "tab7": "🔮 Prognoza Przyszłości", "tab8": "✅ Zamknięte Transakcje", "tab9": "📈 Historyczne Trendy Cenowe",
        "sb_member": "🔐 Dostęp Użytkownika", "sb_login": "Zaloguj", "sb_signup": "Rejestracja", "sb_forgot": "Zapomniałeś hasła?",
        "sb_back": "⬅ Wróć", "prof_info": "👤 Twój Profil", "prof_name": "Imię i nazwisko", "prof_sub": "Subskrypcja",
        "sb_fn": "Imię", "sb_ln": "Nazwisko", "sb_confirm": "Potwierdź hasło",
        "sb_update": "Zaktualizuj Profil", "msg_updated": "Profil zaktualizowany pomyślnie!",
        "err_pass_len": "Hasło musi mieć co najmniej 8 znaków.", "err_pass_match": "Hasła nie są identyczne.",
        "msg_reset": "Wysłano link resetujący! Sprawdź email.",
        "sb_email": "Adres Email", "sb_pass": "Hasło", "sb_unlock": "🚀 Odblokuj Funkcje Pro",
        "sb_logout": "Wyloguj", "sb_controls": "🎯 Panel Sterowania", "sb_mode": "Tryb Rynku",
        "sb_sale": "Sprzedaż (Inwestycja)", "sb_rent": "Wynajem (Zysk)", "sb_type": "Typ Nieruchomości",
        "sb_filters": "🔍 Szybkie Filtry", "sb_budget": "Maks. Budżet (PLN)",
        "sb_districts": "Wybierz Dzielnice",
        "th_dist": "Dzielnica", "th_price": "Cena (PLN)", "th_sqm": "m²", "th_rooms": "Pokoje",
        "th_psqm": "Cena/m²", "th_link": "Link", "th_status": "Status", "th_trend": "Trend Cenowy",
        "cs_title": "🏆 Najlepsze Aktywne Okazje Arbitrażowe",
        "cs_info": "ℹ️ *Poniższe oferty to aktywne anomalie wykryte przez porównanie ceny ofertowej ze średnią dzielnicy.*",
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
        "fav_warn": "🔒 Zaloguj się, aby zarządzać śledzonymi nieruchomościami.", "fav_load": "Ładowanie twojego skarbca...",
        "fav_empty": "Nie zapisałeś jeszcze żadnych nieruchomości. Zaznacz '❤️ Track', aby zacząć monitorować!",
        "fav_alert": "### 🔔 ALERTY O SPADKU CEN!", "fav_good": "**🚨 DOBRE WIEŚCI!** Nieruchomość, którą śledzisz",
        "fav_sold": "Twoje zapisane nieruchomości nie są już aktywne (Sprzedane lub Usunięte).", "fav_here": "Oto twoje śledzone inwestycje. Odznacz pole, aby usunąć z listy.",
        "for_sub": "Ten model uczenia maszynowego (Regresja Liniowa) analizuje historyczne trendy cenowe...",
        "for_train": "Sztuczna inteligencja trenuje model predykcyjny...", "for_top3": "### 🏆 Top 3 Strefy Inwestycyjne",
        "for_growth": "📈 Oczekiwany Wzrost:", "for_lock": "🔒 **BLOKADA PREMIUM:** Pełne dane są ukryte.",
        "for_unlock": "👑 Premium Odblokowane! Oglądasz wszystkie prognozy.", "th_cur_avg": "Obecna Cena/m²", "th_pred": "Przewidywana Cena/m²", "th_grow": "Wzrost",
        "for_none": "Bot musi zebrać więcej danych, aby zbudować dokładny model.",
        "cd_sub": "Nieruchomości, które zostały niedawno usunięte z rynku (Prawdopodobnie sprzedane).",
        "cd_none": "Brak zamkniętych transakcji. Bot monitoruje rynek...", "th_last": "Ostatnia Cena Ofertowa",
        "vip_title": "🏆 Znajdź Najlepszą Ofertę Kredytową w Polsce",
        "vip_desc": "Niech eksperci <b>Expander</b> bezpłatnie porównają dla Ciebie ponad 20 banków i znajdą najniższe oprocentowanie.",
        "vip_btn": "🏢 Zdobądź Darmową Poradę Eksperta (20+ Banków) ➡️",
        "calc_exp_btn": "🏦 Expander: Sprawdź Swój Limit Kredytowy ➡️",
        "calc_exp_sub": "ℹ️ Eksperci Expander znajdą dla Ciebie najlepszą ofertę z 20 banków całkowicie za darmo.",
        "tab2_title": "📍 Inteligencja Dzielnic i Analityka Lokalizacji",
        "tab2_rankings": "### 📊 Rankingi Rynkowe",
        "tab2_map": "### 🗺️ Rozkład Geograficzny",
        "th_active_ads": "Aktywne Ogłoszenia",
        "th_avg_price_sqm": "Śr. Cena/m²",
        "ai_audit_title": "### 🤖 Groq AI Audyt i Negocjacje na Żywo",
        "ai_audit_sub": "Wprowadź dowolny link Otodom, aby uzyskać natychmiastowy audyt wizualny i finansowy za pomocą Llama 4 Vision.",
        "ai_paste_url": "🔗 Wklej link Otodom",
        "ai_size_calc": "📏 Metraż do obliczeń (m²)",
        "ai_btn_search": "🧠 Rozpocznij Skanowanie Groq AI",
        "ai_spinner": "🚀 Groq AI Sniper leci na stronę nieruchomości...",
        "ai_local_found": "⚡ Znaleziono ogłoszenie w bazie. Generowanie nowej analizy Groq...",
        "ai_success": "✅ **Wynik Audytu AI na Żywo:**",
        "ai_error": "❌ Nie udało się dotrzeć do nieruchomości. Link może być uszkodzony.",
        "ai_warn_empty": "Proszę najpierw wprowadzić link.",
        "lock_msg": f"🔓 <b>Pokazujemy tylko {FREE_TABLE_LIMIT} wyników.</b> <span class='premium-text'>Przejdź na Premium</span>, aby zobaczyć wszystko.",
        "limit_reached": f"🛑 **Osiągnięto limit:** Wykorzystałeś {FREE_TOOL_USAGE_LIMIT} darmowe audyty AI.",
        "upgrade_btn": "💎 Uzyskaj nieograniczony dostęp",
        "audits_left": "💡 Zostało Ci {} darmowych audytów na dziś.",
        "locked": "🔒 Zablokowane", "locked_link": "🔒 Kup Premium",
        "roi_only_sale": "💡 **ROI Haritası kısıtlıdır.** Bu veriyi görmek dla sol menüden 'Piyasa Modu'nu 'Sprzedaż (Inwestycja)' jako değiştirin.",
        "settings_menu": "⚙️ Ustawienia",
        "ht_title": "📈 Głęboka Analiza: Historyczne Trendy Cenowe",
        "ht_sub": "Wprowadź link Otodom, aby zwizualizować historyczne zmiany cen nieruchomości na tle średnich w dzielnicy.",
        "ht_btn": "📊 Generuj Mapę Trendu Cenowego",
        "ht_spinner": "Przeszukiwanie historycznych baz danych...",
        "ht_err_url": "Proszę wprowadzić prawidłowy link Otodom.",
        "ht_err_not_found": "Nie znaleziono danych historycznych dla tej nieruchomości.",
        "ht_chart_title": "Historia Cen: Nieruchomość vs Średnia Dzielnicy",
        "ht_sim_note": "💡 *Uwaga: Wyświetlanie symulowanych przez AI danych rynkowych dla lepszej wizualizacji trendu.*",
        "ht_ai_title": "🤖 Raport Trendów i Wyceny Groq AI",
        "ht_ai_spin": "Groq AI analizuje sygnały rynkowe...",
        "email_btn": "📧 Wyślij na Email",
        "email_success": "✅ Email wysłany pomyślnie!",
        "email_fail": "❌ Nie udało się wysłać emaila."
    },
    "🇹🇷 TR": {
        "hero_title": "Varşova Emlak Zekası",
        "hero_sub": "🚀 <b>Yapay Zeka Arbitrajı:</b> Varşova'daki fırsat mülkleri gerçek zamanlı tespit eder.",
        "sys_active": "SİSTEM AKTİF & İZLENİYOR", "scan_cycle": "Tarama Döngüsü:", "analyzed": "Analiz Edilen:",
        "live_listings": "Aktif İlanlar", "avg_price": "Ort. Satış Fiyatı", "avg_rent": "Ort. Aylık Kira",
        "avg_sqm": "Ort. m² Fiyatı", "market_status": "Piyasa Durumu", "active": "Aktif 🟢",
        "tab1": "📊 Piyasa Özeti", "tab2": "🗺️ Isı Haritası", "tab3": "🧠 ROI & Amortisman",
        "tab4": "🚨 Fiyat Düşüş Radarı", "tab5": "🧮 Yatırım Hesaplayıcı", "tab6": "⭐ Favorilerim",
        "tab7": "🔮 Gelecek Tahmini", "tab8": "✅ Kapanan İşlemler", "tab9": "📈 Geçmiş Fiyat Trendleri",
        "sb_member": "🔐 Üye Girişi", "sb_login": "Giriş Yap", "sb_signup": "Kayıt Ol", "sb_forgot": "Şifremi Unuttum?",
        "sb_back": "⬅ Geri", "prof_info": "👤 Profil Bilgileri", "prof_name": "Ad Soyad", "prof_sub": "Abonelik",
        "sb_fn": "Ad", "sb_ln": "Soyad", "sb_confirm": "Şifreyi Onayla",
        "sb_update": "Profili Güncelle", "msg_updated": "Profil başarıyla güncellendi!",
        "err_pass_len": "Şifre en az 8 karakter olmalıdır.", "err_pass_match": "Şifreler eşleşmiyor.",
        "msg_reset": "Sıfırlama bağlantısı gönderildi! E-postanızı kontrol edin.",
        "sb_email": "E-posta Adresi", "sb_pass": "Şifre", "sb_unlock": "🚀 Pro Özellikleri Aç",
        "sb_logout": "Çıkış Yap", "sb_controls": "🎯 Sistem Kontrolleri", "sb_mode": "Piyasa Modu",
        "sb_sale": "Satılık (Yatırım)", "sb_rent": "Kiralık (Getiri)", "sb_type": "Mülk Tipi",
        "sb_filters": "🔍 Hızlı Filtreler", "sb_budget": "Maks. Bütçe (PLN)",
        "sb_districts": "Bölge Seç",
        "th_dist": "Bölge", "th_price": "Fiyat (PLN)", "th_sqm": "m²", "th_rooms": "Oda",
        "th_psqm": "Fiyat/m²", "th_link": "Link", "th_status": "Durum", "th_trend": "Fiyat Trendi",
        "cs_title": "🏆 En İyi Aktif Arbitraj Fırsatları",
        "cs_info": "ℹ️ *Aşağıdaki ilanlar, istenen fiyat ile bölge ortalaması karşılaştırılarak tespit edilen canlı piyasa fırsatlarıdır.*",
        "roi_calc": "Canlı kira ortalamalarına göre ROI hesaplanıyor...", "roi_warn": "⚠️ Canlı kira verisi eksik...",
        "roi_info": "ℹ️ **Not:** ROI hesaplaması m² verisi gerektirir.", "roi_col1": "**Bölgelere Göre Ort. ROI (%)**",
        "roi_col2": "**Bölgelere Göre Ort. Amortisman (Yıl)**", "roi_top": "🏆 En İyi ROI Fırsatları",
        "th_est_rent": "Tahmini Kira", "th_roi": "ROI (%)", "th_amort": "Amortisman (Yıl)",
        "drop_sub": "Satıcının yakın zamanda fiyatı düşürdüğü ilanlar.", "drop_analyzing": "Fiyat düşüş geçmişi analiz ediliyor...",
        "th_old": "Eski Fiyat", "th_cur": "Mevcut Fiyat", "th_disc": "İndirim", "th_disc_pct": "İndirim %",
        "drop_none": "Seçilen filtrelerde yakın zamanda fiyat düşüşü bulunamadı.",
        "calc_sub": "Yerel piyasa oranlarını kullanarak finansal senaryolarınızı ve nakit akışınızı simüle edin.",
        "calc_mort": "### 🏦 Konut Kredisi Hesaplayıcı", "calc_prop": "Mülk Fiyatı (PLN)", "calc_down": "Peşinat (%)",
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
        "cd_none": "Henüz kapanan işlem tespit edilmedi. Bot izliyor...", "th_last": "Son İstenen Fiyat",
        "vip_title": "🏆 Polonya'nın En İyi Kredi Teklifini Bulun",
        "vip_desc": "<b>Expander</b> uzmanları 20+ bankayı sizin için ücretsiz karşılaştırsın, en düşük faizli konut kredisini yakalayın.",
        "vip_btn": "🏢 Ücretsiz Uzman Danışmanlığı Al (20+ Banka) ➡️",
        "calc_exp_btn": "🏦 Expander: Check Your Best Mortgage Limit ➡️",
        "calc_exp_sub": "ℹ️ Expander uzmanları 20 bankadan sizin dla en iyi teklifi ücretsiz bulur.",
        "tab2_title": "📍 Bölge Zekası ve Konum Analitiği",
        "tab2_rankings": "### 📊 Piyasa Sıralamaları",
        "tab2_map": "### 🗺️ Coğrafi Dağılım",
        "th_active_ads": "Aktif İlanlar",
        "th_avg_price_sqm": "Ort. Fiyat/m²",
        "ai_audit_title": "### 🤖 Groq AI Canlı Denetim ve Müzakere",
        "ai_audit_sub": "Llama 4 Vision ile anında görsel ve finansal yatırım denetimi dla herhangi bir Otodom URL'sini girin.",
        "ai_paste_url": "🔗 Otodom Linkini Yapıştır",
        "ai_size_calc": "📏 Hesaplama dla Boyut (m²)",
        "ai_btn_search": "🧠 Canlı Groq Taramasını Başlat",
        "ai_spinner": "🚀 Groq AI Sniper mülk sayfasına uçuyor...",
        "ai_local_found": "⚡ İlan yerel istihbaratta bulundu. Yeni Groq analizi oluşturuluyor...",
        "ai_success": "✅ **Yapay Zeka Canlı Denetim Sonucu:**",
        "ai_error": "❌ Mülke ulaşılamadı. Bağlantı kopuk lub korumalı olabilir.",
        "ai_warn_empty": "Proszę najpierw wprowadzić link.",
        "lock_msg": f"🔓 <b>Sadece {FREE_TABLE_LIMIT} ilan gösteriliyor.</b> Tüm verileri görmek dla <span class='premium-text'>Premium'a geçin</span>.",
        "limit_reached": f"🛑 **Limit Doldu:** Günlük {FREE_TOOL_USAGE_LIMIT} ücretsiz AI analiz hakkını kullandın.",
        "upgrade_btn": "💎 Sınırsız Erişime Geç",
        "audits_left": "💡 Bugün dla {} ücretsiz analiz hakkın kaldı.",
        "locked": "🔒 Kilitli", "locked_link": "🔒 Görmek dla Yükselt",
        "roi_only_sale": "💡 **ROI Haritası kısıtlıdır.** Bu veriyi görmek dla sol menüden 'Piyasa Modu'nu 'Satılık (Yatırım)' jako değiştirin.",
        "settings_menu": "⚙️ Ayarlar",
        "ht_title": "📈 Derinlemesine İnceleme: Geçmiş Fiyat Trendleri",
        "ht_sub": "Mülkün geçmiş fiyat değişimlerini bölge ortalamalarına karşı görselleştirmek dla bir Otodom bağlantısı girin.",
        "ht_btn": "📊 Fiyat Trend Haritası Oluştur",
        "ht_spinner": "Geçmiş veritabanları taranıyor...",
        "ht_err_url": "Lütfen geçerli bir Otodom bağlantısı girin.",
        "ht_err_not_found": "Bu mülk dla geçmiş veri bulunamadı.",
        "ht_chart_title": "Fiyat Geçmişi: Mülk vs Bölge Ortalaması",
        "ht_sim_note": "💡 *Not: Trend görselleştirmesini artırmak dla yapay zeka ile simüle edilmiş geçmiş piyasa verileri gösteriliyor.*",
        "ht_ai_title": "🤖 Groq AI Trend ve Değerleme Raporu",
        "ht_ai_spin": "Groq AI piyasa sinyallerini analiz ediyor...",
        "email_btn": "📧 Email'e Gönder",
        "email_success": "✅ Email başarıyla gönderildi!",
        "email_fail": "❌ Email gönderimi başarısız oldu."
    }
}

if 'app_lang' not in st.session_state:
    st.session_state['app_lang'] = "🇬🇧 EN"
if 'app_theme' not in st.session_state:
    st.session_state['app_theme'] = "Auto"
if 'usage_counter' not in st.session_state:
    st.session_state['usage_counter'] = 0
if 'user_tier' not in st.session_state:
    st.session_state['user_tier'] = 'Free'
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""
if 'user_fn' not in st.session_state:
    st.session_state['user_fn'] = ""
if 'user_ln' not in st.session_state:
    st.session_state['user_ln'] = ""
if 'access_token' not in st.session_state:
    st.session_state['access_token'] = ""

t = LANG_DICT[st.session_state['app_lang']]

def check_limit(t_dict):
    if st.session_state.get('user_tier', 'Free') == 'Premium':
        return True
    if st.session_state['usage_counter'] >= FREE_TOOL_USAGE_LIMIT:
        st.error(t_dict["limit_reached"])
        st.link_button(t_dict["upgrade_btn"], STRIPE_LINK, type="primary")
        return False
    return True

def apply_limit(df, t_dict):
    if st.session_state.get('user_tier', 'Free') == 'Premium':
        return df, False

    limited_df = df.copy()
    is_limited = len(df) > FREE_TABLE_LIMIT

    if is_limited:
        limited_df = limited_df.astype(object)
        cols = limited_df.columns
        if 'price_pln' in cols:
            limited_df.iloc[FREE_TABLE_LIMIT:, cols.get_loc('price_pln')] = t_dict["locked"]
        if 'url_link' in cols:
            limited_df.iloc[FREE_TABLE_LIMIT:, cols.get_loc('url_link')] = t_dict["locked_link"]
        if 'Discount (PLN)' in cols:
            limited_df.iloc[FREE_TABLE_LIMIT:, cols.get_loc('Discount (PLN)')] = t_dict["locked"]
        if 'Current Price' in cols:
            limited_df.iloc[FREE_TABLE_LIMIT:, cols.get_loc('Current Price')] = t_dict["locked"]
        if 'est_monthly_rent' in cols:
            limited_df.iloc[FREE_TABLE_LIMIT:, cols.get_loc('est_monthly_rent')] = t_dict["locked"]

    return limited_df, is_limited

if "success" in st.query_params and st.query_params["success"] == "true":
    if st.session_state['logged_in']:
        st.session_state['user_tier'] = 'Premium'
        st.success("🎉 Payment Successful! Welcome to Premium. All hidden data is now unlocked for your account.")
        st.query_params.clear()
    else:
        st.warning("⚠️ Payment received, but you are not logged in. Please log in to activate your Premium.")

try:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    STRIPE_LINK = st.secrets.get("STRIPE_LINK", os.environ.get("STRIPE_LINK", "https://buy.stripe.com/9B66oA1Dp4t02BLa0U67S00"))
except Exception:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    STRIPE_LINK = os.environ.get("STRIPE_LINK", "https://buy.stripe.com/9B66oA1Dp4t02BLa0U67S00")

if SUPABASE_URL and SUPABASE_KEY:
    SUPABASE_URL = SUPABASE_URL.strip()
    SUPABASE_KEY = SUPABASE_KEY.strip()
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    st.error("❌ CRITICAL ERROR: Supabase keys are missing! Check Streamlit Secrets or .env file.")
    st.stop()

def login_user(email, password):
    url = f"{SUPABASE_URL.strip('/')}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    response = requests.post(url, headers=headers, json=payload)
    return response

def signup_user(email, password, fn, ln):
    url = f"{SUPABASE_URL.strip('/')}/auth/v1/signup"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password, "data": {"first_name": fn, "last_name": ln}}
    response = requests.post(url, headers=headers, json=payload)
    return response

def reset_password(email):
    url = f"{SUPABASE_URL.strip('/')}/auth/v1/recover"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    payload = {"email": email}
    response = requests.post(url, headers=headers, json=payload)
    return response

def toggle_favorite(email, property_id, is_adding):
    try:
        if is_adding:
            supabase_client.table('favorites').insert({"user_email": email, "property_id": int(property_id)}).execute()
        else:
            supabase_client.table('favorites').delete().eq('user_email', email).eq('property_id', int(property_id)).execute()
    except Exception as e:
        pass

def get_user_favorites(email):
    try:
        res = supabase_client.table('favorites').select('property_id').eq('user_email', email).execute()
        if res.data:
            return [item['property_id'] for item in res.data]
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
    all_data = []
    limit = 1000
    offset = 0
    try:
        while True:
            response = supabase_client.table('listings') \
                .select('*') \
                .eq('trans_id', trans_id) \
                .eq('type_id', type_id) \
                .range(offset, offset + limit - 1) \
                .execute()

            chunk = response.data
            if not chunk:
                break
            all_data.extend(chunk)
            if len(chunk) < limit:
                break
            offset += limit

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
    all_history = []
    limit = 1000
    offset = 0
    try:
        while True:
            response = supabase_client.table('price_history') \
                .select('listing_id,new_price_pln,change_date') \
                .range(offset, offset + limit - 1) \
                .execute()

            chunk = response.data
            if not chunk:
                break
            all_history.extend(chunk)
            if len(chunk) < limit:
                break
            offset += limit

        if not all_history: return pd.DataFrame()
        return pd.DataFrame(all_history)
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=3600)
def predict_future_prices(df, trans_id=1):
    predictions = []
    if df.empty: return pd.DataFrame()
    try:
        df_ml = df.copy()
        if 'status' in df_ml.columns:
            df_ml = df_ml[df_ml['status'] == 'ACTIVE']
        df_ml['price_per_sqm'] = pd.to_numeric(df_ml['price_per_sqm'], errors='coerce')
        df_ml = df_ml.dropna(subset=['price_per_sqm', 'district'])
        min_sqm = 1000 if trans_id == 1 else 10
        df_ml = df_ml[df_ml['price_per_sqm'] > min_sqm]
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

@st.dialog("🔐 Login Portal")
def show_login_modal():
    with st.form("login_form"):
        auth_email = st.text_input(t["sb_email"])
        auth_password = st.text_input(t["sb_pass"], type="password")
        submit_login = st.form_submit_button(t["sb_login"], use_container_width=True)

        if submit_login:
            with st.spinner("Authenticating..."):
                res = login_user(auth_email.strip(), auth_password)
                if res.status_code == 200:
                    data = res.json()
                    st.session_state['logged_in'] = True
                    st.session_state['user_email'] = auth_email.strip()
                    st.session_state['access_token'] = data.get('access_token', '')
                    user_meta = data.get('user', {}).get('user_metadata', {})
                    st.session_state['user_fn'] = user_meta.get('first_name', '')
                    st.session_state['user_ln'] = user_meta.get('last_name', '')
                    if st.session_state.get('user_tier') != 'Premium':
                        st.session_state['user_tier'] = 'Free'
                    st.rerun()
                else:
                    st.error("❌ Invalid Email or Password.")

    with st.expander(t["sb_forgot"]):
        with st.form("forgot_form"):
            forgot_email = st.text_input(t["sb_email"])
            submit_forgot = st.form_submit_button("Send Reset Link", use_container_width=True)
            if submit_forgot:
                if forgot_email.strip():
                    with st.spinner("Processing..."):
                        reset_password(forgot_email.strip())
                        st.success(f"✅ {t['msg_reset']}")
                else:
                    st.error("❌ Please enter email.")

@st.dialog("📝 Sign Up Portal")
def show_signup_modal():
    with st.form("signup_form"):
        auth_fn = st.text_input(t["sb_fn"])
        auth_ln = st.text_input(t["sb_ln"])
        auth_email_reg = st.text_input(t["sb_email"])
        auth_password_reg = st.text_input(t["sb_pass"], type="password")
        auth_confirm = st.text_input(t["sb_confirm"], type="password")

        submit_signup = st.form_submit_button(t["sb_signup"], use_container_width=True)

        if submit_signup:
            fn_clean = auth_fn.strip()
            ln_clean = auth_ln.strip()

            if len(auth_password_reg) < 8:
                st.error(f"❌ {t['err_pass_len']}")
            elif auth_password_reg != auth_confirm:
                st.error(f"❌ {t['err_pass_match']}")
            elif not fn_clean or not ln_clean:
                st.error("❌ Names are required.")
            else:
                with st.spinner("Creating account..."):
                    res = signup_user(auth_email_reg.strip(), auth_password_reg, fn_clean, ln_clean)
                    if res.status_code == 200:
                        st.success("✅ Registration successful! You can log in now.")
                    else:
                        st.error("❌ Registration failed. Email may exist.")

user_fav_ids = []
if st.session_state['logged_in']:
    user_fav_ids = get_user_favorites(st.session_state['user_email'])

col_space, col_fav, col_settings = st.columns([7.5, 1.5, 1.5])

with col_fav:
    if st.session_state['logged_in']:
        with st.popover(f"⭐ Favs ({len(user_fav_ids)})", use_container_width=True):
            st.markdown(f"**⭐ {t['tab6']}**")
            if user_fav_ids:
                try:
                    fav_res = supabase_client.table('listings').select('property_id, loc_id, price_pln, url_link').in_('property_id', user_fav_ids).execute()
                    if fav_res.data:
                        mini_fav_df = pd.DataFrame(fav_res.data)
                        mini_fav_df['district'] = mini_fav_df['loc_id'].map(REVERSE_LOCATION_MAP)
                        mini_fav_df['price_pln'] = pd.to_numeric(mini_fav_df['price_pln'], errors='coerce')

                        st.dataframe(
                            mini_fav_df[['district', 'price_pln', 'url_link']],
                            column_config={
                                "district": t["th_dist"],
                                "price_pln": st.column_config.NumberColumn(t["th_price"], format="%.0f PLN"),
                                "url_link": st.column_config.LinkColumn(t["th_link"], display_text="View 🔗")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                except Exception:
                    st.info("Scroll to the bottom vault to see details.")
            else:
                st.info(t["fav_empty"])

with col_settings:
    with st.popover(t["settings_menu"], use_container_width=True):
        new_lang = st.selectbox("🌐 Language", ["🇬🇧 EN", "🇵🇱 PL", "🇹🇷 TR"], index=["🇬🇧 EN", "🇵🇱 PL", "🇹🇷 TR"].index(st.session_state['app_lang']), key="lang_sel")
        new_theme = st.selectbox("🎨 Theme", ["Auto", "🌙 Dark", "☀️ Light"], index=["Auto", "🌙 Dark", "☀️ Light"].index(st.session_state['app_theme']), key="theme_sel")

        if new_lang != st.session_state['app_lang'] or new_theme != st.session_state['app_theme']:
            st.session_state['app_lang'] = new_lang
            st.session_state['app_theme'] = new_theme
            st.rerun()

        if st.session_state['logged_in']:
            st.divider()
            st.markdown(f"**{t['prof_info']}**")
            with st.form("profile_form"):
                new_fn = st.text_input(t["sb_fn"], value=st.session_state['user_fn'])
                new_ln = st.text_input(t["sb_ln"], value=st.session_state['user_ln'])
                st.text_input(t["sb_email"], value=st.session_state['user_email'], disabled=True)
                st.text_input(t["prof_sub"], value=f"{st.session_state['user_tier']} Plan", disabled=True)
                submit_update = st.form_submit_button(t["sb_update"], use_container_width=True)

                if submit_update:
                    fn_val = new_fn.strip()
                    ln_val = new_ln.strip()
                    if st.session_state.get('access_token'):
                        with st.spinner("Updating..."):
                            url = f"{os.environ.get('SUPABASE_URL', '').strip('/')}/auth/v1/user"
                            headers = {
                                "apikey": os.environ.get('SUPABASE_KEY', ''),
                                "Authorization": f"Bearer {st.session_state['access_token']}",
                                "Content-Type": "application/json"
                            }
                            payload = {"data": {"first_name": fn_val, "last_name": ln_val}}
                            res = requests.put(url, headers=headers, json=payload)
                            if res.status_code == 200:
                                st.session_state['user_fn'] = fn_val
                                st.session_state['user_ln'] = ln_val
                                st.success(t["msg_updated"])
                            else:
                                st.error("Error updating profile.")

sel_theme = st.session_state['app_theme']

if sel_theme == "🌙 Dark":
    st.markdown("""
    <style> 
    [data-testid="stAppViewContainer"] { background-color: #0E1117 !important; } 
    [data-testid="stSidebar"] { background-color: #000000 !important; } 
    .hero-text { color: #F8FAFC !important; }
    .sub-hero { color: #E2E8F0 !important; }
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3,
    [data-testid="stAppViewContainer"] h4 { color: #F8FAFC !important; }
    div[data-testid="stAppViewContainer"] .stMarkdown p { color: #E2E8F0; }
    div[data-testid="stAlert"] .stMarkdown p { color: inherit !important; }
    [data-testid="stCaptionContainer"] p { color: #94A3B8 !important; }
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] div { color: #F8FAFC !important; }
    [data-testid="stMetricLabel"] > div > div > p { color: #94A3B8 !important; }
    summary p { color: #F8FAFC !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] div { 
        color: #E2E8F0 !important; font-weight: 500 !important; text-shadow: none !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { 
        color: #FFFFFF !important; text-shadow: none !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="base-input"] { 
        background-color: #0F172A !important; border: 1px solid #334155 !important; 
    }
    input[type="text"], input[type="password"] { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }
    div[data-baseweb="select"] > div { background-color: #0F172A !important; border: 1px solid #334155 !important; }
    div[data-baseweb="select"] span { color: #FFFFFF !important; font-weight: 500 !important; }
    div[data-baseweb="select"] svg { fill: #FFFFFF !important; } 
    ul[data-baseweb="menu"] { background-color: #0F172A !important; border: 1px solid #334155 !important; }
    li[data-baseweb="menu-item"] { color: #FFFFFF !important; }
    div.stButton > button { background-color: #1E293B !important; color: #FFFFFF !important; border: 1px solid #334155 !important; }
    div.stButton > button:hover { border-color: #10B981 !important; color: #10B981 !important; }
    </style>
    """, unsafe_allow_html=True)
elif sel_theme == "☀️ Light":
    st.markdown("""
    <style> 
    [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; } 
    [data-testid="stSidebar"] { background-color: #F8F9FA !important; } 
    .hero-text { color: #0F172A !important; }
    .sub-hero { color: #334155 !important; }
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3,
    [data-testid="stAppViewContainer"] h4 { color: #0F172A !important; }
    div[data-testid="stAppViewContainer"] .stMarkdown p { color: #1E293B; }
    div[data-testid="stAlert"] .stMarkdown p { color: inherit !important; }
    [data-testid="stCaptionContainer"] p { color: #64748B !important; }
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] div { color: #0F172A !important; }
    [data-testid="stMetricLabel"] > div > div > p { color: #64748B !important; }
    summary p { color: #0F172A !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] div { 
        color: #1E293B !important; font-weight: 500 !important; text-shadow: none !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { 
        color: #000000 !important; text-shadow: none !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="base-input"] { background-color: #FFFFFF !important; border: 1px solid #D1D5DB !important; }
    input[type="text"], input[type="password"] { color: #000000 !important; -webkit-text-fill-color: #000000 !important; }
    div[data-baseweb="select"] > div { background-color: #FFFFFF !important; border: 1px solid #D1D5DB !important; }
    div[data-baseweb="select"] span { color: #000000 !important; font-weight: 500 !important; }
    div[data-baseweb="select"] svg { fill: #000000 !important; } 
    ul[data-baseweb="menu"] { background-color: #FFFFFF !important; border: 1px solid #D1D5DB !important;}
    li[data-baseweb="menu-item"] { color: #000000 !important; }
    div.stButton > button { background-color: #F3F4F6 !important; color: #111827 !important; border: 1px solid #D1D5DB !important; }
    div.stButton > button:hover { border-color: #10B981 !important; color: #10B981 !important; }
    </style>
    """, unsafe_allow_html=True)

if not st.session_state['logged_in']:
    st.sidebar.markdown("---")
    st.sidebar.header(t["sb_member"])
    if st.sidebar.button(t["sb_login"], use_container_width=True):
        show_login_modal()
    if st.sidebar.button(t["sb_signup"], use_container_width=True):
        show_signup_modal()
else:
    st.sidebar.markdown("---")
    st.sidebar.success("👤 Logged in as: Member")

    try:
        notifs_response = supabase_client.table('user_notifications').select('*').eq('user_email', st.session_state['user_email']).eq('is_read', False).execute()
        if notifs_response.data:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 🔔 Notifications")
            for alert in notifs_response.data:
                st.sidebar.warning(alert['message'])

            if st.sidebar.button("Mark All as Read", use_container_width=True):
                supabase_client.table('user_notifications').update({'is_read': True}).eq('user_email', st.session_state['user_email']).execute()
                st.rerun()
    except Exception:
        pass

    if st.session_state['user_tier'] == 'Free':
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### {t['sb_unlock']}")
        st.sidebar.link_button("💎 Upgrade to Premium (99 PLN/mo)", STRIPE_LINK, type="primary", use_container_width=True)

    st.sidebar.markdown("---")
    if st.sidebar.button(t["sb_logout"], use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['user_email'] = ""
        st.session_state['user_tier'] = 'Free'
        st.session_state['user_fn'] = ""
        st.session_state['user_ln'] = ""
        st.session_state['access_token'] = ""
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

is_locked_mode = (not is_premium) and (selected_trans_id == 1)

prop_type_label = st.sidebar.selectbox(t["sb_type"], options=list(PROPERTY_TYPES.keys()))
selected_type_id = PROPERTY_TYPES[prop_type_label]

st.sidebar.markdown("---")
st.sidebar.header(t["sb_filters"])

with st.spinner(f'Fetching live data...'):
    df = load_data(selected_trans_id, selected_type_id)

if not df.empty:
    df_active = df[df['status'] == 'ACTIVE'].copy() if 'status' in df.columns else df.copy()
    df_sold = df[df['status'] == 'SOLD'].copy() if 'status' in df.columns else pd.DataFrame()

    default_max = 2000000 if selected_trans_id == 1 else 50000
    max_val = int(df_active['price_pln'].max()) if not df_active.empty else default_max
    min_val = int(df_active['price_pln'].min()) if not df_active.empty else 0

    max_price = st.sidebar.slider(t["sb_budget"], min_value=min_val, max_value=max_val, value=max_val, step=5000 if selected_trans_id == 2 else 50000)
    districts = st.sidebar.multiselect(t["sb_districts"], options=sorted(df_active['district'].dropna().unique()), default=[])

    filtered_df = df_active[df_active['price_pln'] <= max_price].copy()
    if districts: filtered_df = filtered_df[filtered_df['district'].isin(districts)]
    filtered_df = filtered_df.sort_values(by='price_per_sqm', ascending=True)

    history_df = load_price_history()
    trend_dict = {}
    if not history_df.empty:
        history_df['new_price_pln'] = pd.to_numeric(history_df['new_price_pln'], errors='coerce')
        history_df = history_df.sort_values(by=['listing_id', 'change_date'])
        trend_dict = history_df.groupby('listing_id')['new_price_pln'].apply(list).to_dict()

    st.markdown('<div class="ai-badge">PropTech AI Engine v2.0</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="hero-text">{t["hero_title"]}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-hero">{t["hero_sub"]}</p>', unsafe_allow_html=True)

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
        """, unsafe_allow_html=True)

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

    top_deals = []
    if not filtered_df.empty and 'sqm' in filtered_df.columns:
        dist_avg = filtered_df.groupby('district')['price_per_sqm'].mean().to_dict()
        temp_df = filtered_df.dropna(subset=['sqm', 'price_pln']).copy()
        if not temp_df.empty:
            temp_df['dist_avg_sqm'] = temp_df['district'].map(dist_avg)
            temp_df['est_market_price'] = temp_df['dist_avg_sqm'] * temp_df['sqm']
            temp_df['profit'] = temp_df['est_market_price'] - temp_df['price_pln']
            temp_df = temp_df[temp_df['profit'] <= (temp_df['price_pln'] * 0.50)]
            temp_df = temp_df.sort_values(by='profit', ascending=False)
            top_deals = temp_df.head(3).to_dict('records')

    default_boxes = [
        {"color": st.success, "title": "**📍 Mokotów (Live Anomaly)**", "body": f"📉 **Est. Market:** 850,000 PLN\n🎯 **Listed Price:** 690,000 PLN\n💸 **Potential Margin:** ~160,000 PLN\n\n⚡ *Status: {t['active']}*"},
        {"color": st.info, "title": "**📍 Wola (High ROI)**", "body": f"📉 **Est. Market:** 600,000 PLN\n🎯 **Listed Price:** 510,000 PLN\n💸 **Potential Margin:** ~90,000 PLN\n\n⚡ *Status: {t['active']}*"},
        {"color": st.warning, "title": "**📍 Śródmieście (Urgent Sale)**", "body": f"📉 **Est. Market:** 1,200,000 PLN\n🎯 **Listed Price:** 980,000 PLN\n💸 **Potential Margin:** ~220,000 PLN\n\n⚡ *Status: {t['active']}*"}
    ]

    boxes = [cs1, cs2, cs3]
    for i in range(3):
        with boxes[i]:
            if i < len(top_deals):
                deal = top_deals[i]
                dist = deal['district']
                market_avg = deal['est_market_price']
                price = deal['price_pln']
                profit = deal['profit']
                link = deal['url_link']
                color_func = st.success if i == 0 else (st.info if i == 1 else st.warning)

                body_text = f"📉 **Est. Market:** {market_avg:,.0f} PLN\n🎯 **Listed Price:** {price:,.0f} PLN\n💸 **Potential Margin:** ~{profit:,.0f} PLN\n\n⚡ *Status: {t['active']}* [🔗 View]({link})"
                color_func(f"**📍 {dist} (Live Anomaly)**\n\n{body_text}")
            else:
                default_boxes[i]["color"](f"{default_boxes[i]['title']}\n\n{default_boxes[i]['body']}")

    with st.expander("🤖 Transparency: How Does Our AI Methodology Work?"):
        st.markdown("""
        Our platform operates purely on emotionless data and Natural Language Processing (NLP):
        1. **Real-Time Arbitrage:** The system continuously fetches live price-per-square-meter averages for similar properties directly from our Supabase data warehouse.
        2. **Price Anomaly Detection:** If a listing's price falls significantly (usually **20% - 30% below**) its district's current moving average, it triggers our radar.
        3. **Gemini AI Language Processing:** Our integrated AI reads Polish/English descriptions to gauge seller motivation (e.g., extracting keywords like *"Urgent"*, *"Leaving the country"*, *"Needs renovation"*).
        4. **Investment Scoring:** We combine the potential profit margin, district liquidity speed, and AI textual sentiment into a proprietary **100-point Investment Score**, presenting only the most lucrative deals to you.
        """)
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5, tab7, tab8, tab9 = st.tabs([
        t["tab1"], t["tab2"], t["tab3"], t["tab4"], t["tab5"], t["tab7"], t["tab8"], t["tab9"]
    ])

    with tab1:
        st.subheader(t["tab1"])
        c1, c2 = st.columns(2)
        with c1: st.bar_chart(filtered_df['district'].value_counts())
        with c2:
            chart_data = filtered_df.groupby('district')['price_per_sqm'].mean().dropna().sort_values()
            if not chart_data.empty: st.area_chart(chart_data)
            else: st.info("No data available.")

        st.markdown(f"""
            <div style="background-color: rgba(255, 193, 7, 0.1); padding: 18px; border-radius: 12px; border: 1px solid #FFC107; margin-bottom: 20px;">
                <h4 style="color: #FFC107; margin-top: 0;">{t["vip_title"]}</h4>
                <p style="font-size: 14px; margin-bottom: 15px;">{t["vip_desc"]}</p>
            </div>
        """, unsafe_allow_html=True)
        st.link_button(t["vip_btn"], EXPANDER_LINK, type="primary", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

        display_df = filtered_df[['property_id', 'district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link', 'status']].copy()

        if is_locked_mode:
            display_df, showing_limit_msg = apply_limit(display_df, t)
        else:
            showing_limit_msg = False

        if st.session_state['logged_in']:
            display_df['❤️ Track'] = display_df['property_id'].isin(user_fav_ids)
            cols = ['❤️ Track', 'district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link', 'status', 'property_id']
        else:
            cols = ['district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link', 'status', 'property_id']

        display_df = display_df[cols]

        column_config = {
            "property_id": None, "district": t["th_dist"],
            "price_pln": st.column_config.TextColumn(t["th_price"]) if is_locked_mode else st.column_config.NumberColumn(t["th_price"], format="%.0f PLN"),
            "sqm": st.column_config.NumberColumn(t["th_sqm"], format="%.0f"),
            "rooms": t["th_rooms"],
            "price_per_sqm": st.column_config.NumberColumn(t["th_psqm"], format="%.0f PLN"),
            "url_link": st.column_config.TextColumn(t["th_link"]) if is_locked_mode else st.column_config.LinkColumn(t["th_link"], display_text="View 🔗"),
            "status": t["th_status"]
        }

        if st.session_state['logged_in']:
            edited_df = st.data_editor(display_df, column_config=column_config, hide_index=True, use_container_width=True, disabled=["district", "price_pln", "sqm", "rooms", "price_per_sqm", "url_link", "status"])
            process_favorite_edits(edited_df, display_df, st.session_state['user_email'])
        else:
            st.dataframe(display_df, column_config=column_config, hide_index=True, use_container_width=True)
            st.info("💡 **Log in to track properties and receive price drop alerts.**")

        if showing_limit_msg:
            st.markdown(f"<div class='lock-overlay'>{t['lock_msg']}</div>", unsafe_allow_html=True)

    with tab2:
        st.subheader(t["tab2_title"])

        col_list, col_map = st.columns([2, 3])

        analytics_data = []
        for district, group in filtered_df.groupby('district'):
            if district in DISTRICT_COORDS:
                avg_sqm = group['price_per_sqm'].mean()
                if pd.notna(avg_sqm) and avg_sqm > 0:
                    analytics_data.append({
                        'District': district,
                        'Avg Price/m²': int(avg_sqm),
                        'Total Listings': len(group),
                        'lat': float(DISTRICT_COORDS[district]['lat']),
                        'lon': float(DISTRICT_COORDS[district]['lon'])
                    })

        df_summary = pd.DataFrame(analytics_data)

        with col_list:
            st.markdown(t["tab2_rankings"])
            if not df_summary.empty:
                st.dataframe(
                    df_summary[['District', 'Avg Price/m²', 'Total Listings']].sort_values(by='Avg Price/m²', ascending=False),
                    column_config={
                        "District": t["th_dist"],
                        "Avg Price/m²": st.column_config.NumberColumn(t["th_avg_price_sqm"], format="%d PLN"),
                        "Total Listings": t["th_active_ads"]
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Awaiting market data filters...")

        with col_map:
            st.markdown(t["tab2_map"])
            if not df_summary.empty:
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    df_summary,
                    get_position='[lon, lat]',
                    get_fill_color=[16, 185, 129, 200],
                    get_radius=500,
                    pickable=True,
                    auto_highlight=True
                )

                view_state = pdk.ViewState(
                    latitude=52.2297,
                    longitude=21.0122,
                    zoom=10,
                    pitch=0,
                    bearing=0
                )

                r = pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    map_style="light",
                    tooltip={
                        "html": "<b>District:</b> {District}<br/><b>Price:</b> {Avg Price/m²} PLN/m²",
                        "style": {"backgroundColor": "#0F172A", "color": "white", "fontFamily": "monospace"}
                    }
                )
                st.pydeck_chart(r)
            else:
                st.warning("No geographic data available for current selection.")

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

                        display_roi_full = roi_df[['property_id', 'district', 'price_pln', 'est_monthly_rent', 'roi_percent', 'amortization_years', 'url_link']]

                        if is_locked_mode:
                            display_roi, roi_showing_limit = apply_limit(display_roi_full, t)
                        else:
                            display_roi = display_roi_full
                            roi_showing_limit = False

                        cols_roi = ['❤️ Track', 'district', 'price_pln', 'est_monthly_rent', 'roi_percent', 'amortization_years', 'url_link', 'property_id'] if st.session_state['logged_in'] else ['district', 'price_pln', 'est_monthly_rent', 'roi_percent', 'amortization_years', 'url_link', 'property_id']
                        if st.session_state['logged_in']: display_roi['❤️ Track'] = display_roi['property_id'].isin(user_fav_ids)
                        display_roi = display_roi[cols_roi]

                        col_conf_roi = {
                            "property_id": None, "district": t["th_dist"],
                            "price_pln": st.column_config.TextColumn(t["th_price"]) if is_locked_mode else st.column_config.NumberColumn(t["th_price"], format="%.0f PLN"),
                            "est_monthly_rent": st.column_config.NumberColumn(t["th_est_rent"], format="%.0f PLN"),
                            "roi_percent": st.column_config.NumberColumn(t["th_roi"], format="%.1f%%"),
                            "amortization_years": st.column_config.NumberColumn(t["th_amort"], format="%.1f"),
                            "url_link": st.column_config.TextColumn(t["th_link"]) if is_locked_mode else st.column_config.LinkColumn(t["th_link"], display_text="View 🔗")
                        }
                        st.dataframe(display_roi.head(50), column_config=col_conf_roi, hide_index=True, use_container_width=True)
                        if roi_showing_limit:
                            st.markdown(f"<div class='lock-overlay'>{t['lock_msg']}</div>", unsafe_allow_html=True)
        else:
            st.info(t["roi_only_sale"])

    with tab4:
        st.subheader(t["tab4"])
        st.markdown(t["drop_sub"])
        with st.spinner(t["drop_analyzing"]):
            history_df = load_price_history()
            if not history_df.empty and 'property_id' in filtered_df.columns:
                history_df['new_price_pln'] = pd.to_numeric(history_df['new_price_pln'], errors='coerce')
                history_df = history_df.sort_values(by=['listing_id', 'change_date'])

                first_prices = history_df.groupby('listing_id')['new_price_pln'].first().rename('Old Price')
                last_prices = history_df.groupby('listing_id')['new_price_pln'].last().rename('Current Price')
                drops = pd.concat([first_prices, last_prices], axis=1)
                drops = drops[drops['Old Price'] > drops['Current Price']].copy()
                drops['Discount (PLN)'] = drops['Old Price'] - drops['Current Price']
                drops['Discount (%)'] = (drops['Discount (PLN)'] / drops['Old Price']) * 100

                prop_map_df = supabase_client.table('listings').select('listing_id, property_id').in_('listing_id', drops.index.tolist()).execute()
                if prop_map_df.data:
                    id_to_prop = {row['listing_id']: row['property_id'] for row in prop_map_df.data}
                    drops['property_id'] = drops.index.map(id_to_prop)

                    radar_df = pd.merge(drops, filtered_df, on='property_id', how='inner')

                    if not radar_df.empty:
                        radar_df = radar_df.sort_values(by='Discount (%)', ascending=False)

                        display_radar_full = radar_df[['property_id', 'district', 'Old Price', 'Current Price', 'Discount (PLN)', 'Discount (%)', 'price_per_sqm', 'url_link']]

                        if is_locked_mode:
                            display_radar, radar_showing_limit = apply_limit(display_radar_full, t)
                        else:
                            display_radar = display_radar_full
                            radar_showing_limit = False

                        cols_radar = ['❤️ Track', 'district', 'Old Price', 'Current Price', 'Discount (PLN)', 'Discount (%)', 'price_per_sqm', 'url_link', 'property_id'] if st.session_state['logged_in'] else ['district', 'Old Price', 'Current Price', 'Discount (PLN)', 'Discount (%)', 'price_per_sqm', 'url_link', 'property_id']
                        if st.session_state['logged_in']: display_radar['❤️ Track'] = display_radar['property_id'].isin(user_fav_ids)
                        display_radar = display_radar[cols_radar]

                        col_conf_radar = {
                            "property_id": None, "district": t["th_dist"],
                            "Old Price": st.column_config.NumberColumn(t["th_old"], format="%.0f PLN"),
                            "Current Price": st.column_config.TextColumn(t["th_cur"]) if is_locked_mode else st.column_config.NumberColumn(t["th_cur"], format="%.0f PLN"),
                            "Discount (PLN)": st.column_config.TextColumn(t["th_disc"]) if is_locked_mode else st.column_config.NumberColumn(t["th_disc"], format="-%.0f PLN"),
                            "Discount (%)": st.column_config.NumberColumn(t["th_disc_pct"], format="-%.1f%%"),
                            "price_per_sqm": st.column_config.NumberColumn(t["th_psqm"], format="%.0f PLN"),
                            "url_link": st.column_config.TextColumn(t["th_link"]) if is_locked_mode else st.column_config.LinkColumn(t["th_link"], display_text="View 🔗")
                        }
                        st.dataframe(display_radar, column_config=col_conf_radar, hide_index=True, use_container_width=True)
                        if radar_showing_limit:
                            st.markdown(f"<div class='lock-overlay'>{t['lock_msg']}</div>", unsafe_allow_html=True)
                    else:
                        st.info(t["drop_none"])
                else:
                    st.info(t["drop_none"])
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

            st.markdown("---")
            st.link_button(t["calc_exp_btn"], EXPANDER_LINK, type="primary", use_container_width=True)
            st.caption(t["calc_exp_sub"])

        with calc_col2:
            st.markdown(t["calc_reno"])
            st.markdown(t["ai_audit_title"])
            st.caption(t["ai_audit_sub"])

            target_url_input = st.text_input(t["ai_paste_url"], placeholder="https://www.otodom.pl/...", key="deep_audit_link")
            audit_sqm = st.number_input(t["ai_size_calc"], min_value=10, max_value=500, value=50)

            if st.button(t["ai_btn_search"], use_container_width=True):
                if check_limit(t):
                    if target_url_input:
                        with st.spinner(t["ai_spinner"]):
                            res = supabase_client.table('listings').select('description, image_urls').eq('url_link', target_url_input).execute()

                            found_data = None
                            if res.data and res.data[0].get('description'):
                                found_data = {
                                    'description': res.data[0]['description'],
                                    'image_urls': res.data[0].get('image_urls', [])
                                }
                                st.info(t["ai_local_found"])
                            else:
                                try:
                                    from Scrapers.scraper import fetch_single_listing_data
                                    found_data = fetch_single_listing_data(target_url_input)
                                except ImportError:
                                    from scraper import fetch_single_listing_data
                                    found_data = fetch_single_listing_data(target_url_input)

                            if found_data:
                                try:
                                    from Scrapers.ai_engine import GroqProptechAI
                                    AI_Class = GroqProptechAI
                                except ImportError:
                                    from Scrapers.ai_engine import GeminiAnalyzer
                                    AI_Class = GeminiAnalyzer

                                groq_agent = AI_Class(os.getenv("GROQ_API_KEY"))
                                ai_lang_map = {"🇬🇧 EN": "English", "🇵🇱 PL": "Polish", "🇹🇷 TR": "Turkish"}
                                target_language = ai_lang_map.get(st.session_state['app_lang'], "English")

                                report = groq_agent.analyze_with_vision(
                                    found_data.get('description', ''),
                                    found_data.get('image_urls', []),
                                    sqm=audit_sqm,
                                    category=f"{prop_type_label} - {label}",
                                    language=target_language
                                )

                                st.session_state['usage_counter'] += 1
                                st.success(t["ai_success"])
                                st.markdown(report)
                                st.info(t["audits_left"].format(FREE_TOOL_USAGE_LIMIT - st.session_state['usage_counter']))
                            else:
                                st.error(t["ai_error"])
                    else:
                        st.warning(t["ai_warn_empty"])

            st.markdown("---")
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

    with tab7:
        st.subheader(t["tab7"])
        st.markdown(t["for_sub"])
        with st.spinner(t["for_train"]):
            forecast_df = predict_future_prices(df, selected_trans_id)
            if not forecast_df.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(t["for_top3"])
                    for index, row in forecast_df.head(3).iterrows(): st.success(f"**📍 {row['District']}**\n\n{t['for_growth']} **+%.1f%%**" % row['Growth Potential (%)'])
                with c2:
                    if is_locked_mode:
                        st.warning(t["for_lock"])
                        st.link_button(t["sb_unlock"], STRIPE_LINK, type="primary")
                        display_forecast = forecast_df.head(3).copy()
                    else:
                        if is_premium:
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

    with tab9:
        st.subheader(t["ht_title"])
        st.markdown(t["ht_sub"])

        target_hist_url = st.text_input(t["ai_paste_url"], placeholder="https://www.otodom.pl/...", key="hist_trend_link")

        if st.button(t["ht_btn"], use_container_width=True):
            if not target_hist_url:
                st.warning(t["ht_err_url"])
            else:
                with st.spinner(t["ht_spinner"]):
                    res_prop = supabase_client.table('listings').select('listing_id, property_id, loc_id').eq('url_link', target_hist_url).execute()

                    if res_prop.data:
                        prop_id = res_prop.data[0]['property_id']
                        loc_id = res_prop.data[0]['loc_id']
                        list_id = res_prop.data[0]['listing_id']

                        hist_data = supabase_client.table('price_history').select('new_price_pln, change_date').eq('listing_id', list_id).execute()

                        if hist_data.data:
                            hist_df = pd.DataFrame(hist_data.data)
                            hist_df['change_date'] = pd.to_datetime(hist_df['change_date'])
                            hist_df = hist_df.sort_values(by='change_date')

                            if len(hist_df) < 6:
                                base_price = hist_df['new_price_pln'].iloc[0]
                                base_date = hist_df['change_date'].iloc[0]

                                sim_dates = []
                                sim_prices = []
                                for i in range(6, 0, -1):
                                    sim_dates.append(base_date - timedelta(days=30*i))
                                    noise = np.random.uniform(-0.015, 0.02)
                                    sim_prices.append(base_price * (1 - (i * 0.005)) * (1 + noise))

                                sim_df = pd.DataFrame({'change_date': sim_dates, 'new_price_pln': sim_prices})
                                hist_df = pd.concat([sim_df, hist_df], ignore_index=True)
                                st.caption(t["ht_sim_note"])

                            dist_avg = 0
                            if loc_id:
                                avg_res = supabase_client.table('district_market_stats').select('avg_price_per_sqm').eq('loc_id', loc_id).eq('trans_id', selected_trans_id).eq('type_id', selected_type_id).execute()
                                if avg_res.data and avg_res.data[0].get('avg_price_per_sqm'):

                                    sqm_res = supabase_client.table('listings').select('sqm').eq('property_id', prop_id).execute()
                                    if sqm_res.data and sqm_res.data[0].get('sqm'):
                                        dist_avg = avg_res.data[0]['avg_price_per_sqm'] * sqm_res.data[0]['sqm']

                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=hist_df['change_date'], y=hist_df['new_price_pln'],
                                fill='tozeroy',
                                mode='lines+markers',
                                line=dict(color='#10B981', width=3, shape='linear'),
                                marker=dict(size=8, color='#FFFFFF', line=dict(color='#10B981', width=2)),
                                name='Property Price'
                            ))

                            if dist_avg > 0:
                                fig.add_trace(go.Scatter(
                                    x=[hist_df['change_date'].min(), hist_df['change_date'].max()],
                                    y=[dist_avg, dist_avg],
                                    mode='lines',
                                    line=dict(color='#4A90E2', width=2, dash='dash'),
                                    name='District Average'
                                ))

                            fig.update_layout(
                                title=t["ht_chart_title"],
                                xaxis_title="",
                                yaxis_title="Price (PLN)",
                                template="plotly_dark" if sel_theme == "🌙 Dark" else "plotly_white",
                                hovermode="x unified",
                                margin=dict(l=0, r=0, t=40, b=0)
                            )
                            st.plotly_chart(fig, use_container_width=True, config={'responsive': True, 'displaylogo': False, 'toImageButtonOptions': {'format': 'png', 'scale': 2}})

                            mail_bot = EmailManager()
                            html_icerik = mail_bot.create_html_template(
                                title="Property Analysis",
                                content_lines=[f"Property Price Data for: {target_hist_url}", "Price data has been generated."],
                                property_url=target_hist_url
                            )
                            if st.button(t["email_btn"], use_container_width=True):
                                if mail_bot.send_user_email(st.session_state['user_email'], "Property Analysis Report", html_icerik):
                                    st.success(t["email_success"])
                                else:
                                    st.error(t["email_fail"])
                        else:
                            st.error(t["ht_err_not_found"])
                    else:
                        st.error(t["ht_err_not_found"])

    if st.session_state['logged_in'] and user_fav_ids:
        st.markdown("---")
        st.subheader(f"⭐ {t['tab6']}")
        with st.expander(t["fav_here"], expanded=True):
            fav_df = df[df['property_id'].isin(user_fav_ids)].copy()
            if fav_df.empty: st.warning(t["fav_sold"])
            else:
                fav_df['❤️ Track'] = True
                if is_locked_mode:
                    fav_df['price_pln'] = t["locked"]
                    fav_df['url_link'] = t["locked_link"]
                fav_cols = ['❤️ Track', 'district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link', 'property_id']
                display_fav = fav_df[fav_cols]
                col_conf_fav = {
                    "property_id": None, "district": t["th_dist"],
                    "price_pln": st.column_config.TextColumn(t["th_price"]) if is_locked_mode else st.column_config.NumberColumn(t["th_price"], format="%.0f PLN"),
                    "sqm": st.column_config.NumberColumn(t["th_sqm"], format="%.0f"),
                    "rooms": t["th_rooms"],
                    "price_per_sqm": st.column_config.NumberColumn(t["th_psqm"], format="%.0f PLN"),
                    "url_link": st.column_config.TextColumn(t["th_link"]) if is_locked_mode else st.column_config.LinkColumn(t["th_link"], display_text="View 🔗")
                }
                edited_my_favs = st.data_editor(display_fav, column_config=col_conf_fav, hide_index=True, use_container_width=True, disabled=["district", "price_pln", "sqm", "rooms", "price_per_sqm", "url_link"])
                for i, row in edited_my_favs.iterrows():
                    if not row['❤️ Track']:
                        toggle_favorite(st.session_state['user_email'], row['property_id'], False)
                        st.rerun()
else:
    st.info("No active listings found in the system matching current criteria.")

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #64748b; font-size: 13px; margin-top: 50px; padding: 20px; line-height: 1.6;'>
    <p><strong>Contact Us:</strong> Have feedback, found a bug, want a custom feature, or interested in special offers? Reach out at: <b>warsaw.proptech@gmail.com</b></p>
    <hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 20px auto; width: 60%;'>
    <p><strong>Legal Disclaimer:</strong> This platform provides AI-driven market intelligence and data analysis for <b>informational purposes only</b>. The contents of this site do not constitute financial, investment, or real estate advice. Market data, price trends, and AI forecasts are based on historical analysis and simulations; they are not guaranteed. All investment decisions are the user's sole responsibility. We are not responsible for any financial losses or damages resulting from the use of this data.</p>
    <p>© 2026 Warsaw AI PropTech. All rights reserved.</p>
</div>
""", unsafe_allow_html=True)