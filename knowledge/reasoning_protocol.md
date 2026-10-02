# Trading Reasoning Protocol

## Purpose

This document defines how the trading system must reason before proposing
a trade.

The system must prefer evidence over intuition and uncertainty over false
confidence.

---

# 1. Establish the Decision

Before reasoning, define:

- Asset
- Market
- Timestamp
- Time horizon
- Available capital
- Maximum acceptable risk
- Intended position type

Never reason about an undefined trade.

---

# 2. Validate the Data

Before using any market information:

Check:

- Data source
- Timestamp
- Missing values
- Duplicate records
- Date ordering
- OHLC consistency
- Price validity
- Volume validity
- Corporate actions
- Data freshness

If data quality is uncertain:

REJECT.

---

# 3. Separate Facts From Assumptions

Every analysis must distinguish:

FACTS:
Observed data.

ASSUMPTIONS:
Things assumed to be true.

HYPOTHESES:
Claims that require testing.

PREDICTIONS:
Expected future outcomes.

Never present assumptions as facts.

---

# 4. Generate Multiple Hypotheses

Do not immediately search for evidence supporting one trade.

Generate competing explanations.

Example:

Hypothesis A:
Price will continue upward.

Hypothesis B:
Price will mean-revert.

Hypothesis C:
The movement is caused by temporary volatility.

Hypothesis D:
There is insufficient evidence.

The system must allow "no trade" to remain a valid outcome.

---

# 5. Identify the Market Regime

Determine whether the market currently resembles:

- Uptrend
- Downtrend
- Range
- High volatility
- Low volatility
- Event-driven market
- Unknown regime

A strategy should only be used when its historical behavior is
compatible with the current regime.

---

# 6. Calculate Features

Features may include:

- Returns
- Moving averages
- Volatility
- ATR
- Volume
- Momentum
- Relative strength
- Correlation
- Z-score
- Market regime variables

Features must be calculated only from information available at the
decision timestamp.

---

# 7. Estimate Expected Value

For a trade:

EV = P(win) × Average Win
     - P(loss) × Average Loss
     - Trading Costs
     - Slippage

Expected value must be estimated from evidence.

A positive EV estimate is not automatically trustworthy.

The probability estimate itself must be validated.

---

# 8. Evaluate Risk

Consider:

- Maximum loss
- Position size
- Volatility
- Drawdown
- Liquidity
- Concentration
- Correlation
- Tail risk
- Gap risk
- Event risk

A profitable-looking trade may still be unacceptable if the downside
is excessive.

---

# 9. Test Historical Evidence

Ask:

- How many historical examples exist?
- What was the win rate?
- What was the average win?
- What was the average loss?
- What was the maximum drawdown?
- What happened during different regimes?
- What happened after transaction costs?

Never rely on a single historical example.

---

# 10. Perform Out-of-Sample Testing

Historical data must be separated into:

TRAINING
VALIDATION
TEST

The final test period must not influence strategy development.

Out-of-sample performance is more important than in-sample performance.

---

# 11. Check for Bias

Before accepting results, check:

- Look-ahead bias
- Survivorship bias
- Selection bias
- Data leakage
- Overfitting
- Multiple-testing bias

If a major bias is detected:

REJECT THE RESULT.

---

# 12. Perform Adversarial Analysis

Ask:

"What would make this trade wrong?"

Search specifically for:

- Contradictory evidence
- Alternative explanations
- Historical failures
- Regime mismatch
- Liquidity problems
- Event risk
- Data problems

The system must attack its own hypothesis.

---

# 13. Estimate Uncertainty

Never output:

"Certain."

Instead communicate:

- Estimated probability
- Evidence quality
- Sample size
- Historical consistency
- Model uncertainty
- Data uncertainty

Confidence must be earned through evidence.

---

# 14. Determine Invalidation Conditions

Every trade must define what would make the thesis invalid.

Examples:

- Price falls below defined level
- Volume behavior changes
- Market regime changes
- Expected catalyst fails
- Data becomes unreliable

A trade without an invalidation condition is incomplete.

---

# 15. Compare Against No Trade

The system must ask:

"Is this opportunity sufficiently better than simply doing nothing?"

If the answer is unclear:

WAIT.

---

# 16. Produce a Trade Proposal

The proposal should contain:

Asset:
Timestamp:
Direction:
Entry:
Stop:
Target:
Position Size:
Risk:
Expected Return:
Expected Value:
Estimated Probability:
Evidence:
Contradictory Evidence:
Invalidation Condition:
Transaction Costs:
Slippage Estimate:
Decision:

Possible decisions:

TRADE
WAIT
REJECT

---

# 17. Human Approval

During development:

The AI must NEVER execute real trades.

The system produces a proposal.

The human decides whether to approve it.

---

# Core Principle

The system does not need to trade.

The system needs to know when NOT to trade.