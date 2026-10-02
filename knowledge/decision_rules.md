# Trading Decision Rules

## Purpose

These rules define when the system may propose, reject, or defer a trade.

---

# Rule 1 — Data Integrity

If required data is missing, corrupted, stale, duplicated, or
untrustworthy:

REJECT.

---

# Rule 2 — No Future Information

If the analysis uses information unavailable at the decision timestamp:

REJECT.

---

# Rule 3 — Evidence Required

A trade must have a clearly defined hypothesis supported by measurable
evidence.

No evidence:

REJECT.

---

# Rule 4 — Expected Value

The estimated expected value must account for:

- Probability
- Average win
- Average loss
- Costs
- Slippage

If expected value is not sufficiently positive after costs:

REJECT.

---

# Rule 5 — Risk Limit

Every trade must have:

- Maximum loss
- Position size
- Stop/invalidation condition
- Defined risk

Undefined risk:

REJECT.

---

# Rule 6 — Liquidity

The system must determine whether the desired position can realistically
be entered and exited.

If liquidity is insufficient:

REJECT.

---

# Rule 7 — Regime Compatibility

If the current market regime is inconsistent with the strategy's
historical successful regimes:

REJECT or WAIT.

---

# Rule 8 — Robustness

A strategy must demonstrate reasonable stability across:

- Different time periods
- Different market conditions
- Different parameter values
- Out-of-sample data

Highly fragile strategies should be rejected.

---

# Rule 9 — Contradictory Evidence

If strong evidence contradicts the trade hypothesis:

WAIT or REJECT.

---

# Rule 10 — Confidence

Confidence must be supported by empirical evidence.

High linguistic confidence without empirical evidence is invalid.

---

# Rule 11 — Position Sizing

Position size must depend on:

- Capital
- Risk per trade
- Stop distance
- Volatility
- Liquidity
- Portfolio exposure

Never size a trade only because the model is confident.

---

# Rule 12 — Portfolio Exposure

Before approving a trade, consider existing exposure.

Avoid excessive concentration in:

- One company
- One sector
- One strategy
- One market regime

---

# Rule 13 — Event Risk

If a major known event can materially change the expected outcome,
evaluate the event risk before proposing the trade.

---

# Rule 14 — No Trade Is Valid

The system must be comfortable returning:

WAIT

or

REJECT

There is no requirement to generate a trade every day.

---

# Rule 15 — Human Approval

During development:

AI proposes.

Human approves.

No autonomous real-money execution.

---

# Rule 16 — Logging

Every proposal must be logged with:

- Timestamp
- Data version
- Strategy version
- Features
- Prediction
- Probability
- Entry
- Exit
- Position size
- Risk
- Expected value
- Decision
- Reason
- Invalidation condition

---

# Rule 17 — Post-Trade Evaluation

After a simulated trade:

Compare:

Expected outcome
vs
Actual outcome

Track:

- Prediction error
- Slippage
- Costs
- Profit/loss
- Drawdown
- Calibration
- Strategy performance

---

# Rule 18 — Strategy Shutdown

A strategy should be investigated or suspended when evidence shows
persistent deterioration.

Possible triggers:

- Significant performance degradation
- Unexpected drawdown
- Regime incompatibility
- Data failure
- Model drift
- Calibration failure

---

# Final Decision States

TRADE

Conditions:
- Data valid
- Evidence sufficient
- Expected value acceptable
- Risk acceptable
- Liquidity acceptable
- Strategy compatible with regime
- No critical failure detected

WAIT

Conditions:
- Evidence is incomplete
- Opportunity may improve
- Market state is unclear
- More information is required

REJECT

Conditions:
- Critical data problem
- Negative expected value
- Excessive risk
- Major bias
- Insufficient evidence
- Strategy failure
- Unacceptable liquidity
- Major contradiction

---

# Core Principle

Protect capital first.

Seek positive expected value second.

Trade only when the evidence supports the decision.