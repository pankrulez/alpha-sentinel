import time
import psycopg2
import feedparser
from datetime import datetime
from transformers import pipeline
from time import mktime

# --- CONFIG ---
RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/"
POLL_INTERVAL = 300 

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "alpha_password",
    "host": "localhost",
    "port": "5432"
}

# --- LOAD MODEL ---
print("🧠 Loading FinBERT model...")
sentiment_pipe = pipeline("sentiment-analysis", model="ProsusAI/finbert")
print("✅ Model Loaded!")

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_and_analyze_news():
    print(f"📰 Checking RSS Feed: {RSS_URL}...")
    
    # 1. Parse the RSS Feed
    feed = feedparser.parse(RSS_URL)
    
    if not feed.entries:
        print("⚠️ No entries found in RSS feed.")
        return

    conn = get_db_connection()
    cur = conn.cursor()

    for entry in feed.entries:
        try:
            headline = entry.title
            # RSS times are struct_time, convert to datetime
            published_struct = entry.published_parsed
            dt_object = datetime.fromtimestamp(mktime(published_struct))

            # Filter: Only care about Bitcoin for this project
            if "bitcoin" not in headline.lower() and "btc" not in headline.lower() and "crypto" not in headline.lower():
                continue

            # Check Duplicates
            cur.execute(
                "SELECT 1 FROM crypto_sentiment WHERE headline = %s", 
                (headline,)
            )
            if cur.fetchone():
                continue 

            # AI Analysis
            # Truncate headline to 512 tokens max for BERT safety
            result = sentiment_pipe(headline[:512])[0]
            label = result['label']
            score = result['score']
            
            # Store Result
            cur.execute("""
                INSERT INTO crypto_sentiment (time, headline, sentiment_label, sentiment_score)
                VALUES (%s, %s, %s, %s)
            """, (dt_object, headline, label, score))
            
            print(f"💾 Analyzed: '{headline[:30]}...' -> {label} ({round(score, 2)})")

        except Exception as e:
            print(f"⚠️ Error processing entry: {e}")

    conn.commit()
    cur.close()
    conn.close()

def main():
    while True:
        try:
            fetch_and_analyze_news()
        except Exception as e:
            print(f"❌ Main Loop Error: {e}")
        
        print(f"😴 Sleeping for {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()