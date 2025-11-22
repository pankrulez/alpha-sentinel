# ... (Keep existing imports)
import joblib
import pandas as pd
import pandas_ta as ta
from ta.momentum import RSIIndicator
from ta.trend import MACD
import warnings

warnings.filterwarnings('ignore')

# ... (Keep DB config)

# LOAD MODEL
print("🧠 Loading XGBoost model...")
model = joblib.load("model.bin")

def calculate_features(price_history):
    """Recalculates indicators for the latest data point."""
    df = pd.DataFrame(price_history, columns=['time', 'price'])
    
    # RSI
    df['rsi'] = RSIIndicator(close=df['price'], window=14).rsi()
    
    # MACD
    macd = MACD(close=df['price'])
    df['macd'] = macd.macd()
    df['macd_diff'] = macd.macd_diff()
    
    # Volatility & Returns
    df['volatility'] = df['price'].pct_change().rolling(window=20).std()
    df['return_5m'] = df['price'].pct_change(periods=5)
    df['return_15m'] = df['price'].pct_change(periods=15)
    
    # We only care about the LAST row (the current minute)
    return df.iloc[[-1]][['rsi', 'macd', 'macd_diff', 'volatility', 'return_5m', 'return_15m']]

def fetch_and_store():
    # ... (Keep existing init code)
    
    # Keep a small buffer of recent prices in memory for indicator calculation
    price_buffer = [] 

    while True:
        try:
            # ... (Keep existing fetch logic)
            
            # Add to buffer
            dt_object = pd.Timestamp.utcnow()
            # Ensure current_price is defined; try common names used by fetch logic, then fall back to last buffered price
            try:
                # If current_price already exists this will succeed; otherwise a NameError is raised and handled
                _ = current_price
            except NameError:
                current_price = None
                for candidate in ('price', 'last_price', 'price_fetched', 'latest_price', 'close'):
                    if candidate in locals():
                        current_price = locals()[candidate]
                        break
                if current_price is None:
                    if price_buffer:
                        current_price = price_buffer[-1]['price']
                    else:
                        print("No price available yet; skipping this iteration")
                        continue

            price_buffer.append({'time': dt_object, 'price': current_price})
            if len(price_buffer) > 50: # We need ~30-50 rows for RSI/MACD to warm up
                price_buffer.pop(0)
                
                # --- MAKE PREDICTION ---
                features = calculate_features(price_buffer)
                
                # Check if we have valid features (not NaN)
                if not features.isnull().values.any():
                    prediction = model.predict(features)[0]
                    probability = model.predict_proba(features)[0][1]
                    
                    signal = "🟢 BUY" if prediction == 1 else "🔴 HOLD"
                    print(f"🔮 Alpha Signal: {signal} (Conf: {probability:.2f})")
                    
                    # TODO: Insert this prediction into a 'predictions' table in DB
                else:
                    print("⏳ Gathering more history for indicators...")

            # ... (Keep existing insert logic)
        except Exception as e:
            # Log the exception and continue the loop to avoid leaving a bare try
            print(f"⚠️ Error in fetch loop: {e}")
            continue