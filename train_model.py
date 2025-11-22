import ccxt
import pandas as pd
import pandas_ta as ta  # Note: We use pandas_ta (pip install pandas_ta) or standard 'ta'
import numpy as np
import xgboost as xgb
import joblib
from sklearn.metrics import accuracy_score, classification_report
from ta.momentum import RSIIndicator
from ta.trend import MACD

# --- CONFIG ---
SYMBOL = 'BTC/USDT'
TIMEFRAME = '1m'
HISTORY_DAYS = 7  # Fetch last 7 days for training
TARGET_TIMEFRAME = 15 # Predict price 15 mins into the future

def fetch_historical_data():
    """Fetches last 7 days of 1m data from Binance for training."""
    print(f"⏳ Fetching {HISTORY_DAYS} days of historical data for {SYMBOL}...")
    exchange = ccxt.binance()
    
    # Calculate start time in milliseconds
    since = exchange.milliseconds() - (HISTORY_DAYS * 24 * 60 * 60 * 1000)
    
    all_ohlcv = []
    while since < exchange.milliseconds():
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 60000  # Move forward by 1 minute
        print(f"   ...Fetched {len(all_ohlcv)} candles so far")
        
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def add_technical_indicators(df):
    """Calculates RSI, MACD, and volatility features."""
    print("🛠️ Engineering features...")
    
    # 1. RSI (Relative Strength Index)
    rsi = RSIIndicator(close=df['close'], window=14)
    df['rsi'] = rsi.rsi()

    # 2. MACD (Moving Average Convergence Divergence)
    macd = MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_diff'] = macd.macd_diff()

    # 3. Rolling Volatility
    df['volatility'] = df['close'].pct_change().rolling(window=20).std()

    # 4. Lag Features (Price 5 mins ago, etc.) to give context
    df['return_5m'] = df['close'].pct_change(periods=5)
    df['return_15m'] = df['close'].pct_change(periods=15)

    # Drop NaNs created by indicators
    df.dropna(inplace=True)
    return df

def create_target(df):
    """
    Target: 1 if price increases by > 0.1% in the next 15 mins.
    Target: 0 otherwise.
    """
    print(f"🎯 Creating targets (Prediction horizon: {TARGET_TIMEFRAME} mins)...")
    
    # Calculate future return
    # shift(-15) looks 15 rows AHEAD
    df['future_close'] = df['close'].shift(-TARGET_TIMEFRAME)
    df['future_return'] = (df['future_close'] - df['close']) / df['close']
    
    # Define the signal (Threshold = 0.1% gain)
    df['target'] = (df['future_return'] > 0.001).astype(int)
    
    # Drop the last 15 rows (since they don't have a future yet)
    df.dropna(inplace=True)
    return df

def train_model():
    # 1. Get Data
    df = fetch_historical_data()
    
    # 2. Add Features
    df = add_technical_indicators(df)
    
    # 3. Create Target
    df = create_target(df)
    
    # 4. Split Data (Time-based split, NOT random shuffle)
    # We train on the past, test on the "future"
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    features = ['rsi', 'macd', 'macd_diff', 'volatility', 'return_5m', 'return_15m']
    X_train = train_df[features]
    y_train = train_df['target']
    X_test = test_df[features]
    y_test = test_df['target']
    
    print(f"🧠 Training XGBoost on {len(X_train)} rows...")
    
    # 5. Train XGBoost
    model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        objective='binary:logistic',
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # 6. Evaluate
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"\n📊 Model Accuracy: {acc:.2%}")
    print(classification_report(y_test, preds))
    
    # 7. Save
    joblib.dump(model, "model.bin")
    print("💾 Model saved to 'model.bin'")

if __name__ == "__main__":
    train_model()