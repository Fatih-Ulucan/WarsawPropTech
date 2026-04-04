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

PROPERTY_TYPES = {
    "Apartment": 1,
    "Commercial/Retail": 2,
    "Land": 3,
    "Office": 4,
    "WareHouse": 5,
    "Garage": 6
}

@st.cache_data(ttl=300)
def load_data(trans_id, type_id):
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
            table_url = f"{clean_url}/rest/v1/listings?trans_id=eq.{trans_id}&type_id=eq.{type_id}&select=*&limit={limit}&offset={offset}"
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
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_rent_averages(type_id):
    df_rent = load_data(trans_id=2, type_id=type_id)
    if df_rent.empty:
        return {}, 0
    rent_avg_district = df_rent.groupby('loc_id')['price_per_sqm'].mean().to_dict()
    rent_avg_city = df_rent['price_per_sqm'].mean()
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

st.sidebar.header("🎯 System Controls")

transaction_type = st.sidebar.selectbox(
    "Market Mode",
    options=[("Sale (Investment)", 1), ("Rent (Yield)", 2)],
    format_func=lambda x: x[0]
)
selected_trans_id = transaction_type[1]
label = "Sale" if selected_trans_id == 1 else "Rent"

prop_type_label = st.sidebar.selectbox(
    "Property Type",
    options=list(PROPERTY_TYPES.keys())
)
selected_type_id = PROPERTY_TYPES[prop_type_label]

st.sidebar.markdown("---")
st.sidebar.header("🔍 Quick Filters")

with st.spinner(f'Fetching live {label} data for {prop_type_label}...'):
    df = load_data(selected_trans_id, selected_type_id)

if not df.empty:
    max_val = int(df['price_pln'].max())
    min_val = int(df['price_pln'].min())

    max_price = st.sidebar.slider(
        "Max Budget (PLN)",
        min_value=min_val, max_value=max_val, value=max_val, step=5000 if selected_trans_id == 2 else 50000
    )

    districts = st.sidebar.multiselect(
        "Select Districts",
        options=sorted(df['district'].dropna().unique()),
        default=[]
    )

    filtered_df = df[df['price_pln'] <= max_price].copy()
    if districts:
        filtered_df = filtered_df[filtered_df['district'].isin(districts)]

    filtered_df = filtered_df.sort_values(by='price_per_sqm', ascending=True)

    st.title(f"🏢 Warsaw AI PropTech Radar")
    st.markdown(f"Real-time market intelligence for **{prop_type_label}** ({label}).")

    col1, col2, col3, col4 = st.columns(4)

    avg_price_total = filtered_df['price_pln'].mean()
    avg_price_sqm = filtered_df['price_per_sqm'].mean()

    display_avg_total = f"{avg_price_total:,.0f} PLN" if pd.notna(avg_price_total) else "N/A"
    display_avg_sqm = f"{avg_price_sqm:,.0f} PLN" if pd.notna(avg_price_sqm) else "N/A"

    col1.metric("Live Listings", f"{len(filtered_df)}")
    col2.metric(f"Avg Total Price", display_avg_total)
    col3.metric(f"Avg Price / m²", display_avg_sqm)
    col4.metric("Market Status", "Active 🟢")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📊 Market Overview", "🧠 ROI & Amortization Map", "🚨 Price Drop Radar"])

    with tab1:
        st.subheader("📊 Market Overview")
        c1, c2 = st.columns(2)
        with c1:
            st.bar_chart(filtered_df['district'].value_counts())
        with c2:
            chart_data = filtered_df.groupby('district')['price_per_sqm'].mean().dropna().sort_values()
            if not chart_data.empty:
                st.area_chart(chart_data)
            else:
                st.info("No price/m² data available for charts.")

        st.subheader(f"📋 Current {label} Listings")
        display_df = filtered_df[['district', 'price_pln', 'sqm', 'rooms', 'price_per_sqm', 'url_link_html']].copy()
        display_df.columns = ['District', 'Price (PLN)', 'm²', 'Rooms', 'Price/m²', 'Otodom Link']
        st.write(display_df.to_html(escape=False, index=False, classes='stTable'), unsafe_allow_html=True)

    with tab2:
        st.subheader("🧠 ROI & Investment Analysis")

        if selected_trans_id == 1:
            st.markdown("Calculates **Gross Yield (ROI)** and **Amortization Period (Years)** for the selected properties based on real-time rental averages in the same district.")

            with st.spinner("Calculating ROI based on live rent averages..."):
                rent_averages, city_avg_rent = load_rent_averages(selected_type_id)
                roi_df = filtered_df.dropna(subset=['sqm', 'loc_id']).copy()

                if pd.isna(city_avg_rent) or city_avg_rent <= 0:
                    fallback_rates = {1: 85.0, 2: 100.0, 3: 2.0, 4: 80.0, 5: 35.0, 6: 25.0}
                    city_avg_rent = fallback_rates.get(selected_type_id, 50.0)
                    st.warning(f"⚠️ Live rental data is missing from the database. Using an estimated fallback average ({city_avg_rent} PLN/m²) to generate ROI projections.")

                if roi_df.empty:
                    st.info(f"ℹ️ **Data Note:** ROI calculation requires property size (m²). Listings in the **{prop_type_label}** category currently lack parsed m² data (common for lands/garages sold in ares/hectares), or this category is not suitable for standard yield metrics.")
                else:
                    roi_df['avg_rent_sqm'] = roi_df['loc_id'].map(rent_averages).fillna(city_avg_rent)

                    roi_df['est_monthly_rent'] = roi_df['sqm'] * roi_df['avg_rent_sqm']
                    roi_df['net_annual'] = (roi_df['est_monthly_rent'] * 12) * 0.8

                    roi_df = roi_df[roi_df['price_pln'] > 0]
                    roi_df = roi_df[roi_df['net_annual'] > 0]

                    if not roi_df.empty:
                        roi_df['roi_percent'] = (roi_df['net_annual'] / roi_df['price_pln']) * 100
                        roi_df['amortization_years'] = roi_df['price_pln'] / roi_df['net_annual']

                        c1, c2 = st.columns(2)
                        with c1:
                            st.write("**Average ROI (%) by District**")
                            roi_chart = roi_df.groupby('district')['roi_percent'].mean().sort_values(ascending=False)
                            st.bar_chart(roi_chart, color="#4CAF50")
                        with c2:
                            st.write("**Average Amortization (Years) by District**")
                            amort_chart = roi_df.groupby('district')['amortization_years'].mean().sort_values()
                            st.bar_chart(amort_chart, color="#FF9800")

                        st.subheader("🏆 Top ROI Opportunities")
                        roi_df = roi_df.sort_values(by='roi_percent', ascending=False)

                        display_roi = roi_df[['district', 'price_pln', 'est_monthly_rent', 'roi_percent', 'amortization_years', 'url_link_html']].copy()
                        display_roi.columns = ['District', 'Sale Price (PLN)', 'Est. Rent (PLN/mo)', 'ROI (%)', 'Amortize (Yrs)', 'Link']

                        display_roi['Sale Price (PLN)'] = display_roi['Sale Price (PLN)'].apply(lambda x: f"{x:,.0f} PLN")
                        display_roi['Est. Rent (PLN/mo)'] = display_roi['Est. Rent (PLN/mo)'].apply(lambda x: f"{x:,.0f} PLN")
                        display_roi['ROI (%)'] = display_roi['ROI (%)'].apply(lambda x: f"<strong style='color: #4CAF50;'>{x:.1f}%</strong>")
                        display_roi['Amortize (Yrs)'] = display_roi['Amortize (Yrs)'].apply(lambda x: f"<strong>{x:.1f}</strong>")

                        st.write(display_roi.head(50).to_html(escape=False, index=False, classes='stTable'), unsafe_allow_html=True)
                    else:
                        st.info("Cannot calculate ROI metrics: Prices or estimated yields are mathematically invalid for the current selection.")
        else:
            st.info("ROI and Amortization metrics are only available for the 'Sale (Investment)' market mode. Please switch modes from the sidebar.")

    with tab3:
        st.subheader("📉 Largest Price Drops")
        st.markdown("Listings where the seller recently reduced the asking price.")

        with st.spinner("Analyzing price drop history..."):
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
                    display_radar = radar_df[['district', 'Old Price', 'Current Price', 'Discount (PLN)', 'Discount (%)', 'price_per_sqm', 'url_link_html']].copy()
                    display_radar.columns = ['District', 'Old Price', 'Current Price', 'Discount (PLN)', 'Discount %', 'Price/m²', 'Link']

                    display_radar['Old Price'] = display_radar['Old Price'].apply(lambda x: f"<span style='text-decoration: line-through; color: gray;'>{x:,.0f} PLN</span>")
                    display_radar['Current Price'] = display_radar['Current Price'].apply(lambda x: f"<strong style='color: #4CAF50;'>{x:,.0f} PLN</strong>")
                    display_radar['Discount (PLN)'] = display_radar['Discount (PLN)'].apply(lambda x: f"-{x:,.0f} PLN")
                    display_radar['Discount %'] = display_radar['Discount %'].apply(lambda x: f"<strong>-{x:.1f}%</strong>")

                    display_radar['Price/m²'] = display_radar['Price/m²'].apply(lambda x: f"{x:,.0f} PLN" if pd.notna(x) else "N/A")

                    st.write(display_radar.to_html(escape=False, index=False, classes='stTable'), unsafe_allow_html=True)
                else:
                    st.info("No recent price drops found in the current selection. Sellers are holding firm!")
            else:
                st.info("No price drop history available yet, or bot is still gathering initial data.")

else:
    st.info(f"There are currently no active {label.lower()} listings for {prop_type_label} in the system.")