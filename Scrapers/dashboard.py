import streamlit as st
import pandas as pd
import requests
import os
from pathlib import Path
from dotenv import load_dotenv
import io 

current_dir = Path(__file__).resolve().parent
base_dir = current_dir.parent
env_path = base_dir / ".env"

if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8-sig") as f:
            clean_content = f.read()
        load_dotenv(stream=io.StringIO(clean_content), override=True)
    except Exception as e:
        st.error(f"❌ Failed to parse .env file: {e}")
else:
    st.error(f"❌ .env file NOT FOUND at: {env_path}")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    SUPABASE_URL = SUPABASE_URL.strip()
    SUPABASE_KEY = SUPABASE_KEY.strip()
else:
    st.error(f"❌ CRITICAL ERROR: Supabase keys are empty! Check your .env file content.")
    st.stop()
LOCATION_MAP = {
    1: 'Mokotów', 2: 'Praga-Południe', 3: 'Ursynów', 4: 'Wola',
    5: 'Białołęka', 6: 'Bielany', 7: 'Bemowo', 8: 'Targówek',
    9: 'Śródmieście', 10: 'Wawer', 11: 'Ochota', 12: 'Ursus',
    13: 'Praga-Północ', 14: 'Włochy', 15: 'Wilanów', 16: 'Wesoła',
    17: 'Żoliborz', 18: 'Rembertów'
}

@st.cache_data(ttl=300) 
def load_data():
    clean_url = SUPABASE_URL.strip("/")
    table_url = f"{clean_url}/rest/v1/listings?is_active=eq.true&trans_id=eq.1&select=*"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Range-Unit": "items"
    }

    try:
        response = requests.get(table_url, headers=headers, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            if not df.empty:
                df['district'] = df['loc_id'].map(LOCATION_MAP)
                df['url_link'] = df['url_link'].apply(lambda x: f'<a href="{x}" target="_blank" style="color:#1E90FF; font-weight:bold;">View Listing 🔗</a>')
            return df
        else:
            st.error(f"API Error: {response.text}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

st.title("🏢 Warsaw AI PropTech Radar")
st.markdown("The most recent **For Sale** real estate opportunities found by our AI bot.")

with st.spinner('Fetching current listings from Supabase database...'):
    df = load_data()

if not df.empty:
    st.sidebar.header("🔍 Investor Filters")

    max_price = st.sidebar.slider(
        "Maximum Budget (PLN)",
        min_value=int(df['price_pln'].min()),
        max_value=int(df['price_pln'].max()),
        value=int(df['price_pln'].max()),
        step=50000
    )

    districts = st.sidebar.multiselect(
        "Districts (All if none selected)",
        options=sorted(df['district'].dropna().unique()),
        default=[]
    )

    filtered_df = df[df['price_pln'] <= max_price]
    if districts:
        filtered_df = filtered_df[filtered_df['district'].isin(districts)]

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Listings Found", f"{len(filtered_df)}")
    col2.metric("Average Price", f"{filtered_df['price_pln'].mean():,.0f} PLN")
    col3.metric("Average Price / m²", f"{filtered_df['price_per_sqm'].mean():,.0f} PLN")
    st.markdown("---")

    st.subheader("📋 Current Listings")

    display_df = filtered_df[['district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link']].copy()
    display_df.columns = ['District', 'Price (PLN)', 'm²', 'Rooms', 'Price/m²', 'Otodom Link']

    st.write(display_df.to_html(escape=False, index=False, classes='stTable'), unsafe_allow_html=True)

else:
    st.info("There are currently no active listings in the system. The bot might be running in the background.")