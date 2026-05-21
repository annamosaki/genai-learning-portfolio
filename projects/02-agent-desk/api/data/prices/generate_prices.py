"""Generate synthetic OHLCV price data for testing."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os


def generate_ohlcv_data(ticker: str, days: int = 60, start_price: float = 100.0) -> pd.DataFrame:
    """Generate synthetic OHLCV data with realistic patterns."""
    
    np.random.seed(hash(ticker) % 1000)  # Consistent data per ticker
    
    dates = pd.date_range(end=datetime.now().date(), periods=days, freq='D')
    
    # Generate returns with some autocorrelation and volatility clustering
    returns = []
    volatility = 0.02  # Base volatility
    
    for i in range(days):
        # Add some trend and mean reversion
        if i > 0:
            momentum = returns[-1] * 0.1  # Some momentum
            mean_reversion = -np.mean(returns[-5:]) * 0.05 if len(returns) >= 5 else 0
        else:
            momentum = mean_reversion = 0
        
        # Volatility clustering
        if i > 0 and abs(returns[-1]) > 0.03:
            volatility = min(volatility * 1.2, 0.05)
        else:
            volatility = max(volatility * 0.98, 0.01)
        
        daily_return = np.random.normal(momentum + mean_reversion, volatility)
        returns.append(daily_return)
    
    # Generate prices
    prices = [start_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Generate OHLCV
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        # Generate intraday range
        daily_volatility = abs(returns[i]) + np.random.uniform(0.005, 0.02)
        
        # High and Low around close
        high = close * (1 + daily_volatility * np.random.uniform(0.3, 1.0))
        low = close * (1 - daily_volatility * np.random.uniform(0.3, 1.0))
        
        # Open based on previous close with gap
        if i == 0:
            open_price = close * (1 + np.random.uniform(-0.01, 0.01))
        else:
            gap = np.random.uniform(-0.005, 0.005)
            open_price = prices[i-1] * (1 + gap)
        
        # Ensure OHLC consistency
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Volume with some correlation to volatility
        base_volume = 1000000
        volume_multiplier = 1 + daily_volatility * 5 + np.random.uniform(0.5, 2.0)
        volume = int(base_volume * volume_multiplier)
        
        data.append({
            'Date': date.strftime('%Y-%m-%d'),
            'Open': round(open_price, 2),
            'High': round(high, 2),
            'Low': round(low, 2),
            'Close': round(close, 2),
            'Volume': volume
        })
    
    return pd.DataFrame(data)


def main():
    """Generate price data for all tickers."""
    
    tickers = [
        ('NVDA', 450.0),
        ('AAPL', 180.0), 
        ('MSFT', 380.0)
    ]
    
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    
    for ticker, start_price in tickers:
        print(f"Generating data for {ticker}...")
        df = generate_ohlcv_data(ticker, days=60, start_price=start_price)
        
        filename = f"{ticker}.csv"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        df.to_csv(filepath, index=False)
        
        print(f"Generated {len(df)} days of data for {ticker}")
        print(f"Price range: ${df['Low'].min():.2f} - ${df['High'].max():.2f}")
        print(f"Saved to: {filepath}")
        print()


if __name__ == "__main__":
    main()