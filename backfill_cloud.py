import ccxt
import psycopg2
from datetime import datetime

# --- CONFIGURATION ---
# 🔴 PASTE YOUR NEON CLOUD URL HERE 🔴
# It must start with 'postgresql://' and end with '?sslmode=require'
DB_URL = "postgresql://neondb_owner:npg_qzyhs8fxRr2K@ep-divine-pine-ad3z4af6-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

SYMBOL = 'BTC/USDT'
LIMIT = 1440 # 24 Hours

def backfill_cloud():
    print(f"🔌 Connecting to Cloud DB...")
    
    try:
        # 1. Connect to Cloud
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # 2. Fetch History from Binance
        print(f"⏳ Downloading last {LIMIT} minutes of data from Binance...")
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(SYMBOL, '1m', limit=LIMIT)
        
        if not ohlcv:
            print("❌ Failed to download data from Binance.")
            return

        print(f"✅ Downloaded {len(ohlcv)} candles. Inserting into Cloud DB...")

        # 3. Bulk Insert
        count = 0
        for candle in ohlcv:
            timestamp_ms = candle[0]
            price = candle[4]
            volume = candle[5]
            dt_object = datetime.fromtimestamp(timestamp_ms / 1000.0)
            
            try:
                # The SQL query to insert data
                cur.execute("""
                    INSERT INTO crypto_prices (time, symbol, price, volume)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (dt_object, SYMBOL, price, volume))
                count += 1
            except Exception as row_error:
                print(f"⚠️ Row Error: {row_error}")
                conn.rollback()
                continue

        conn.commit()
        cur.close()
        conn.close()
        
        print(f"🎉 Success! Backfilled {count} rows to the Cloud.")
        print("🚀 Go refresh your Streamlit Dashboard now!")

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("👉 Double check your DB_URL variable!")

if __name__ == "__main__":
    backfill_cloud()