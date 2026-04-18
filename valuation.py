# valuation.py — your edge over Yahoo Finance
def simple_dcf(
    current_fcf: float,
    growth_rate: float = 0.08,
    discount_rate: float = 0.15,  # SA WACC typically higher
    terminal_growth: float = 0.04,
    years: int = 5
) -> dict:
    """
    SA-calibrated DCF. Uses higher discount rate for emerging market risk.
    This is JSE-specific logic that generic tools don't have.
    """
    projected_fcfs = [
        current_fcf * (1 + growth_rate) ** i
        for i in range(1, years + 1)
    ]
    
    # Terminal value (Gordon Growth Model)
    terminal_value = (
        projected_fcfs[-1] * (1 + terminal_growth)
    ) / (discount_rate - terminal_growth)
    
    # Discount everything back
    pv_fcfs = sum(
        fcf / (1 + discount_rate) ** i
        for i, fcf in enumerate(projected_fcfs, 1)
    )
    pv_terminal = terminal_value / (1 + discount_rate) ** years
    
    intrinsic_value = pv_fcfs + pv_terminal
    
    return {
        "intrinsic_value": round(intrinsic_value, 0),
        "pv_cash_flows": round(pv_fcfs, 0),
        "pv_terminal": round(pv_terminal, 0),
        "projected_fcfs": [round(f, 0) for f in projected_fcfs],
        "terminal_value": round(terminal_value, 0),
    }