import yfinance as yf
print("Downloading NVDA close history...")
try:
    df = yf.download("NVDA", period="5d", progress=False)
    print("NVDA Close series:")
    print(df['Close'])
    close_series = df['Close']['NVDA']
    if len(close_series) >= 2:
        current_price = float(close_series.iloc[-1])
        prev_price = float(close_series.iloc[-2])
        change_pct = float(((current_price - prev_price) / prev_price) * 100)
        print(f"NVDA Current Price: ${current_price:.2f}")
        print(f"NVDA Previous Price: ${prev_price:.2f}")
        print(f"NVDA Change Percent: {change_pct:.2f}%")
except Exception as e:
    print("Failed to download NVDA:", e)
