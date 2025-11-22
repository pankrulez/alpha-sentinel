import psycopg2

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "alpha_password",
    "host": "localhost",
    "port": "5432"
}

def create_sentiment_table():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Create a dedicated table for news sentiment
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_sentiment (
                time TIMESTAMPTZ NOT NULL,
                headline TEXT,
                sentiment_label TEXT,
                sentiment_score DOUBLE PRECISION
            );
        """)
        
        # Make it a hypertable (TimescaleDB magic)
        try:
            cur.execute("SELECT create_hypertable('crypto_sentiment', 'time');")
            print("✅ Hypertable 'crypto_sentiment' created!")
        except psycopg2.errors.PlPgsqlError:
            print("ℹ️ Hypertable already exists.")
            
        conn.commit()
        cur.close()
        conn.close()
        print("🎉 Database ready for News!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_sentiment_table()