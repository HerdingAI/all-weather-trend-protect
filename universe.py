"""
universe.py -- the ticker universe and the return-series policy.

Side-effect free BY DESIGN. This module exists so that consumers which only
need to know WHAT the tickers are (build_aggregates.py, analysis scripts) do
not have to import pull_returns.py, which configures yfinance and whose job is
to hit the network.

It also gives the equal-weighted aggregation exactly one home. That maths was
previously written twice -- inline in pull_returns.py and again in
build_aggregates.py -- so the two could silently drift apart while both claimed
to produce the same asset-class panel.
"""
from __future__ import annotations

import pandas as pd

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
#   Excluded BY KIND, so a newly added ticker of the same kind is excluded
#   automatically. Listing the tickers by name instead would silently readmit a
#   price-only series the next time one is added -- the exact class of bug this
#   policy exists to prevent.
NON_RETURN_KINDS = {
    "YIELD",    # ^TNX/^FVX/^TYX -- yield levels
    "INDEX",    # ^GSPC/^DJI/^IXIC/^RUT price-only, ^VIX a level
}
# Escape hatch for one-off tickers whose `kind` is otherwise fine. Empty today;
# kept so the policy has a single obvious place to grow.
NON_RETURN_TICKERS: set[str] = set()


def is_return_series(ticker: str, meta: tuple) -> bool:
    """True if this ticker's pct_change is a genuine total return, i.e. it may
    enter an asset-class/sector return aggregate.

    meta[2] is the `kind` for asset tickers and the GICS sector for single
    stocks; single stocks never carry a NON_RETURN_KINDS value, so the same
    test is safe for both tuple schemas.
    """
    return ticker not in NON_RETURN_TICKERS and meta[2] not in NON_RETURN_KINDS


# --------------------------------------------------------------------------- #
# Equal-weighted aggregation (one home for both producers)
# --------------------------------------------------------------------------- #

def aggregatable_groups(meta: dict, available, legacy: bool = False) -> dict:
    """asset_class -> [tickers] eligible for the equal-weighted return aggregate.

    `legacy=True` reproduces the pre-fix rule (yield/price-only levels included),
    which the reproduction gate needs in order to prove we are starting from the
    same inputs that produced the published file.
    """
    available = set(available)
    groups: dict[str, list[str]] = {}
    for ticker, m in meta.items():
        if ticker not in available:
            continue
        asset_class = m[1]
        if asset_class.startswith("Sector-") or asset_class == "Equity (single stock)":
            continue  # single stocks + sector ETFs are aggregated separately
        if not legacy and not is_return_series(ticker, m):
            continue  # yield/price-only levels are not returns
        groups.setdefault(asset_class, []).append(ticker)
    return groups


def equal_weight(wide: pd.DataFrame, groups: dict) -> pd.DataFrame:
    """Time-varying equal-weighted mean per asset class.

    Uses only the constituents with data in a given month, so coverage expands
    as tickers inception over time. A month with no constituent stays NaN.
    """
    out = pd.DataFrame(index=wide.index)
    for ac, tks in groups.items():
        cols = [t for t in tks if t in wide.columns]
        if not cols:
            continue
        out[ac] = wide[cols].mean(axis=1, skipna=True)
    return out.dropna(how="all").sort_index()
