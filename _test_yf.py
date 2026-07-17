import yfinance as yf
import pandas as pd
print("yfinance", yf.__version__)
t = yf.Ticker("SPY")
df = t.history(period="max", interval="1mo")
print("shape", df.shape)
print("index range", df.index.min(), "->", df.index.max())
print(df.tail(3)[["Open","Close","Adj Close","Volume"]])
