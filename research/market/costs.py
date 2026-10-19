import pandas as pd


def calculate_portfolio_turnover(
    previous_symbols,
    current_symbols,
):
    """
    Calculate one-way portfolio turnover.

    Assumes equal-weight portfolio.

    Example:
        Previous = {A, B, C}
        Current  = {B, C, D}

        One position is replaced.
    """

    previous_symbols = set(previous_symbols)
    current_symbols = set(current_symbols)

    if not previous_symbols and not current_symbols:
        return 0.0

    if not previous_symbols:
        return 1.0

    if not current_symbols:
        return 1.0

    overlap = len(previous_symbols & current_symbols)
    current_size = len(current_symbols)

    turnover = 1 - (overlap / current_size)

    return turnover


def calculate_transaction_cost(
    turnover,
    cost_per_turnover=0.001,
):
    """
    Convert portfolio turnover into transaction cost.

    0.001 = 0.10% cost.
    """

    if turnover < 0:
        raise ValueError("turnover cannot be negative")

    if cost_per_turnover < 0:
        raise ValueError("cost_per_turnover cannot be negative")

    return turnover * cost_per_turnover


def calculate_net_return(
    gross_return,
    transaction_cost,
):
    """
    Net return after transaction costs.
    """

    return gross_return - transaction_cost