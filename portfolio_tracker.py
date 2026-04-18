# portfolio_tracker.py
def render_portfolio_tracker():
    st.subheader("📁 My JSE Portfolio")
    st.info("Your holdings are stored locally — never shared.")
    
    # Simple session-state portfolio for MVP
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = {}
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.selectbox("Add stock", JSE_TICKERS)
    with col2:
        shares = st.number_input("Shares", min_value=1, value=100)
    with col3:
        avg_cost = st.number_input("Avg cost (ZAR)", min_value=0.0, value=100.0)
    
    if st.button("Add to Portfolio"):
        st.session_state.portfolio[ticker] = {
            "shares": shares,
            "avg_cost": avg_cost
        }
    
    if st.session_state.portfolio:
        portfolio_data = []
        for t, pos in st.session_state.portfolio.items():
            current_price = yf.Ticker(t).info.get("currentPrice", 0)
            value = pos["shares"] * current_price
            cost = pos["shares"] * pos["avg_cost"]
            pnl = value - cost
            
            portfolio_data.append({
                "Ticker": t,
                "Shares": pos["shares"],
                "Avg Cost": f"R{pos['avg_cost']:.2f}",
                "Current": f"R{current_price:.2f}",
                "Value": f"R{value:,.0f}",
                "P&L": f"R{pnl:+,.0f}",
                "Return": f"{(pnl/cost)*100:+.1f}%"
            })
        
        st.dataframe(pd.DataFrame(portfolio_data), use_container_width=True)