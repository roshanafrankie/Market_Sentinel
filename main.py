import os
import datetime as dt
from decimal import Decimal
import requests
import yfinance as yf
import mysql.connector
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd

# 1. INITIAL CONFIGURATION
load_dotenv()
analyzer = SentimentIntensityAnalyzer()

# Global Config - Shared across all functions
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""), 
    "database": os.getenv("MYSQL_DB", "cse_data"),
}

NEWSDATA_API_KEY = os.getenv("NEWSDATA_KEY")

companies_df = pd.read_csv('companies.csv')
WATCHLIST = companies_df['ticker'].tolist()

def get_mysql_connection():
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except mysql.connector.Error as err:
        print(f"❌ DB Error: {err}")
        return None

# 2. RESILIENT PRICE FETCHING
def fetch_daily_closes(tickers):
    results = []
    for symbol in tickers:
        print(f"🔍 Syncing Data for: {symbol}...")
        ticker = yf.Ticker(symbol)

        hist = ticker.history(period="1mo")
        
        if not hist.empty:
            last_few_days = hist.tail(5) 
            
            for date, row in last_few_days.iterrows():
                results.append({
                    "symbol": symbol,
                    "trade_date": date.date(),
                    "close_price": Decimal(str(row["Close"]))
                })
            print(f"   ✅ Data synced for {symbol}")
    return results

def save_daily_closes(rows):
    if not rows: return
    conn = get_mysql_connection()
    if not conn: return
    cursor = conn.cursor()
    sql = """
    INSERT INTO stocks_daily (symbol, trade_date, close_price)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE close_price = VALUES(close_price)
    """
    data = [(r["symbol"], r["trade_date"], r["close_price"]) for r in rows]
    cursor.executemany(sql, data)
    conn.commit()
    cursor.close()
    conn.close()

# 3. NEWS & AI SENTIMENT ANALYSIS
def fetch_and_score_news(page_size=10):
    if not NEWSDATA_API_KEY:
        print("❌ NewsData API Key missing!")
        return []

    url = "https://newsdata.io/api/1/latest"
    params = {
        "apikey": NEWSDATA_API_KEY,
        "q": "Apple AND (Stock OR Market OR AAPL)",
        "language": "en",
        "category": "business",
        "size": page_size
    }
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"⚠️ NewsData Error {resp.status_code}: {resp.text}")
            return []
            
        data = resp.json()
        articles = []
        for item in data.get("results", []):
            title = item.get("title", "")
            desc = item.get("description", "") or ""
            
            # AI Logic: Scoring the "vibe" of the news
            score = analyzer.polarity_scores(f"{title}. {desc}")['compound']
            
            articles.append({
                "source": item.get("source_id"),
                "title": title,
                "description": desc,
                "url": item.get("link"),
                "published_at": item.get("pubDate"),
                "sentiment": score
            })
        return articles
    except Exception as e:
        print(f"⚠️ News Pipeline Failed: {e}")
        return []

def save_news(articles):
    if not articles: return
    conn = get_mysql_connection()
    if not conn: return
    cursor = conn.cursor()
    sql = """
    INSERT IGNORE INTO news (source, title, description, url, published_at, sentiment_score)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    data = [(a["source"], a["title"], a["description"], a["url"], a["published_at"], a["sentiment"]) for a in articles]
    cursor.executemany(sql, data)
    conn.commit()
    cursor.close()
    conn.close()

# 4. MAIN ORCHESTRATOR
def main():
    print("--- 🚀 STARTING STOCK PIPELINE ---")
    
    # Step 1: Stock Prices
    prices = fetch_daily_closes(WATCHLIST)
    save_daily_closes(prices)
    print(f"✅ Prices updated: {len(prices)} companies.")

    # Step 2: News Sentiment
    news = fetch_and_score_news(page_size=10)
    save_news(news)
    print(f"✅ News analyzed: {len(news)} articles scored with AI.")
    
    print("--- 🏁 PIPELINE COMPLETE ---")

if __name__ == "__main__":
    main()