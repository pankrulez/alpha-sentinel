import psycopg2
import pandas as pd

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "alpha_password",
    "host": "localhost",
    "port": "5432"
}

conn = psycopg2.connect(**DB_CONFIG)

print("--- 💰 LATEST PRICES ---")
print(pd.read_sql("SELECT * FROM crypto_prices ORDER BY time DESC LIMIT 3;", conn))

print("\n--- 📰 LATEST NEWS ---")
print(pd.read_sql("SELECT * FROM crypto_sentiment ORDER BY time DESC LIMIT 3;", conn))

conn.close()