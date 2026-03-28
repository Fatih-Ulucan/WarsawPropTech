import streamlit as st
import pandas as pd
import requests
import os
from pathlib import Path
from dotenv import load_dotenv
import io

st.set_page_config(page_title="Warsaw AI PropTech", page_icon="🏢", layout="wide")

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
def load_data(t_id):
    clean_url = SUPABASE_URL.strip("/")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Range-Unit": "items"
    }

    all_data = []  
    limit = 1000   
    offset = 0     

    try:
        while True:
            table_url = f"{clean_url}/rest/v1/listings?trans_id=eq.{t_id}&select=*&limit={limit}&offset={offset}"

            response = requests.get(table_url, headers=headers, timeout=15)

            if response.status_code == 200:
                chunk = response.json()

                if not chunk: 
                    break

                all_data.extend(chunk) 

                if len(chunk) < limit: 
                    break

                offset += limit 
            else:
                st.error(f"API Error: {response.text}")
                break

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        df['district'] = df['loc_id'].map(LOCATION_MAP)

        df['price_pln'] = pd.to_numeric(df['price_pln'], errors='coerce')
        df['sqm'] = pd.to_numeric(df['sqm'], errors='coerce')
        df['price_per_sqm'] = pd.to_numeric(df['price_per_sqm'], errors='coerce')

        df = df.dropna(subset=['price_pln'])

        df['url_link_html'] = df['url_link'].apply(lambda x: f'<a href="{x}" target="_blank" style="color:#1E90FF; font-weight:bold;">View Listing 🔗</a>')

        return df

    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

st.sidebar.header("🎯 Main Selection")
transaction_type = st.sidebar.selectbox(
    "Transaction Type",
    options=[("Sale", 1), ("Rent", 2)],
    format_func=lambda x: x[0]
)
selected_id = transaction_type[1]

label = "Sale" if selected_id == 1 else "Rent"

st.title(f"🏢 Warsaw AI PropTech - {label} Radar")
st.markdown(f"The most recent **{label}** real estate opportunities found by our AI bot.")

with st.spinner(f'Fetching current {label} listings from Supabase...'):
    df = load_data(selected_id)

if not df.empty:
    st.sidebar.header("🔍 Investor Filters")

    max_val = int(df['price_pln'].max())
    min_val = int(df['price_pln'].min())

    max_price = st.sidebar.slider(
        "Maximum Budget (PLN)",
        min_value=min_val,
        max_value=max_val,
        value=max_val,
        step=5000 if selected_id == 2 else 50000
    )

    districts = st.sidebar.multiselect(
        "Districts (All if none selected)",
        options=sorted(df['district'].dropna().unique()),
        default=[]
    )

    filtered_df = df[df['price_pln'] <= max_price].copy()
    if districts:
        filtered_df = filtered_df[filtered_df['district'].isin(districts)]

    filtered_df = filtered_df.sort_values(by='price_per_sqm', ascending=True)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Listings Found", f"{len(filtered_df)}")
    col2.metric("Average Price", f"{filtered_df['price_pln'].mean():,.0f} PLN")
    col3.metric("Average Price / m²", f"{filtered_df['price_per_sqm'].mean():,.0f} PLN")
    st.markdown("---")

    
    st.subheader("📊 Market Overview")
    c1, c2 = st.columns(2)
    with c1:
        st.bar_chart(filtered_df['district'].value_counts())
    with c2:
        chart_data = filtered_df.groupby('district')['price_per_sqm'].mean().sort_values()
        st.area_chart(chart_data)

    st.subheader(f"📋 Current {label} Listings")

    display_df = filtered_df[['district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link_html']].copy()
    display_df.columns = ['District', 'Price (PLN)', 'm²', 'Rooms', 'Price/m²', 'Otodom Link']

    st.write(display_df.to_html(escape=False, index=False, classes='stTable'), unsafe_allow_html=True)

else:
    st.info(f"There are currently no active {label.lower()} listings in the system. The bot might be running in the background.")