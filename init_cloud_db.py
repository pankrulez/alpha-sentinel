import psycopg2
import ccxt
from datetime import datetime


# Paste your NEON CLOUD URL here
DB_URL = "postgresql://neondb_owner:npg_qzyhs8fxRr2K@ep-divine-pine-ad3z4af6-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require" 


# --- CONFIGURATION ---
# PASTE YOUR NEON CLOUD URL HERE (Start with postgresql://...)
# Ensure it has '?sslmode=require' at the end
# DB_URL = "postgresql://neondb_owner:npg_qzyhs8fxRr2K@ep-divine-pine-ad3z4af6-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require" 


SYMBOL = 'BTC/USDT'

def init_db():
    print(f"🔌 Connecting to Cloud DB: {DB_URL.split('@')[1]}...") # Hide password in print
    
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # 1. Create Price Table
        print("🔨 Creating table 'crypto_prices'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_prices (
                time TIMESTAMPTZ NOT NULL,
                symbol TEXT NOT NULL,
                price DOUBLE PRECISION NULL,
                volume DOUBLE PRECISION NULL
            );
        """)

        # 2. Create Sentiment Table
        print("🔨 Creating table 'crypto_sentiment'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_sentiment (
                time TIMESTAMPTZ NOT NULL,
                headline TEXT,
                sentiment_label TEXT,
                sentiment_score DOUBLE PRECISION
            );
        """)

        # 3. (Optional) Skip Hypertable creation if using Neon (It's not TimescaleDB)
        # If you ARE using Timescale Cloud, uncomment the lines below.
        # try:
        #     cur.execute("SELECT create_hypertable('crypto_prices', 'time');")
        # except:
        #     pass

        conn.commit()
        print("✅ Tables created successfully!")

        # 4. Backfill Data (So dashboard isn't empty)
        print("⏳ Backfilling last 24 hours of price data...")
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(SYMBOL, '1m', limit=1440)
        
        count = 0
        for candle in ohlcv:
            timestamp_ms = candle[0]
            price = candle[4]
            volume = candle[5]
            dt_object = datetime.fromtimestamp(timestamp_ms / 1000.0)
            
            cur.execute("""
                INSERT INTO crypto_prices (time, symbol, price, volume)
                VALUES (%s, %s, %s, %s);
            """, (dt_object, SYMBOL, price, volume))
            count += 1
            
        conn.commit()
        print(f"🎉 Backfilled {count} rows of data!")
        
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    init_db()