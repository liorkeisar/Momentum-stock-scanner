def dcf_per_share(fcf, growth, terminal_growth, discount_rate, shares, net_debt=0.0, years=5):
    """Discounted cash flow value per share.

    fcf: latest free cash flow (absolute value)
    growth: annual FCF growth for the projection years (e.g. 0.10 for 10%)
    terminal_growth: long-term growth after the projection (e.g. 0.025)
    discount_rate: required return (e.g. 0.09)
    shares: shares outstanding
    net_debt: total debt minus cash (same currency units as fcf)
    Returns (value_per_share, breakdown dict), or (None, {}) if inputs are unusable.
    """
    if not fcf or fcf <= 0 or not shares or shares <= 0:
        return None, {}
    if discount_rate <= terminal_growth:
        raise ValueError("שיעור ההיוון חייב להיות גבוה משיעור הצמיחה לטווח ארוך")

    pv_flows = 0.0
    cf = fcf
    for year in range(1, years + 1):
        cf *= 1 + growth
        pv_flows += cf / (1 + discount_rate) ** year

    terminal_value = cf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** years

    enterprise_value = pv_flows + pv_terminal
    equity_value = enterprise_value - net_debt

    breakdown = {
        "pv_flows": pv_flows,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
    }
    return equity_value / shares, breakdown
