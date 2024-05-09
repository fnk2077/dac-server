import pandas as pd
from fastapi.responses import JSONResponse
import yfinance as yf
import ta


def crypto_scanner(time_frame, rsi_period,rsi_more_than ,rsi_theshole):
    print(time_frame, rsi_period, rsi_more_than, rsi_theshole)
    tickers = pd.read_json("symbols/crypto_symbols.json")["tickers"].tolist()
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

    if time_frame == "1d":
        result = result.rename(columns={'Date': 'date', "Symbol": "symbol"})
        result = result[result["date"] == str(pd.Timestamp.now().date())]
    elif time_frame == "1h":
        result = result.rename(columns={'Datetime': 'date', "Symbol": "symbol"})
        result = result[result["date"].apply(lambda x: x.date()) == pd.Timestamp.now().date()]
    result = result[["date", "symbol", "open", "close", "percentChange", "volumeChange", "rsi", "volumeUSD"]]
    result["date"] = result["date"].dt.strftime('%Y-%m-%d %H:%M')

    result["open"] = result["open"].apply(lambda x: f"{x:.2f}")
    result["close"] = result["close"].apply(lambda x: f"{x:.2f}")
    result["percentChange"] = result["percentChange"].apply(lambda x: f"{x:.2f}")
    result["volumeChange"] = result["volumeChange"].apply(lambda x: f"{x:.2f}")
    result["rsi"] = result["rsi"].apply(lambda x: f"{x:.2f}")
    result["symbol"] = result["symbol"].str.replace("-", "")

    if rsi_more_than:
        result = result[result["rsi"].astype(float) > rsi_theshole]
    else:
        result = result[result["rsi"].astype(float) < rsi_theshole]
    result = result.groupby('symbol').apply(lambda x: x.sort_values(by='date', ascending=False).head(1)).reset_index(drop=True)

    return JSONResponse(content=result.to_dict(orient="records"))
