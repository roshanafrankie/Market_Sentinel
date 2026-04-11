import os
import datetime as dt
from decimal import Decimal
import requests
import yfinance as yf
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd

# 1. INITIAL CONFIGURATION
# Force Python to reload the .env file and overwrite any "localhost" ghosts in memory
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

analyzer = SentimentIntensityAnalyzer()

# Verify NewsData Key
NEWSDATA_API_KEY = os.getenv("NEWSDATA_KEY")

# Load your local watchlist
try:
    companies_df = pd.read_csv('companies.csv')
    WATCHLIST = companies_df['ticker'].tolist()
except Exception as e:
    print(f"❌ Error loading companies.csv: {e}")
    WATCHLIST = []

def get_mysql_connection():
    """Fetches Aiven credentials directly from the environment and connects."""
    host = os.getenv("MYSQL_HOST")
    port = os.getenv("MYSQL_PORT")
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    db = os.getenv("MYSQL_DB")

    try:
        # This will help us debug if it's still trying to hit localhost
        if host == "localhost" or host is None:
            print(f"⚠️ Warning: Still detecting host as '{host}'. Check your .env file!")
        
        return mysql.connector.connect(
            host=host,
            port=int(port) if port else 3306,
            user=user,
            password=password,
            database=db,
            connect_timeout=10,
            ssl_disabled=False # Required for Aiven Cloud
        )
    except mysql.connector.Error as err:
        print(f"❌ DB Error: {err}")
        return None

def setup_database():
    """Ensures the required tables exist in the Aiven cloud database."""
    conn = get_mysql_connection()
    if not conn: return
    cursor = conn.cursor()
    
    print("🛠️ Verifying database tables in Aiven...")
    
    # Create Stock Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stocks_daily (
        symbol VARCHAR(10),
        trade_date DATE,
        close_price DECIMAL(15, 2),
        PRIMARY KEY (symbol, trade_date)
    )
    """)
    
    # Create News Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source VARCHAR(100),
        title TEXT,
        description TEXT,
        url VARCHAR(500) UNIQUE,
        published_at DATETIME,
        sentiment_score DECIMAL(5, 4)
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database tables ready.")

# 2. PRICE FETCHING LOGIC
def fetch_daily_closes(tickers):
    results = []
    for symbol in tickers:
        print(f"🔍 Syncing Data for: {symbol}...")
        try:
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
        except Exception as e:
            print(f"   ⚠️ Could not fetch {symbol}: {e}")
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
        "q": "Stock Market OR Business News",
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
    # Final check before starting
    print(f"DEBUG: Using DB Host: {os.getenv('MYSQL_HOST')}")
    print("--- 🚀 STARTING MARKET SENTINEL PIPELINE ---")
    
    # Step 0: Setup Cloud DB
    setup_database()
    
    # Step 1: Stock Prices
    prices = fetch_daily_closes(WATCHLIST)
    save_daily_closes(prices)
    
    # Step 2: News Sentiment
    news = fetch_and_score_news(page_size=10)
    save_news(news)
    
    print("--- 🏁 PIPELINE COMPLETE ---")

if __name__ == "__main__":
    main()