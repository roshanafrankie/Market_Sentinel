# 🚀 Market Sentinel: AI Powered Financial Intelligence

Market Sentinel is a professional grade financial dashboard that bridges the gap between raw market data and actionable insights. It monitors price movements and utilizes AI to read and score the global news sentiment for a customized watchlist of companies.

## 🌟 Key Features

- **AI Sentiment Analysis:** Automatically scrapes financial news and uses NLP to determine if the market mood is **Bullish** (Positive), **Bearish** (Negative), or **Neutral**.
- **Live Market Dashboard:** A high performance Streamlit interface providing real time sector composition and global sentiment trends.
- **Deep-Dive Intelligence:** Zoom into specific stocks to view 10-day price trends and a **Visual Sentiment Gauge** an instant "speedometer" for market mood.
- **Automated Data Pipeline:** A robust backend that manages a MySQL database, syncing stock prices via financial APIs and archiving news scores.

## 📊 How It Works

1. **Scrape:** The pipeline fetches the latest headlines and stock prices.
2. **Analyze:** AI processes headlines to generate a sentiment score between -1 (Panic) and +1 (Euphoria).
3. **Visualize:** Data is pushed to the dashboard where complex sentiment clusters are transformed into simple, color-coded signals.

## 🛠️ Tech Stack

- **Frontend:** Streamlit, Plotly
- **Backend:** Python
- **Database:** MySQL
- **APIs:** Yahoo Finance (via yfinance)
- **Environment:** Dotenv for secure credential management

## 🚀 Getting Started

1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Set up your `.env` file with your MySQL credentials.
4. Run the scraper: `python main.py`.
5. Launch the dashboard: `streamlit run dashboard.py`.

---
*Developed for smarter, data-driven investing.*
