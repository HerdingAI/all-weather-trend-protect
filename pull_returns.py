"""
Pull monthly returns across asset classes (and individual stocks grouped into
asset classes / sectors) as far back as Yahoo Finance provides.

Data source: Yahoo Finance via yfinance.  yfinance v1.5+ returns *auto-adjusted*
prices by default, so the 'Close' column is a total-return (split+dividend
adjusted) close for ETFs/stocks -- the right basis for monthly returns.

Outputs (in ./output):
  monthly_returns_by_ticker.csv     long panel: every ticker, monthly return, labels
  monthly_returns_by_asset_class.csv wide: asset-class equal-weighted monthly returns
  monthly_returns_by_sector.csv     wide: GICS sector equal-weighted monthly returns (stocks)
  monthly_prices.csv                wide: monthly adjusted close per ticker
  coverage_summary.csv              per-series coverage + stats (start,end,n,mean,std,min,max)
  universe.csv                      the ticker universe with metadata
  README.md                         methodology + coverage notes
"""
from __future__ import annotations
import os, sys, time, json
from datetime import datetime
import pandas as pd
import yfinance as yf

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# Rate-limit / network resilience configuration
# Yahoo will 401/429 or silently empty responses if hit too hard.
# ---------------------------------------------------------------------------
yf.set_tz_cache_location(os.path.join(OUT, "_yf_tz_cache"))
try:
    yf.config.network.retries = 5          # exponential backoff: 1s,2s,4s,8s,16s
except Exception:
    pass  # older yfinance versions
DOWNLOAD_BATCH_SIZE = 50                   # tickers per yf.download() call
INTER_BATCH_SLEEP_S = 3.0                  # pause between batches


def _download_batched(tickers, interval, period="max"):
    """Download history in chunks to respect Yahoo rate limits.
    Returns a wide DataFrame indexed by date, one column per ticker."""
    chunks = [tickers[i:i+DOWNLOAD_BATCH_SIZE] for i in range(0, len(tickers), DOWNLOAD_BATCH_SIZE)]
    print(f"\nDownloading {len(tickers)} tickers in {len(chunks)} batches "
          f"(batch={DOWNLOAD_BATCH_SIZE}, sleep={INTER_BATCH_SLEEP_S}s, retries={getattr(yf.config,'network',None) and getattr(yf.config.network,'retries','?')}) ...", flush=True)
    frames = []
    for i, chunk in enumerate(chunks, 1):
        t0 = time.time()
        data = yf.download(
            tickers=chunk,
            period=period,
            interval=interval,
            auto_adjust=True,
            actions=False,
            group_by="column",
            threads=True,
            progress=False,
            ignore_tz=True,
            timeout=60,
        )
        elapsed = time.time() - t0
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"].copy()
        else:
            close = data.to_frame(name=chunk[0]) if data.ndim == 1 else data.copy()
        close.index = pd.to_datetime(close.index)
        # normalize to month-end for monthly, else keep as-is
        if interval == "1mo":
            close.index = close.index.to_period("M").to_timestamp("M")
        close = close.sort_index()
        frames.append(close)
        n_cols = len(close.columns)
        print(f"  batch {i}/{len(chunks)}: {len(chunk)} tk -> {n_cols} cols, {len(close)} rows ({elapsed:.0f}s)", flush=True)
        if i < len(chunks):
            time.sleep(INTER_BATCH_SLEEP_S)
    if not frames:
        raise SystemExit("All batches returned empty")
    # Outer-join on date index so tickers with different histories align
    merged = pd.concat(frames, axis=1).sort_index()
    merged = merged.loc[~merged.index.duplicated(keep="first")]
    return merged

# ---------------------------------------------------------------------------
# 1. ASSET-CLASS UNIVERSE
#    Each entry: ticker -> (name, asset_class, kind, notes)
#    kind in {ETF, INDEX, FUTURES, YIELD}
#    For broad indices we include both the investable ETF and the long-history
#    index so we get the longest possible monthly history per asset class.
# ---------------------------------------------------------------------------
ASSET_TICKERS = {
    # ---- US Equity ----
    "^GSPC":  ("S&P 500 Index",                 "US Equity",            "INDEX",   "S&P 500 price index; monthly back to ~1985"),
    "SPY":    ("SPDR S&P 500 ETF",              "US Equity",            "ETF",     "S&P 500 total return; since 1993"),
    "VTI":    ("Vanguard Total US Market ETF",  "US Equity",            "ETF",     "CRSP US total market; since 2001"),
    "QQQ":    ("Invesco Nasdaq-100 ETF",        "US Equity",            "ETF",     "Nasdaq-100; since 1999"),
    "^IXIC":  ("Nasdaq Composite Index",        "US Equity",            "INDEX",   "Nasdaq composite; back to ~1985"),
    "^DJI":   ("Dow Jones Industrial Avg",      "US Equity",            "INDEX",   "Dow 30; back to ~1985"),
    "IWM":    ("iShares Russell 2000 ETF",      "US Equity",            "ETF",     "US small cap; since 2000"),
    "^RUT":   ("Russell 2000 Index",            "US Equity",            "INDEX",   "US small cap index; back to ~1985"),
    "SPHB":   ("Invesco S&P 500 High Beta ETF", "US Equity",            "ETF",     "high-beta slice; since 2011"),
    # ---- International / Emerging Equity ----
    "EFA":    ("iShares MSCI EAFE ETF",         "International Equity", "ETF",     "developed ex-US; since 2001"),
    "VEA":    ("Vanguard FTSE Developed ETF",  "International Equity", "ETF",     "developed ex-US; since 2007"),
    "VWO":    ("Vanguard Emerging Markets ETF","International Equity", "ETF",     "emerging markets; since 2005"),
    "EEM":    ("iShares MSCI Emerging ETF",    "International Equity", "ETF",     "emerging markets; since 2003"),
    "VXUS":   ("Vanguard Total Intl Stock ETF","International Equity", "ETF",     "ex-US total; since 2011"),
    # ---- Fixed Income ----
    "AGG":    ("iShares Core US Aggregate Bond","US Bonds",            "ETF",     "investment-grade agg; since 2003"),
    "BND":    ("Vanguard Total Bond Market",   "US Bonds",             "ETF",     "broad US bonds; since 2007"),
    "IEF":    ("iShares 7-10yr Treasury",      "US Treasuries",        "ETF",     "intermediate treasuries; since 2002"),
    "TLT":    ("iShares 20+yr Treasury Bond",   "US Treasuries",        "ETF",     "long treasuries; since 2002"),
    "SHY":    ("iShares 1-3yr Treasury",        "US Treasuries",        "ETF",     "short treasuries; since 2002"),
    "LQD":    ("iShares IG Corporate Bond",     "US Corporate Bonds",   "ETF",     "investment-grade corp; since 2002"),
    "HYG":    ("iShares High Yield Corp Bond",  "US Corporate Bonds",   "ETF",     "high yield; since 2007"),
    "TIP":    ("iShares TIPS Bond",             "US Bonds",             "ETF",     "inflation-protected treasuries; since 2003"),
    "MUB":    ("iShares National Muni Bond",    "US Municipal Bonds",   "ETF",     "tax-exempt munis; since 2007"),
    "^TNX":   ("CBOE 10yr Treasury Yield",      "US Treasuries",        "YIELD",   "yield LEVEL (not a price); back to ~1985"),
    # ---- Real Assets ----
    "GLD":    ("SPDR Gold Shares",             "Gold",                 "ETF",     "gold; since 2004"),
    "IAU":    ("iShares Gold Trust",           "Gold",                 "ETF",     "gold; since 2005"),
    "SLV":    ("iShares Silver Trust",         "Silver",               "ETF",     "silver; since 2006"),
    "VNQ":    ("Vanguard Real Estate ETF",      "US REIT",              "ETF",     "US REITs; since 2004"),
    "IYR":    ("iShares US Real Estate ETF",   "US REIT",              "ETF",     "US real estate; since 2000"),
    "DBC":    ("Invesco DB Commodity Index",   "Commodities",          "ETF",     "broad commodities; since 2006"),
    "GSG":    ("iShares S&P GSCI Commodity",   "Commodities",          "ETF",     "broad commodities; since 2006"),
    "PDBC":   ("Invesco Optimum Yield Commodity","Commodities",        "ETF",     "broad commodities; since 2014"),
    # ---- Sector Equity ETFs (also feed 'asset class = sector equity') ----
    "XLE":    ("Energy Select Sector SPDR",    "Sector-Energy",        "ETF",     "energy sector; since 1998"),
    "XLF":    ("Financial Select Sector SPDR", "Sector-Financials",    "ETF",     "financials; since 1998"),
    "XLK":    ("Technology Select Sector SPDR","Sector-Technology",    "ETF",     "technology; since 1998"),
    "XLV":    ("Health Care Select Sector SPDR","Sector-Healthcare",   "ETF",     "healthcare; since 1998"),
    "XLY":    ("Consumer Discretionary SPDR",  "Sector-Cons Disc",     "ETF",     "consumer discretionary; since 1998"),
    "XLP":    ("Consumer Staples Select SPDR","Sector-Cons Staples",  "ETF",     "consumer staples; since 1998"),
    "XLI":    ("Industrial Select Sector SPDR","Sector-Industrials",  "ETF",     "industrials; since 1998"),
    "XLB":    ("Materials Select Sector SPDR", "Sector-Materials",    "ETF",     "materials; since 1998"),
    "XLU":    ("Utilities Select Sector SPDR", "Sector-Utilities",    "ETF",     "utilities; since 1998"),
    "XLRE":   ("Real Estate Select Sector SPDR","Sector-Real Estate", "ETF",     "real estate sector; since 2015"),
    "XLC":    ("Communication Services SPDR",  "Sector-Comm Services","ETF",     "comm services; since 2018"),
    # ---- Cryptocurrency / Digital Assets ----
    "GBTC":   ("Grayscale Bitcoin Trust",        "Digital Assets",       "ETF",     "bitcoin trust; since 2015"),
    "IBIT":   ("iShares Bitcoin Trust ETF",      "Digital Assets",       "ETF",     "spot bitcoin; since 2024"),
    "BITO":   ("ProShares Bitcoin Strategy ETF", "Digital Assets",       "ETF",     "bitcoin futures; since 2021"),
    # ---- Small/Mid Cap (deeper US equity coverage) ----
    "IJH":    ("iShares Core S&P Mid-Cap ETF",   "US Equity",            "ETF",     "mid cap; since 2000"),
    "MDY":    ("SPDR S&P MidCap 400 ETF",        "US Equity",            "ETF",     "mid cap; since 1995"),
    "VO":     ("Vanguard Mid-Cap ETF",            "US Equity",            "ETF",     "mid cap blend; since 2004"),
    "IJS":    ("iShares S&P SmallCap 600 Value", "US Equity",            "ETF",     "small cap value; since 2000"),
    "IJT":    ("iShares S&P SmallCap 600 Growth","US Equity",            "ETF",     "small cap growth; since 2000"),
    "VBR":    ("Vanguard Small-Cap Value ETF",   "US Equity",            "ETF",     "small cap value; since 2004"),
    "VB":     ("Vanguard Small-Cap ETF",         "US Equity",            "ETF",     "small cap blend; since 2004"),
    # ---- International detail ----
    "VGK":    ("Vanguard FTSE Europe ETF",       "International Equity", "ETF",     "developed Europe; since 2005"),
    "VPL":    ("Vanguard FTSE Pacific ETF",      "International Equity", "ETF",     "developed Pacific; since 2005"),
    "FXI":    ("iShares China Large-Cap ETF",    "International Equity", "ETF",     "china large cap; since 2004"),
    # ---- EM Bonds ----
    "EMB":    ("iShares EM USD Bond ETF",        "EM Bonds",             "ETF",     "emerging market USD bonds; since 2007"),
    # ---- Currency ----
    "UUP":    ("Invesco DB US Dollar Bullish",   "Currency",             "ETF",     "long USD vs basket; since 2007"),
    # ---- More Treasuries ----
    "^FVX":   ("CBOE 5yr Treasury Yield",        "US Treasuries",        "YIELD",   "5yr treasury yield; back to ~1985"),
    "^TYX":   ("CBOE 30yr Treasury Yield",       "US Treasuries",        "YIELD",   "30yr treasury yield; back to ~1985"),
    # ---- Preferred / Convertibles ----
    "PFF":    ("iShares Preferred ETF",          "Preferred Stock",      "ETF",     "preferred stock; since 2007"),
    # ---- Commodities / Natural resources ----
    "USO":    ("United States Oil Fund",          "Commodities",          "ETF",     "WTI crude oil; since 2006"),
    # ---- Sector: Biotech ----
    "IBB":    ("iShares Biotechnology ETF",      "Sector-Biotech",       "ETF",     "biotech; since 2001"),
    "XBI":    ("SPDR S&P Biotech ETF",           "Sector-Biotech",       "ETF",     "biotech equal-weight; since 2006"),
    # ---- Sector: Semiconductors ----
    "SMH":    ("VanEck Semiconductor ETF",       "Sector-Semiconductors","ETF",     "semiconductors; since 2000"),
    "SOXX":   ("iShares Semiconductor ETF",      "Sector-Semiconductors","ETF",     "semiconductors; since 2001"),
    # ---- Sector: Homebuilders ----
    "XHB":    ("SPDR S&P Homebuilders ETF",      "Sector-Homebuilders","ETF",     "homebuilders; since 2006"),
    # ---- Sector: Regional Banks ----
    "KRE":    ("SPDR S&P Regional Banking ETF",  "Sector-Financials",   "ETF",     "regional banks; since 2006"),
    # ---- Sector: Clean Energy ----
    "ICLN":   ("iShares Global Clean Energy ETF","Sector-Clean Energy", "ETF",     "clean energy; since 2008"),
    # ---- Dividends ----
    "NOBL":   ("ProShares Dividend Aristocrats",  "US Equity",            "ETF",     "dividend aristocrats; since 2013"),
    # ---- Alternatives / risk ----
    "^VIX":   ("CBOE Volatility Index",        "Volatility",           "INDEX",   "VIX level; since 1990"),
    # ====================================================================
    # MUTUAL FUNDS & ADDITIONAL ETFs (from user-provided list)
    # Adds Vanguard mutual funds, iShares ETFs, Fidelity/PIMCO/etc funds.
    # Yahoo provides daily history back to fund inception for most of these.
    # ====================================================================
    # Commodities (1)
    "PCRIX":  ("PIMCO Commodity Real Ret Strat Instl", "Commodities", "MUTUALFUND", "commodity real return strategy"),
    # Gold/Precious Metals (3)
    "ASA":    ("ASA Gold and Precious Metals Ltd", "Gold/Precious Metals", "STOCK", "closed-end gold and precious metals"),
    "FSAGX":  ("Fidelity Select Gold", "Gold/Precious Metals", "MUTUALFUND", "gold sector fund"),
    "INIVX":  ("VanEck International Investors Gold A", "Gold/Precious Metals", "MUTUALFUND", "gold mining equity"),
    # International Bonds (7)
    "BNDW":   ("Vanguard Total World Bond ETF", "International Bonds", "ETF", "global bond USD hedged"),
    "IGOV":   ("iShares International Treasury Bond ETF", "International Bonds", "ETF", "intl govt bonds"),
    "PADMX":  ("PIMCO Global Bond Fund Unhedged", "International Bonds", "MUTUALFUND", "global bond unhedged"),
    "PAGPX":  ("PIMCO Global Bond Fund Unhedged Adm", "International Bonds", "MUTUALFUND", "global bond unhedged"),
    "PIGLX":  ("PIMCO Global Bond Fund Unhedged Instl", "International Bonds", "MUTUALFUND", "global bond unhedged"),
    "VTABX":  ("Vanguard Total Intl Bond Idx Admiral", "International Bonds", "MUTUALFUND", "intl bond index admiral"),
    "VTIBX":  ("Vanguard Total Intl Bond Idx Investor", "International Bonds", "MUTUALFUND", "intl bond index investor"),
    # International Equity (18)
    "DISV":   ("Dimensional Intl Small Cap Value ETF", "International Equity", "ETF", "intl small cap value"),
    "DISVX":  ("DFA International Small Cap Value Portfolio", "International Equity", "MUTUALFUND", "intl small cap value"),
    "EFV":    ("iShares MSCI EAFE Value ETF", "International Equity", "ETF", "developed ex-US value"),
    "ISVL":   ("iShares Intl Developed Small Cap Value", "International Equity", "ETF", "intl developed small cap value"),
    "VDVIX":  ("Vanguard Developed Markets Index Fund", "International Equity", "MUTUALFUND", "developed ex-US"),
    "VEIEX":  ("Vanguard Emerging Markets Stock Index Inv", "International Equity", "MUTUALFUND", "emerging markets"),
    "VEMAX":  ("Vanguard Emerging Markets Stock Index Adm", "International Equity", "MUTUALFUND", "emerging markets"),
    "VEURX":  ("Vanguard FTSE Europe ETF", "International Equity", "MUTUALFUND", "developed Europe"),
    "VEUSX":  ("Vanguard FTSE Europe ETF Adm", "International Equity", "MUTUALFUND", "developed Europe"),
    "VFSAX":  ("Vanguard FTSE All-World ex-US Small Cap", "International Equity", "MUTUALFUND", "ex-US small cap"),
    "VGTSX":  ("Vanguard Total Intl Stock Index Inv", "International Equity", "MUTUALFUND", "total intl stock"),
    "VINEX":  ("Vanguard International Explorer Inv", "International Equity", "MUTUALFUND", "intl explorer"),
    "VPACX":  ("Vanguard Pacific Stock Index Investor", "International Equity", "MUTUALFUND", "Pacific developed"),
    "VPADX":  ("Vanguard Pacific Stock Index Admiral", "International Equity", "MUTUALFUND", "Pacific developed"),
    "VSS":    ("Vanguard FTSE All-World ex-US Small-Cap ETF", "International Equity", "ETF", "ex-US small cap"),
    "VTIAX":  ("Vanguard Total Intl Stock Index Admiral", "International Equity", "MUTUALFUND", "total intl stock"),
    "VTMGX":  ("Vanguard Developed Markets Index Admiral", "International Equity", "MUTUALFUND", "developed ex-US"),
    "VTRIX":  ("Vanguard International Value Inv", "International Equity", "MUTUALFUND", "intl value"),
    # Money Market (3)
    "SPAXX":  ("Fidelity Government Money Market", "Money Market", "MONEYMARKET", "govt money market"),
    "VMRXX":  ("Vanguard Cash Reserves Money Market", "Money Market", "MONEYMARKET", "cash reserves"),
    "VUSXX":  ("Vanguard Treasury Money Market", "Money Market", "MONEYMARKET", "treasury money market"),
    # Sector-Energy (2)
    "VGELX":  ("Vanguard Energy Opportunities Admiral", "Sector-Energy", "MUTUALFUND", "energy sector"),
    "VGENX":  ("Vanguard Energy Opportunities Investor", "Sector-Energy", "MUTUALFUND", "energy sector"),
    # Sector-Healthcare (2)
    "VGHAX":  ("Vanguard Health Care Fund Admiral", "Sector-Healthcare", "MUTUALFUND", "healthcare sector"),
    "VGHCX":  ("Vanguard Health Care Fund Investor", "Sector-Healthcare", "MUTUALFUND", "healthcare sector"),
    # Sector-Utilities (1)
    "FKUTX":  ("Franklin Utilities A1", "Sector-Utilities", "MUTUALFUND", "utilities sector"),
    # US Bonds (15)
    "FIPDX":  ("Fidelity Inflation-Prot Bond Index", "US Bonds", "MUTUALFUND", "TIPS index"),
    "LTPZ":   ("PIMCO 15+ Year U.S. TIPS ETF", "US Bonds", "ETF", "long-term TIPS"),
    "SCHP":   ("Schwab U.S. TIPS ETF", "US Bonds", "ETF", "TIPS"),
    "STIP":   ("iShares 0-5 Year TIPS Bond ETF", "US Bonds", "ETF", "short-term TIPS"),
    "VAIPX":  ("Vanguard Inflation-Protected Securities Adm", "US Bonds", "MUTUALFUND", "TIPS admiral"),
    "VBIIX":  ("Vanguard Intermediate-Term Bond Index Inv", "US Bonds", "MUTUALFUND", "intermediate bond index"),
    "VBILX":  ("Vanguard Intermediate-Term Bond Index Adm", "US Bonds", "MUTUALFUND", "intermediate bond index"),
    "VBIRX":  ("Vanguard Short-Term Bond Index Adm", "US Bonds", "MUTUALFUND", "short-term bond index"),
    "VBISX":  ("Vanguard Short-Term Bond Index Inv", "US Bonds", "MUTUALFUND", "short-term bond index"),
    "VBMFX":  ("Vanguard Total Bond Market Index Inv", "US Bonds", "MUTUALFUND", "total bond market"),
    "VBTLX":  ("Vanguard Total Bond Market Index Adm", "US Bonds", "MUTUALFUND", "total bond market"),
    "VIPSX":  ("Vanguard Inflation-Protected Securities Inv", "US Bonds", "MUTUALFUND", "TIPS investor"),
    "VTAPX":  ("Vanguard Short-Term TIPS Idx Admiral", "US Bonds", "MUTUALFUND", "short-term TIPS admiral"),
    "VTIP":   ("Vanguard Short-Term TIPS ETF", "US Bonds", "ETF", "short-term TIPS"),
    "VTIPX":  ("Vanguard Short-Term TIPS Idx Investor", "US Bonds", "MUTUALFUND", "short-term TIPS investor"),
    # US Corporate Bonds (10)
    "FBNDX":  ("Fidelity Investment Grade Bond Fund", "US Corporate Bonds", "MUTUALFUND", "investment grade"),
    "PINCX":  ("Putnam Income A", "US Corporate Bonds", "MUTUALFUND", "income fund"),
    "VCIT":   ("Vanguard Intermediate-Term Corporate Bond ETF", "US Corporate Bonds", "ETF", "intermediate corp"),
    "VFSTX":  ("Vanguard Short-Term Investment Grade Inv", "US Corporate Bonds", "MUTUALFUND", "short-term IG"),
    "VFSUX":  ("Vanguard Short-Term Investment Grade Adm", "US Corporate Bonds", "MUTUALFUND", "short-term IG"),
    "VICSX":  ("Vanguard Intermediate-Term Corp Bond Idx Adm", "US Corporate Bonds", "MUTUALFUND", "intermediate corp"),
    "VWEAX":  ("Vanguard High-Yield Corporate Admiral", "US Corporate Bonds", "MUTUALFUND", "high yield"),
    "VWEHX":  ("Vanguard High-Yield Corporate Investor", "US Corporate Bonds", "MUTUALFUND", "high yield"),
    "VWESX":  ("Vanguard Long-Term Investment-Grade Inv", "US Corporate Bonds", "MUTUALFUND", "long-term IG"),
    "VWETX":  ("Vanguard Long-Term Investment-Grade Adm", "US Corporate Bonds", "MUTUALFUND", "long-term IG"),
    # US Equity (56)
    "AIVSX":  ("American Funds Invmt Co of Amer A", "US Equity", "MUTUALFUND", "large cap value"),
    "AUBAX":  ("Invesco Balanced Fund A", "US Equity", "MUTUALFUND", "balanced"),
    "BRSIX":  ("Bridgeway Ultra-Small Company Market", "US Equity", "MUTUALFUND", "micro cap"),
    "FFIDX":  ("Fidelity Fund", "US Equity", "MUTUALFUND", "large cap blend"),
    "FMAGX":  ("Fidelity Magellan Fund", "US Equity", "MUTUALFUND", "large cap growth"),
    "IVV":    ("iShares Core S&P 500 ETF", "US Equity", "ETF", "S&P 500"),
    "IWC":    ("iShares Micro-Cap ETF", "US Equity", "ETF", "micro cap"),
    "LOMMX":  ("CGM Mutual Fund", "US Equity", "MUTUALFUND", "flexible"),
    "MIGFX":  ("MFS Massachusetts Inv Gr Stk A", "US Equity", "MUTUALFUND", "large cap growth"),
    "MITTX":  ("MFS Massachusetts Investors Tr A", "US Equity", "MUTUALFUND", "large cap blend"),
    "MTUM":   ("iShares MSCI USA Momentum Factor ETF", "US Equity", "ETF", "momentum factor"),
    "NAESX":  ("Vanguard Small Cap Index Inv", "US Equity", "MUTUALFUND", "small cap blend"),
    "OTCFX":  ("T. Rowe Price Small-Cap Stock", "US Equity", "MUTUALFUND", "small cap"),
    "PIODX":  ("Victory Pioneer A", "US Equity", "MUTUALFUND", "balanced"),
    "PIORX":  ("Victory Pioneer R", "US Equity", "MUTUALFUND", "balanced"),
    "QUAL":   ("iShares MSCI USA Quality Factor ETF", "US Equity", "ETF", "quality factor"),
    "TEPLX":  ("Templeton Growth A", "US Equity", "MUTUALFUND", "growth"),
    "USMV":   ("iShares MSCI USA Min Vol Factor ETF", "US Equity", "ETF", "min volatility factor"),
    "VDADX":  ("Vanguard Dividend Appreciation Index Adm", "US Equity", "MUTUALFUND", "dividend growth"),
    "VEXAX":  ("Vanguard Extended Market Index Adm", "US Equity", "MUTUALFUND", "extended market (ex-S&P500)"),
    "VEXMX":  ("Vanguard Extended Market Index Inv", "US Equity", "MUTUALFUND", "extended market (ex-S&P500)"),
    "VEXPX":  ("Vanguard Explorer Fund Investor", "US Equity", "MUTUALFUND", "mid cap growth"),
    "VEXRX":  ("Vanguard Explorer Fund Admiral", "US Equity", "MUTUALFUND", "mid cap growth"),
    "VFIAX":  ("Vanguard 500 Index Fund Admiral", "US Equity", "MUTUALFUND", "S&P 500"),
    "VFINX":  ("Vanguard 500 Index Fund Investor", "US Equity", "MUTUALFUND", "S&P 500"),
    "VFTAX":  ("Vanguard FTSE Social Index Fund Adm", "US Equity", "MUTUALFUND", "ESG/socially responsible"),
    "VHYAX":  ("Vanguard High Dividend Yield Index Adm", "US Equity", "MUTUALFUND", "high dividend yield"),
    "VICEX":  ("USA Mutuals Vice Investor", "US Equity", "MUTUALFUND", "vice stocks (alcohol/tobacco/gambling)"),
    "VIG":    ("Vanguard Dividend Appreciation ETF", "US Equity", "ETF", "dividend growth"),
    "VIGAX":  ("Vanguard Growth Index Admiral", "US Equity", "MUTUALFUND", "large cap growth"),
    "VIGRX":  ("Vanguard Growth Index Investor", "US Equity", "MUTUALFUND", "large cap growth"),
    "VIMAX":  ("Vanguard Mid Cap Index Admiral", "US Equity", "MUTUALFUND", "mid cap blend"),
    "VIMSX":  ("Vanguard Mid Cap Index Investor", "US Equity", "MUTUALFUND", "mid cap blend"),
    "VISGX":  ("Vanguard Small Cap Growth Index Inv", "US Equity", "MUTUALFUND", "small cap growth"),
    "VISVX":  ("Vanguard Small Cap Value Index Inv", "US Equity", "MUTUALFUND", "small cap value"),
    "VIVAX":  ("Vanguard Value Index Inv", "US Equity", "MUTUALFUND", "large cap value"),
    "VLUE":   ("iShares MSCI USA Value Factor ETF", "US Equity", "ETF", "value factor"),
    "VMGIX":  ("Vanguard Mid-Cap Growth Index Investor", "US Equity", "MUTUALFUND", "mid cap growth"),
    "VMGMX":  ("Vanguard Mid-Cap Growth Index Admiral", "US Equity", "MUTUALFUND", "mid cap growth"),
    "VMVAX":  ("Vanguard Mid-Cap Value Index Admiral", "US Equity", "MUTUALFUND", "mid cap value"),
    "VMVIX":  ("Vanguard Mid-Cap Value Index Investor", "US Equity", "MUTUALFUND", "mid cap value"),
    "VSGAX":  ("Vanguard Small Cap Growth Index Admiral", "US Equity", "MUTUALFUND", "small cap growth"),
    "VSIAX":  ("Vanguard Small Cap Value Index Admiral", "US Equity", "MUTUALFUND", "small cap value"),
    "VSMAX":  ("Vanguard Small Cap Index Admiral", "US Equity", "MUTUALFUND", "small cap blend"),
    "VTSAX":  ("Vanguard Total Stock Market Index Adm", "US Equity", "MUTUALFUND", "total US market"),
    "VTSMX":  ("Vanguard Total Stock Market Index Inv", "US Equity", "MUTUALFUND", "total US market"),
    "VVIAX":  ("Vanguard Value Index Admiral", "US Equity", "MUTUALFUND", "large cap value"),
    "VWELX":  ("Vanguard Wellington Fund Investor", "US Equity", "MUTUALFUND", "balanced value"),
    "VWENX":  ("Vanguard Wellington Fund Admiral", "US Equity", "MUTUALFUND", "balanced value"),
    "VWIAX":  ("Vanguard Wellesley Income Admiral", "US Equity", "MUTUALFUND", "balanced income"),
    "VWINX":  ("Vanguard Wellesley Income Investor", "US Equity", "MUTUALFUND", "balanced income"),
    "VWNAX":  ("Vanguard Windsor II Admiral", "US Equity", "MUTUALFUND", "large cap value"),
    "VWNDX":  ("Vanguard Windsor Fund Investor", "US Equity", "MUTUALFUND", "large cap value"),
    "VWNEX":  ("Vanguard Windsor Fund Admiral", "US Equity", "MUTUALFUND", "large cap value"),
    "VWNFX":  ("Vanguard Windsor II Investor", "US Equity", "MUTUALFUND", "large cap value"),
    "VYM":    ("Vanguard High Dividend Yield ETF", "US Equity", "ETF", "high dividend yield"),
    # US Municipal Bonds (6)
    "VWITX":  ("Vanguard Intermediate-Term Tax-Exempt Inv", "US Municipal Bonds", "MUTUALFUND", "intermediate tax-exempt"),
    "VWIUX":  ("Vanguard Intermediate-Term Tax-Exempt Adm", "US Municipal Bonds", "MUTUALFUND", "intermediate tax-exempt"),
    "VWLTX":  ("Vanguard Long-Term Tax-Exempt Inv", "US Municipal Bonds", "MUTUALFUND", "long-term tax-exempt"),
    "VWLUX":  ("Vanguard Long-Term Tax-Exempt Adm", "US Municipal Bonds", "MUTUALFUND", "long-term tax-exempt"),
    "VWSTX":  ("Vanguard Ultra Short-Term Tax-Exempt Inv", "US Municipal Bonds", "MUTUALFUND", "ultra short tax-exempt"),
    "VWSUX":  ("Vanguard Ultra Short-Term Tax-Exempt Adm", "US Municipal Bonds", "MUTUALFUND", "ultra short tax-exempt"),
    # US REIT (2)
    "VGSIX":  ("Vanguard Real Estate Index Investor", "US REIT", "MUTUALFUND", "US REITs"),
    "VGSLX":  ("Vanguard Real Estate Index Admiral", "US REIT", "MUTUALFUND", "US REITs"),
    # US Treasuries (13)
    "EDV":    ("Vanguard Extended Duration Treasury ETF", "US Treasuries", "ETF", "long-duration treasury"),
    "VFIRX":  ("Vanguard Short-Term Treasury Fund Adm", "US Treasuries", "MUTUALFUND", "short-term treasury"),
    "VFISX":  ("Vanguard Short-Term Treasury Fund Inv", "US Treasuries", "MUTUALFUND", "short-term treasury"),
    "VFITX":  ("Vanguard Intermediate-Term Treasury Inv", "US Treasuries", "MUTUALFUND", "intermediate treasury"),
    "VFIUX":  ("Vanguard Intermediate-Term Treasury Adm", "US Treasuries", "MUTUALFUND", "intermediate treasury"),
    "VGIT":   ("Vanguard Intermediate-Term Treasury ETF", "US Treasuries", "ETF", "intermediate treasury"),
    "VGLT":   ("Vanguard Long-Term Treasury ETF", "US Treasuries", "ETF", "long-term treasury"),
    "VGSH":   ("Vanguard Short-Term Treasury ETF", "US Treasuries", "ETF", "short-term treasury"),
    "VLGSX":  ("Vanguard Long-Term Treasury Index Adm", "US Treasuries", "MUTUALFUND", "long-term treasury"),
    "VSBSX":  ("Vanguard Short-Term Treasury Index Adm", "US Treasuries", "MUTUALFUND", "short-term treasury"),
    "VSIGX":  ("Vanguard Intermediate-Term Treasury Index Adm", "US Treasuries", "MUTUALFUND", "intermediate treasury"),
    "VUSTX":  ("Vanguard Long-Term Treasury Inv", "US Treasuries", "MUTUALFUND", "long-term treasury"),
    "VUSUX":  ("Vanguard Long-Term Treasury Admiral", "US Treasuries", "MUTUALFUND", "long-term treasury"),
    # World Equity (4)
    "OPPAX":  ("Invesco Global Fund A", "World Equity", "MUTUALFUND", "global equity"),
    "VGPMX":  ("Vanguard Global Capital Cycles Investor", "World Equity", "MUTUALFUND", "global capital cycles"),
    "VT":     ("Vanguard Total World Stock ETF", "World Equity", "ETF", "global total market"),
    "VTWAX":  ("Vanguard Total World Stock Index Admiral", "World Equity", "MUTUALFUND", "global total market"),
}

# ---------------------------------------------------------------------------
# 2. INDIVIDUAL STOCK UNIVERSE  (large caps across GICS sectors)
#    Sector labels are GICS sectors. These get grouped into 'asset class = Equity'
#    and also aggregated by sector.
# ---------------------------------------------------------------------------
STOCK_SECTORS = {
    "Technology":          ["AAPL","MSFT","NVDA","AVGO","ORCL","ADBE","CRM","INTC","AMD","CSCO","QCOM","TXN","IBM","NOW","INTU","UBER","PANW","SNOW","MU"],
    "Communication Srv":   ["GOOGL","META","VZ","TMUS","CMCSA","T","NFLX","DIS"],
    "Consumer Discretionary":["AMZN","TSLA","HD","MCD","NKE","SBUX","LOW","BKNG","F","GM","MAR","TJX"],
    "Consumer Staples":    ["WMT","KO","PEP","PG","COST","MDLZ","CL","TGT","PM","MO","EL"],
    "Healthcare":          ["JNJ","UNH","LLY","PFE","ABBV","MRK","TMO","ABT","DHR","BMY","ISRG","ELV","CI","CVS"],
    "Financials":          ["JPM","BAC","WFC","GS","MS","BLK","V","MA","AXP","SCHW","CB","BRK-B","SPGI","C","USB","PNC","AIG"],
    "Industrials":         ["BA","CAT","GE","HON","UPS","UNP","RTX","DE","LMT","ADP","ITW","FDX","NSC","WM","LHX"],
    "Energy":              ["XOM","CVX","COP","SLB","EOG","PSX","MPC","KMI","WMB","OXY"],
    "Materials":           ["LIN","APD","NEM","FCX","DOW","CTVA","ECL"],
    "Utilities":           ["NEE","DUK","SO","AEP","EXC","SRE","D"],
    "Real Estate":         ["PLD","AMT","CCI","EQIX","SPG","PSA","WELL","O"],
}

STOCKS = {}
for sector, tickers in STOCK_SECTORS.items():
    for t in tickers:
        STOCKS[t] = (f"{t} common stock", "Equity (single stock)", sector)

ALL_TICKERS = {**ASSET_TICKERS, **STOCKS}

# ---------------------------------------------------------------------------
# 2b. RETURN-SERIES POLICY  (single source of truth; also used by
#     build_aggregates.py so the offline builder and a live re-pull agree)
#
#     Some tickers are carried in the price matrices for continuity but their
#     pct_change is NOT a return, so they must never enter a return aggregate:
#       - YIELD kind (^TNX/^FVX/^TYX) are yield LEVELS. Yields move opposite to
#         bond prices, so averaging them into a bond sleeve inverts it -- the
#         published US Treasuries sleeve correlated -0.51 with a clean rebuild
#         and understated return by 289 bps/yr.
#       - ^VIX is likewise a level, and is the sole member of "Volatility", so
#         excluding it removes that asset class from the aggregates entirely.
#       - The broad equity indices are price-only (no dividends) where every
#         other constituent is total-return.
#
#     NOTE: these tickers stay in the ticker-level outputs and price matrices.
#     risk_parity_seasons.py legitimately reads the ^TNX yield LEVEL as an
#     inflation-regime signal; only return AGGREGATION is affected.
# ---------------------------------------------------------------------------
NON_RETURN_KINDS = {"YIELD"}
NON_RETURN_TICKERS = {
    "^GSPC", "^DJI", "^IXIC", "^RUT",   # price-only indices (no dividends)
    "^VIX",                              # a level, not a holdable return stream
}


def is_return_series(ticker: str, meta: tuple) -> bool:
    """True if this ticker's pct_change is a genuine total return, i.e. it may
    enter an asset-class/sector return aggregate.

    meta[2] is the `kind` for asset tickers and the GICS sector for single
    stocks; single stocks never carry a NON_RETURN_KINDS value, so the same
    test is safe for both tuple schemas.
    """
    return ticker not in NON_RETURN_TICKERS and meta[2] not in NON_RETURN_KINDS

# ---------------------------------------------------------------------------
# 3. DOWNLOAD  monthly history (period='max', interval='1mo')
#    Uses _download_batched() to respect Yahoo rate limits.
# ---------------------------------------------------------------------------
def download_all(tickers: list[str]) -> pd.DataFrame:
    """Download monthly adjusted close for all tickers. Returns wide DataFrame
    indexed by month-end date with one column per ticker (adjusted close)."""
    return _download_batched(tickers, interval="1mo", period="max")

# ---------------------------------------------------------------------------
# 3b. PIPELINE ENTRY POINT
#     Everything below runs ONLY as a script. Previously this executed at
#     import time, so `import pull_returns` triggered a full Yahoo download
#     and overwrote every monthly CSV -- pull_daily.py imports this module,
#     and so does build_aggregates.py (for the universe + return policy).
# ---------------------------------------------------------------------------
def main() -> None:
    prices = download_all(list(ALL_TICKERS.keys()))
    print("Raw prices shape:", prices.shape)
    print("Date range:", prices.index.min(), "->", prices.index.max())

    # Drop tickers that came back entirely empty
    empty = [c for c in prices.columns if prices[c].dropna().empty]
    if empty:
        print("WARNING: no data for", empty)
        prices = prices.drop(columns=empty)

    # ---------------------------------------------------------------------------
    # 4. MONTHLY RETURNS  (pct change of adjusted close). Yields/VIX levels kept as-is
    #    in prices but NOT used in return aggregation.
    # ---------------------------------------------------------------------------
    returns = prices.pct_change()

    # ---------------------------------------------------------------------------
    # 5. LONG PANEL with metadata
    # ---------------------------------------------------------------------------
    rows = []
    for ticker in prices.columns:
        meta = ALL_TICKERS.get(ticker)
        if meta is None:
            continue
        name, asset_class, sector = meta[0], meta[1], meta[2]
        s = returns[ticker].dropna()
        for dt, r in s.items():
            rows.append({
                "date": dt,
                "ticker": ticker,
                "name": name,
                "asset_class": asset_class,
                "sector": sector,
                "monthly_return": r,
            })
    long_panel = pd.DataFrame(rows).sort_values(["asset_class","sector","ticker","date"])
    long_panel.to_csv(os.path.join(OUT, "monthly_returns_by_ticker.csv"), index=False)
    print("Wrote monthly_returns_by_ticker.csv rows=", len(long_panel))

    # ---------------------------------------------------------------------------
    # 6. ASSET-CLASS LEVEL  equal-weighted monthly return across constituents
    #    (average of available tickers' returns each month within the asset class)
    # ---------------------------------------------------------------------------
    ac_groups = {}
    for ticker, meta in ALL_TICKERS.items():
        name, asset_class, sector = meta[0], meta[1], meta[2]
        if ticker not in returns.columns:
            continue
        if asset_class.startswith("Sector-") or asset_class == "Equity (single stock)":
            continue  # single stocks + sector ETFs handled separately
        if not is_return_series(ticker, meta):
            continue  # yield/price-only levels are not returns -- see §2b
        ac_groups.setdefault(asset_class, []).append(ticker)

    ac_wide = pd.DataFrame(index=returns.index)
    for ac, tks in ac_groups.items():
        sub = returns[tks]
        ac_wide[ac] = sub.mean(axis=1, skipna=True)
    ac_wide = ac_wide.dropna(how="all").sort_index()
    ac_wide.to_csv(os.path.join(OUT, "monthly_returns_by_asset_class.csv"))
    print("Wrote monthly_returns_by_asset_class.csv shape=", ac_wide.shape)

    # Sector level (from sector ETFs + individual stocks)
    sec_groups = {}
    for ticker, meta in ALL_TICKERS.items():
        name, asset_class, sector = meta[0], meta[1], meta[2]
        if ticker not in returns.columns:
            continue
        if not is_return_series(ticker, meta):
            continue  # yield/price-only levels are not returns -- see §2b
        sec = sector
        if not sec:
            continue
        # NOTE: `sector` here is meta[2], which holds the *kind* for asset tickers
        # and the GICS sector only for single stocks -- so this strip never fires
        # (the "Sector-" values live in meta[1]) and the composite columns are
        # kinds (ETF/MUTUALFUND/...) alongside real GICS sectors.
        if sec.startswith("Sector-"):
            sec = sec.replace("Sector-","")
        sec_groups.setdefault(sec, []).append(ticker)
    sec_wide = pd.DataFrame(index=returns.index)
    for sec, tks in sec_groups.items():
        sub = returns[tks]
        sec_wide[sec] = sub.mean(axis=1, skipna=True)
    sec_wide = sec_wide.dropna(how="all").sort_index()
    sec_wide.to_csv(os.path.join(OUT, "monthly_returns_by_sector.csv"))
    print("Wrote monthly_returns_by_sector.csv shape=", sec_wide.shape)

    # Stock-only sector aggregation (so sector returns reflect single stocks only)
    stock_sec = {}
    for ticker, (name, asset_class, sector) in STOCKS.items():
        if ticker not in returns.columns:
            continue
        stock_sec.setdefault(sector, []).append(ticker)
    stock_sec_wide = pd.DataFrame(index=returns.index)
    for sec, tks in stock_sec.items():
        sub = returns[tks]
        stock_sec_wide[sec] = sub.mean(axis=1, skipna=True)
    stock_sec_wide = stock_sec_wide.dropna(how="all").sort_index()
    stock_sec_wide.to_csv(os.path.join(OUT, "monthly_returns_by_sector_stocks_only.csv"))
    print("Wrote monthly_returns_by_sector_stocks_only.csv shape=", stock_sec_wide.shape)

    # ---------------------------------------------------------------------------
    # 7. PRICES (wide) + UNIVERSE + COVERAGE SUMMARY
    # ---------------------------------------------------------------------------
    prices.to_csv(os.path.join(OUT, "monthly_prices.csv"))

    uni_rows = []
    for ticker, meta in ALL_TICKERS.items():
        name, asset_class, sector = meta[0], meta[1], meta[2]
        if ticker in prices.columns:
            s = prices[ticker].dropna()
            first = s.index.min(); last = s.index.max(); n = len(s)
        else:
            first=last=pd.NaT; n=0
        uni_rows.append({"ticker":ticker,"name":name,"asset_class":asset_class,
                         "sector":sector,"first_month":first,"last_month":last,
                         "n_months":n,"present":ticker in prices.columns})
    uni = pd.DataFrame(uni_rows)
    uni.to_csv(os.path.join(OUT, "universe.csv"), index=False)

    cov_rows = []
    for ticker in returns.columns:
        meta = ALL_TICKERS.get(ticker)
        if meta is None: continue
        name, asset_class, sector = meta[0], meta[1], meta[2]
        s = returns[ticker].dropna()
        if s.empty:
            continue
        cov_rows.append({
            "ticker":ticker,"name":name,"asset_class":asset_class,"sector":sector,
            "first_month":s.index.min(),"last_month":s.index.max(),"n_months":len(s),
            "ann_return_pct": (s.mean()*12)*100,
            "ann_vol_pct": (s.std()* (12**0.5))*100,
            "min_month_pct": s.min()*100,
            "max_month_pct": s.max()*100,
            "pct_positive_months": (s>0).mean()*100,
        })
    cov = pd.DataFrame(cov_rows).sort_values(["asset_class","sector","ticker"])
    cov.to_csv(os.path.join(OUT, "coverage_summary.csv"), index=False)
    print("Wrote coverage_summary.csv rows=", len(cov))

    # Asset-class level coverage stats
    ac_cov_rows = []
    for ac, tks in ac_groups.items():
        s = ac_wide[ac].dropna()
        if s.empty: continue
        ac_cov_rows.append({"asset_class":ac,"first_month":s.index.min(),"last_month":s.index.max(),
                            "n_months":len(s),"ann_return_pct":(s.mean()*12)*100,
                            "ann_vol_pct":(s.std()*(12**0.5))*100,
                            "min_month_pct":s.min()*100,"max_month_pct":s.max()*100})
    pd.DataFrame(ac_cov_rows).to_csv(os.path.join(OUT, "asset_class_summary.csv"), index=False)

    # ---------------------------------------------------------------------------
    # 8. README
    # ---------------------------------------------------------------------------
    def _fmt(d): return d.strftime("%Y-%m") if isinstance(d, pd.Timestamp) else str(d)
    readme = f"""# Monthly Returns Across Asset Classes

    Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
    Source: Yahoo Finance via `yfinance` v{yf.__version__}. Prices are **auto-adjusted**
    (split + dividend adjusted = total-return close) for ETFs/stocks, so monthly
    returns are **total returns**. Broad indices (^GSPC, ^DJI, ^IXIC, ^RUT, ^VIX) are
    price-only (no dividends). ^TNX is a **yield level**, not a price -- it is kept in
    `monthly_prices.csv` but excluded from return aggregations.

    ## Universe
    - Asset-class tickers: {len(ASSET_TICKERS)}  (ETFs + broad indices for longest history)
    - Individual stocks: {len(STOCKS)}  (large US caps across {len(STOCK_SECTORS)} GICS sectors)
    - Total series pulled: {len(ALL_TICKERS)}

    ## Files (./output)
    | File | Description |
    |---|---|
    | `monthly_returns_by_ticker.csv` | Long panel: every ticker's monthly return with asset_class/sector labels |
    | `monthly_returns_by_asset_class.csv` | Wide: equal-weighted monthly return per asset class |
    | `monthly_returns_by_sector.csv` | Wide: equal-weighted monthly return per sector (sector ETFs + stocks) |
    | `monthly_returns_by_sector_stocks_only.csv` | Wide: sector return from individual stocks only |
    | `monthly_prices.csv` | Wide: monthly adjusted close per ticker |
    | `universe.csv` | Ticker metadata + first/last month + month count |
    | `coverage_summary.csv` | Per-series coverage + annualized return/vol + monthly min/max |
    | `asset_class_summary.csv` | Asset-class-level coverage + stats |

    ## Coverage (as far back as Yahoo provides, monthly interval)
    Overall date range: **{_fmt(prices.index.min())} -> {_fmt(prices.index.max())}**
    ({len(prices)} months)

    Longest series:
    """
    top10 = cov.sort_values("first_month").head(10)
    for _,r in top10.iterrows():
        readme += f"- {r['ticker']:7s} {r['name'][:42]:42s} {_fmt(r['first_month'])} -> {_fmt(r['last_month'])} ({r['n_months']} mo)\n"

    readme += """
    ## Methodology
    1. Pull monthly history: `yf.download(tickers, period='max', interval='1mo', auto_adjust=True)`.
    2. Monthly return = adjusted close pct_change (month-over-month). Returns indexed to
       month-end timestamps.
    3. Asset-class returns = equal-weighted mean of constituent tickers' monthly returns
       each month (using available tickers). Single stocks and sector ETFs are excluded
       from the asset-class aggregate to avoid double counting; sectors get their own file.
    4. Sector returns = equal-weighted mean across sector ETF + individual stocks in that
       sector. A stocks-only sector file is also produced.

    ## Notes / caveats
    - Yahoo monthly history for indices generally starts 1985; ETFs start at inception.
      Using the longest-history index per asset class maximizes how far back we can go.
    - Total-return vs price-return: ETF/stock returns include dividends; index returns
      (^GSPC etc.) are price-only and will understate total return by the dividend yield.
    - Equal-weighting is used for aggregation (no market-cap weights across ETFs/indexes).
    - Data is for research/illustration; not investment advice.

    ## Reproduce
    ```bash
    .venv/bin/python pull_returns.py
    ```
    """
    with open(os.path.join(OUT,"README.md"),"w") as f:
        f.write(readme)
    print("Wrote README.md")

    print("\n=== DONE ===")
    print("Overall:", _fmt(prices.index.min()), "->", _fmt(prices.index.max()), f"({len(prices)} months)")
    print("Output dir:", OUT)


if __name__ == "__main__":
    main()
