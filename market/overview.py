from fastapi.responses import JSONResponse
import pandas as pd
import ta
import yfinance as yf

def market_overview():
    tickers = ['BTC-USD', 'GC=F', '^SET.BK']
    time_frame = '1d' 
    rsi_period = 14
    start_dt = pd.Timestamp.now() - pd.DateOffset(months=3)
    end_dt = pd.Timestamp.now()

    dfs = []

    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start_dt, end=end_dt, interval=time_frame)
            df["Symbol"] = ticker
            df = df.rename(columns={'Open': 'open', 'Low': 'low', 'High': 'high', 'Close': 'close', 'Volume': 'volume'})
            df = df[df['volume'] != 0]

            df['percentChange'] = df['close'].pct_change(periods=7) * 100
            df['volumeChange'] = df['volume'].pct_change(periods=7) * 100

            df['%K'] = ta.momentum.stoch(df['high'], df['low'], df['close'])
            df['%D'] = ta.momentum.stoch_signal(df['high'], df['low'], df['close'])

            df['rsi'] = ta.momentum.rsi(df['close'], window=rsi_period)

            dfs.append(df)
        except Exception as e:
            print(f"Failed to fetch data for {ticker}: {e}")

    result = pd.concat(dfs).reset_index()
    result['volumeUSD'] = result['volume'].apply(lambda x: f"${x:,.2f}")
    result = result.rename(columns={'Date': 'date', "Symbol": "symbol"})
    result = result[result["date"].dt.date == (pd.Timestamp.now() - pd.Timedelta(days=1)).date()]
    result = result[["date", "symbol", "open", "close", "percentChange", "volumeChange", "rsi", "volumeUSD"]]
    result["date"] = result["date"].dt.strftime('%Y-%m-%d %H:%M')

    result["open"] = result["open"].apply(lambda x: f"{x:.2f}")
    result["close"] = result["close"].apply(lambda x: f"{x:.2f}")
    result["percentChange"] = result["percentChange"].apply(lambda x: f"{x:.2f}")
    result["volumeChange"] = result["volumeChange"].apply(lambda x: f"{x:.2f}")
    result["rsi"] = result["rsi"].apply(lambda x: f"{x:.2f}")

    return JSONResponse(content=result.to_dict(orient="records"))
