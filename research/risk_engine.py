"""Conservative cash-equity position-risk calculation; never places orders."""
from __future__ import annotations

import math
from typing import Any, Mapping


def evaluate_cash_equity_risk(inputs: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return hypothetical units capped by loss, portfolio exposure, and liquidity.

    All amounts are in one currency. ``max_loss_fraction`` and exposure/ADV
    fractions are explicit caller-supplied fractions in (0, 1].
    """
    if not isinstance(inputs, Mapping):
        return {"status": "INCONCLUSIVE", "reason": "explicit_risk_inputs_required"}
    names = ("capital", "max_loss_fraction", "price", "stop_distance",
             "max_portfolio_exposure_fraction", "average_daily_value", "max_adv_fraction")
    values = {name: inputs.get(name) for name in names}
    portfolio_exposure = inputs.get("portfolio_exposure")
    valid_positive = all(isinstance(value, (int, float)) and not isinstance(value, bool)
                         and math.isfinite(value) and value > 0 for value in values.values())
    valid_exposure = (isinstance(portfolio_exposure, (int, float)) and not isinstance(portfolio_exposure, bool)
                      and math.isfinite(portfolio_exposure) and portfolio_exposure >= 0)
    if (not valid_positive or not valid_exposure or values["max_loss_fraction"] > 1
            or values["max_portfolio_exposure_fraction"] > 1 or values["max_adv_fraction"] > 1):
        return {"status": "INCONCLUSIVE", "reason": "capital_portfolio_exposure_liquidity_price_and_stop_inputs_required"}
    budget = values["capital"] * values["max_loss_fraction"]
    loss_cap_units = math.floor(budget / values["stop_distance"])
    exposure_cap_units = math.floor(max(0, values["capital"] * values["max_portfolio_exposure_fraction"] - portfolio_exposure) / values["price"])
    liquidity_cap_units = math.floor(values["average_daily_value"] * values["max_adv_fraction"] / values["price"])
    units = min(loss_cap_units, exposure_cap_units, liquidity_cap_units)
    return {"status": "PASS" if units > 0 else "FAIL", "risk_budget": budget,
            "max_units": units, "maximum_loss_at_stop": units * values["stop_distance"],
            "portfolio_exposure_cap_units": exposure_cap_units,
            "liquidity_cap_units": liquidity_cap_units, "automatic_execution": False}
