import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import plotly.graph_objects as go
import os
import warnings
from dotenv import load_dotenv

# --- 1. INITIAL SETUP ---
warnings.filterwarnings('ignore')
load_dotenv(override=True)

# Define sentiment color function globally so both views can use it
def apply_sentiment_style(val):
    try:
        score = float(val)
        color = "#16a34a" if score > 0.05 else "#dc2626" if score < -0.05 else "#4b5563"
        return f'color: {color}; font-weight: bold'
    except:
        return ''

@st.cache_data
def load_watchlist():
    try:
        df = pd.read_csv('companies.csv')
        return df
    except Exception as e:
        st.error(f"Missing companies.csv: {e}")
        return pd.DataFrame()

def get_data(query):
    """Securely connects to Aiven Cloud MySQL."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT")) if os.getenv("MYSQL_PORT") else 20914,
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DB"),
            ssl_disabled=False 
        )
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return pd.DataFrame()

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="Market Sentinel", layout="wide", page_icon="📈")

# --- 3. PREMIUM CSS (Privacy Shield + Header/Switch Kept) ---
st.markdown("""
    <style>
    /* 1. HIDE FOOTER & BRANDING BADGE */
    footer {visibility: hidden !important; height: 0px !important;}
    [data-testid="stFooter"] {display: none !important;}
    div[class^="viewerBadge"] {display: none !important;}
    
    /* 2. HIDE GITHUB & FORK LINKS ONLY (Keeps Header for Switch Mode) */
    [data-testid="stHeaderActionElements"] {display: none !important;}
    header a[href*="github"] {display: none !important;}
    .stDeployButton {display:none !important;}

    /* 3. CLEAN UP THE HAMBURGER MENU */
    ul[data-testid="main-menu-list"] li:nth-last-child(-n+3) {display: none !important;}
    div[data-testid="stConnectionStatus"] {display: none !important;}
    [data-testid="stSidebarNav"] + div {display: none !important;}

    /* 4. KEEP HEADER & MENU VISIBLE FOR THEME SWITCHING */
    header {visibility: visible !important;}
    #MainMenu {visibility: visible !important;}

    /* 5. THEME STYLES */
    .stApp { background-color: transparent; }
    [data-testid="stSidebar"] { background-color: #111b21 !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stMetricValue"] { font-size: 30px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. SIDEBAR NAVIGATION ---
df_watchlist = load_watchlist()

with st.sidebar:
    col_l, col_r = st.columns([1, 4])
    with col_l:
        if os.path.exists("logo.png"): 
            st.image("logo.png", width=45)
        else:
            st.write("📈")
    with col_r:
        st.markdown("<h2 style='margin-top:5px;'>Market Sentinel</h2>", unsafe_allow_html=True)
    
    st.caption("AI Powered Market Intelligence")
    st.divider()

    if not df_watchlist.empty:
        all_sectors = ["All Sectors"] + sorted(df_watchlist['sector'].unique().tolist())
        selected_sector = st.selectbox("Sector Focus", all_sectors)
        
        filtered_df = df_watchlist if selected_sector == "All Sectors" else df_watchlist[df_watchlist['sector'] == selected_sector]
        
        ticker_display = [f"{row['ticker']} - {row['name']}" for _, row in filtered_df.iterrows()]
        options = ["Global Overview"] + ticker_display
        selected_option = st.selectbox("Navigation", options)
        selected_view = "Global Overview" if selected_option == "Global Overview" else selected_option.split(" - ")[0]
    else:
        selected_view = "Global Overview"

# --- 5. MAIN CONTENT ---
if selected_view == "Global Overview":
    st.title("🌍 Global Market Intelligence")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.subheader("📊 Sector Composition")
            if not df_watchlist.empty:
                fig_pie = px.pie(df_watchlist, names='sector', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, width='stretch')
    with c2:
        with st.container(border=True):
            st.subheader("📈 Market Sentiment")
            news_sample = get_data("SELECT sentiment_score FROM news LIMIT 100")
            if not news_sample.empty:
                fig_glob_sent = px.histogram(news_sample, x="sentiment_score", nbins=15, color_discrete_sequence=['#4F46E5'])
                st.plotly_chart(fig_glob_sent, width='stretch')
            else:
                st.info("Waiting for sentiment data...")

    st.divider()
    with st.container(border=True):
        st.subheader("📰 Market Headlines")
        all_news = get_data("SELECT title, sentiment_score, source FROM news ORDER BY published_at DESC LIMIT 20")
        if not all_news.empty:
            # APPLYING COLOR STYLE HERE
            st.dataframe(all_news.style.map(apply_sentiment_style, subset=['sentiment_score']), width='stretch', hide_index=True)
        else:
            st.info("No news articles found in the database.")

else:
    # --- DEEP DIVE ---
    stock_info = df_watchlist[df_watchlist['ticker'] == selected_view]
    if not stock_info.empty:
        stock_name = stock_info['name'].iloc[0]
        st.title(f"🔍 {stock_name} Intelligence")

        price_query = f"SELECT * FROM (SELECT trade_date, close_price FROM stocks_daily WHERE symbol = '{selected_view}' ORDER BY trade_date DESC LIMIT 10) AS sub ORDER BY trade_date ASC"
        price_data = get_data(price_query)
        
        if not price_data.empty:
            latest = price_data['close_price'].iloc[-1]
            delta = float(latest - price_data['close_price'].iloc[-2]) if len(price_data) > 1 else 0
            
            sent_query = f"SELECT sentiment_score FROM news WHERE title LIKE '%{selected_view}%' OR title LIKE '%{stock_name}%' LIMIT 20"
            sent_df = get_data(sent_query)
            avg_s = sent_df['sentiment_score'].mean() if not sent_df.empty else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Current Price", f"${latest:,.2f}", f"{delta:+.2f}")
            m2.metric("AI Sentiment", f"{avg_s:.2f}", "Bullish" if avg_s > 0.05 else "Bearish" if avg_s < -0.05 else "Neutral")
            m3.metric("10-Day Trend", f"{'Stable' if abs(delta) < 5 else 'Volatile'}")

            with st.container(border=True):
                fig_line = px.line(price_data, x='trade_date', y='close_price', markers=True, line_shape='spline', color_discrete_sequence=['#4F46E5'])
                st.plotly_chart(fig_line, width='stretch')

        st.divider()
        c1, c2 = st.columns([2, 1])
        ticker_news = get_data(f"SELECT title, sentiment_score, source FROM news WHERE title LIKE '%{selected_view}%' OR title LIKE '%{stock_name}%' ORDER BY published_at DESC LIMIT 15")

        with c1:
            with st.container(border=True):
                st.subheader(f"📰 {selected_view} Headlines")
                if not ticker_news.empty:
                    # APPLYING COLOR STYLE HERE TOO
                    st.dataframe(ticker_news.style.map(apply_sentiment_style, subset=['sentiment_score']), width='stretch', hide_index=True)
                else:
                    st.info("No specific news found for this ticker.")

        with c2:
            with st.container(border=True):
                st.subheader("📊 Sentiment Gauge")
                if not ticker_news.empty:
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = avg_s,
                        gauge = {
                            'axis': {'range': [-1, 1]},
                            'bar': {'color': "#1e293b"},
                            'steps': [
                                {'range': [-1, -0.05], 'color': "#ef4444"}, 
                                {'range': [-0.05, 0.05], 'color': "#facc15"}, 
                                {'range': [0.05, 1], 'color': "#22c55e"} 
                            ]
                        }
                    ))
                    fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig_gauge, width='stretch')