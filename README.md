# 🏠 Warsaw AI PropTech Radar

### Intelligent Real Estate Analysis & Investment Platform

---

## 🌟 Project Vision

The Warsaw real estate market is highly fragmented and data-heavy, making it difficult for investors to identify true opportunities.

**Warsaw AI PropTech Radar** solves this by combining automated data pipelines with AI-driven analysis to transform raw listings into **actionable investment insights in real-time**.

---

## 📊 Impact

* Analyzes **hundreds of property listings in seconds**
* Detects **undervalued properties (20–30% below market average)**
* Provides **real-time ROI and amortization insights**
* Enables **data-driven investment decisions**

---

## 🛠️ Tech Stack

**Backend & Data Processing**

* Python 3.x
* Pandas, NumPy

**Database**

* PostgreSQL (via Supabase)
* Real-time data querying & relational modeling

**AI Integration**

* Gemini API (LLM-based text analysis & summarization)

**Frontend & Visualization**

* Streamlit
* Plotly (interactive charts & heatmaps)

**Cloud (Planned)**

* Microsoft Azure (scalable deployment architecture)

---

## ⚡ Key Features

* 📡 **Automated Data Pipeline (ETL)**
  Collects, cleans, and processes real estate data from multiple sources

* 🧠 **AI-Powered Listing Analysis**
  Uses LLM to extract insights such as:

  * seller motivation
  * urgency signals
  * renovation needs

* 📉 **Price Anomaly Detection**
  Identifies properties priced significantly below district averages

* 📊 **ROI & Investment Metrics**

  * Gross yield calculation
  * Amortization period
  * District-level analytics

* 🗺️ **Interactive Market Heatmap**
  Visualizes price distribution and listing density across Warsaw

* 🚨 **Price Drop Radar**
  Tracks historical price changes and highlights discounted listings

---

## 🏗️ Architecture Overview

```
Data Sources
     ↓
ETL Pipeline (Python)
     ↓
Supabase (PostgreSQL)
     ↓
AI Processing (Gemini API)
     ↓
Streamlit Dashboard
     ↓
End User (Investor)
```

Designed with scalability in mind for future cloud deployment on Azure.

---

## 🔐 Environment Setup

Create a `.env` file in the root directory:

```env
SUPABASE_URL=your_url_here
SUPABASE_KEY=your_key_here
TELEGRAM_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id
GEMINI_API_KEY=your_api_key
STRIPE_LINK=your_link
```

⚠️ **Important:** Never share your `.env` file publicly.
Use a `.env.example` file for reference instead.

---

## 🚀 Getting Started

```bash
# Clone the repository
git clone https://github.com/Fatih-Ulucan/WarsawPropTech.git

# Navigate into project
cd warsaw-ai-proptech

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run main.py
```

---

## 🏗️ Future Roadmap

* [x] Backend architecture & database schema
* [x] AI integration for listing analysis
* [ ] Azure cloud deployment
* [ ] Real-time Telegram alerts for undervalued deals
* [ ] Advanced anomaly detection (ML-based scoring)

---

## 💡 Key Engineering Highlights

* Built a **full-stack data pipeline** for real estate analytics
* Implemented **LLM-based natural language processing** for property descriptions
* Designed **real-time ROI calculation engine**
* Applied **data-driven anomaly detection for investment opportunities**

---

## 📌 About the Project

This project was developed as a **PropTech + AI solution** to simulate a real-world investment analytics platform.

It demonstrates:

* Data engineering skills
* Backend architecture design
* AI/LLM integration
* Data visualization & product thinking

---

## 👨‍💻 Author

**Fatih Ulucan**
Warsaw-based developer focused on **AI, data systems, and real-world applications**

---

## ⭐ Final Note

This is not just a dashboard —
it is a **data-driven decision engine for real estate investment**.
