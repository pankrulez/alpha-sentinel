import streamlit as st
import pandas as pd
import joblib
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from ta.momentum import RSIIndicator
from ta.trend import MACD

# --- CONFIG ---
# SQLAlchemy requires a connection URL instead of a dictionary
# Format: postgresql+psycopg2://user:password@host:port/dbname
# DB_URI = "postgresql+psycopg2://postgres:alpha_password@localhost:5432/postgres"

# --- CONFIG ---
# Try to get URI from Streamlit Secrets (Cloud), otherwise fail gracefully
try:
    DB_URI = st.secrets["DB_URI"]
    source = "☁️ CLOUD DATABASE"
except FileNotFoundError:
    # Fallback for local testing if secrets.toml doesn't exist
    DB_URI = "postgresql+psycopg2://postgres:alpha_password@localhost:5432/postgres"
    source = "🏠 LOCAL DOCKER"
    
# ADD THIS LINE TO DEBUG:
st.toast(f"Connected to: {source}", icon="🔌")
print(f"DEBUG: Connecting to {source}") # This prints in your terminal

MODEL_PATH = "model.bin"

# --- PAGE SETUP ---
st.set_page_config(page_title="Alpha Sentinel", layout="wide", page_icon="🦅")
st.title("🦅 The Alpha Sentinel: Live Crypto Strategy")

# --- FUNCTIONS ---
@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)

def get_data():
    """Fetch last 24h of data from DB using SQLAlchemy"""
    # Create the engine
    engine = create_engine(DB_URI)
    
    # Establish connection
    with engine.connect() as conn:
        # Fetch Prices
        query_price = text("""
            SELECT time, price, volume 
            FROM crypto_prices 
            ORDER BY time DESC 
            LIMIT 1440;
        """)
        df_price = pd.read_sql(query_price, conn)
        
        # Fetch Sentiment
        query_sent = text("""
            SELECT time, headline, sentiment_label, sentiment_score 
            FROM crypto_sentiment 
            ORDER BY time DESC 
            LIMIT 5;
        """)
        df_sent = pd.read_sql(query_sent, conn)
    
    # Sort by time for calculations
    df_price = df_price.sort_values('time')
    return df_price, df_sent

def calculate_features(df):
    """Re-create features for the model"""
    df['rsi'] = RSIIndicator(close=df['price'], window=14).rsi()
    macd = MACD(close=df['price'])
    df['macd'] = macd.macd()
    df['macd_diff'] = macd.macd_diff()
    df['volatility'] = df['price'].pct_change().rolling(window=20).std()
    df['return_5m'] = df['price'].pct_change(periods=5)
    df['return_15m'] = df['price'].pct_change(periods=15)
    return df.iloc[[-1]] # Return only the latest row for prediction

# --- MAIN LOGIC ---

try:
    # 1. Load Data & Model
    model = load_model()
    df, df_news = get_data()
    
    if len(df) < 50:
        st.warning("⚠️ Not enough data yet! Let the ingest script run for a while.")
        st.stop()

    # 2. Make Prediction on Live Data
    latest_features = calculate_features(df.copy())
    features_for_pred = latest_features[['rsi', 'macd', 'macd_diff', 'volatility', 'return_5m', 'return_15m']]
    
    # Handle NaN values if indicators aren't ready
    if features_for_pred.isnull().values.any():
        st.warning("⏳ Indicators warming up... (Need more price history)")
        prediction = 0
        prob = 0.5
    else:
        prediction = model.predict(features_for_pred)[0]
        prob = model.predict_proba(features_for_pred)[0][1]

    # 3. UI Layout
    col1, col2, col3 = st.columns(3)

    current_price = df.iloc[-1]['price']
    price_change = current_price - df.iloc[-2]['price']

    with col1:
        st.metric("Bitcoin Price", f"${current_price:,.2f}", f"{price_change:.2f}")
    
    with col2:
        signal = "🟢 BUY" if prediction == 1 else "🔴 HOLD"
        st.metric("Model Signal (15m)", signal, f"Conf: {prob:.0%}")

    with col3:
        if not df_news.empty:
            latest_news_label = df_news.iloc[0]['sentiment_label']
            st.metric("Latest News Sentiment", latest_news_label.upper())
        else:
            st.metric("Latest News Sentiment", "NO NEWS")

    # 4. Charts
    st.subheader("Price Action")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['time'], y=df['price'], mode='lines', name='BTC Price'))
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 5. News Feed
    st.subheader("📰 Live Sentiment Feed")
    for i, row in df_news.iterrows():
        emoji = "🟢" if row['sentiment_label'] == 'positive' else "🔴" if row['sentiment_label'] == 'negative' else "⚪"
        st.markdown(f"{emoji} **{row['sentiment_label'].upper()}** ({row['sentiment_score']:.2f}) - *{row['headline']}*")
        st.caption(f"Published: {row['time']}")

except Exception as e:
    st.error(f"Dashboard Error: {e}")
    st.info("Make sure 'docker-compose' is running and 'model.bin' exists!")

# Auto-refresh logic (Experimental)
st.empty()