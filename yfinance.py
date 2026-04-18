# pip install yfinance pandas streamlit supabase plotly
import yfinance as yf
import pandas as pd

# JSE tickers use .JO suffix — your core universe
JSE_TICKERS = [
    "NPN.JO",  # Naspers
    "PRX.JO",  # Prosus
    "BTI.JO",  # British American Tobacco
    "AGL.JO",  # Anglo American
    "SBK.JO",  # Standard Bank
    "FSR.JO",  # FirstRand
    "SOL.JO",  # Sasol
    "MTN.JO",  # MTN Group
    "VOD.JO",  # Vodacom
    "BHP.JO",  # BHP Group
    "IMP.JO",  # Impala Platinum
    "AMS.JO",  # Anglo American Platinum
]

def fetch_jse_data(tickers: list) -> pd.DataFrame:
    rows = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            hist = t.history(period="1y")
            rows.append({
                "ticker": ticker,
                "name": info.get("longName", ticker),
                "price": info.get("currentPrice"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "div_yield": info.get("dividendYield"),
                "market_cap": info.get("marketCap"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "revenue": info.get("totalRevenue"),
                "ebitda": info.get("ebitda"),
                "debt_equity": info.get("debtToEquity"),
                # Momentum: 3m return
                "momentum_3m": (
                    (hist["Close"].iloc[-1] / hist["Close"].iloc[-63] - 1) * 100
                    if len(hist) >= 63 else None
                ),
            })
        except Exception as e:
            print(f"Failed {ticker}: {e}")
    return pd.DataFrame(rows)

if __name__ == "__main__":
    df = fetch_jse_data(JSE_TICKERS)
    df.to_csv("jse_snapshot.csv", index=False)
    print(df[["ticker", "price", "pe_ratio", "momentum_3m"]].head(12))