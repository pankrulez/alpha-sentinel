import psycopg2

# Connection Config
# Host is 'localhost' because we mapped the ports in docker-compose
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "alpha_password",
    "host": "localhost",
    "port": "5432"
}

def test_connection():
    try:
        # 1. Connect
        print("🔌 Attempting to connect to TimescaleDB...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✅ Connected successfully!")

        # 2. Run a SQL query
        print("📊 Checking database version...")
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        print(f"ℹ️ Database Version: {db_version[0]}")

        # 3. Create a Hypertable (Timescale specific feature)
        # We create a standard table first
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_prices (
                time TIMESTAMPTZ NOT NULL,
                symbol TEXT NOT NULL,
                price DOUBLE PRECISION NULL,
                volume DOUBLE PRECISION NULL
            );
        """)
        
        # Then turn it into a hypertable (optimized for time-series)
        # We use a try-except in case it's already created
        try:
            cur.execute("SELECT create_hypertable('crypto_prices', 'time');")
            print("✅ Hypertable 'crypto_prices' created!")
        except psycopg2.errors.PlPgsqlError: 
             # Ignore error if it already exists
            conn.rollback()
            print("ℹ️ Hypertable already exists.")
        
        conn.commit()
        cur.close()
        conn.close()
        print("🏁 Test Complete. Database is ready for data.")

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_connection()