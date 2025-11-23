import psycopg2

# 🔴 PASTE YOUR NEON CLOUD URL HERE 🔴
DB_URL = "postgresql://neondb_owner:npg_qzyhs8fxRr2K@ep-divine-pine-ad3z4af6-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require" 

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM crypto_prices;")
    count = cur.fetchone()[0]
    print(f"✅ Total Rows in Cloud DB: {count}")
    conn.close()
except Exception as e:
    print(f"❌ Connection Error: {e}")