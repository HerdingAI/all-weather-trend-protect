import yfinance as yf
for tk in ["SPY","^GSPC","^TNX","GLD"]:
    try:
        df = yf.Ticker(tk).history(period="max", interval="1mo")
        print(tk, "cols=", list(df.columns), "shape", df.shape, "rng", df.index.min(), df.index.max())
    except Exception as e:
        print(tk, "ERR", e)
