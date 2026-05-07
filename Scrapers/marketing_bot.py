import os
import pandas as pd
from supabase import create_client, Client
import requests
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ ERROR: GROQ_API_KEY is missing!")
    exit()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_daily_report():
    print("📊 Fetching ALL active listings from Supabase (Bypassing 1000 limit)...")

    all_data = []
    start = 0
    step = 1000

    try:
        while True:
            response = supabase.table('listings') \
                .select('*') \
                .eq('is_active', True) \
                .gt('price_per_sqm', 0) \
                .range(start, start + step - 1) \
                .execute()

            data = response.data
            if not data:
                break

            all_data.extend(data)
            print(f"🔄 Sweeping database... {len(all_data)} records fetched so far.")

            if len(data) < step:
                break

            start += step

        if not all_data:
            print("❌ No valid listings with price_per_sqm found.")
            return

        df = pd.DataFrame(all_data)

        if 'trans_id' in df.columns:
            df = df[df['trans_id'] == 1]

        print(f"✅ FINAL: Successfully fetched ALL {len(df)} VALID sale listings!")

        df['price_per_sqm'] = pd.to_numeric(df['price_per_sqm'], errors='coerce')
        valid_df = df.dropna(subset=['price_per_sqm'])

        total_valid = len(valid_df)

        if total_valid == 0:
            print("❌ Error: Could not parse numeric data.")
            return

        avg_price_sqm = valid_df['price_per_sqm'].mean()

        print(f"🧠 Groq AI is generating report using {total_valid} verified listings...")
        print(f"💡 TRUE MARKET AVERAGE: {avg_price_sqm:.2f} PLN")

        prompt = f"""
        You are a top-tier Real Estate Data Scientist in Poland.
        Market Analysis for Warsaw (Today):
        - Analyzed the COMPLETE MARKET of {total_valid} verified active listings.
        - The absolute true average price per square meter is: {avg_price_sqm:.0f} PLN.
        
        Task: Write an elite, professional, and viral LinkedIn/Twitter post. 
        Discuss the market trends in Warsaw. Emphasize that this data is based on a massive dataset of tens of thousands of listings.
        Write the response in BOTH Polish and English. Use relevant emojis.
        
        Include this link exactly at the very end:
        "🚀 AI-Powered PropTech radar: https://warsaw-proptech.streamlit.app"
        """

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}]
        }

        api_response = requests.post(url, headers=headers, json=payload)
        api_response.raise_for_status()

        print("\n" + "="*60)
        print("🚀 DAILY SOCIAL MEDIA POST (BASED ON ENTIRE MARKET):")
        print("="*60 + "\n")
        print(api_response.json()['choices'][0]['message']['content'])

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    generate_daily_report()