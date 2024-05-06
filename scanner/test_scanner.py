import pandas as pd

tickers = pd.read_json("../symbols/crypto_symbols.json")["tickers"].tolist()
print(tickers)