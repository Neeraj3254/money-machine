# V1 Research Report

## Hypothesis

The strategy enters when:

- 20-day return is positive
- SMA20 > SMA50
- Close > SMA200

Holding period:

20 trading days.

## Universe

- RELIANCE
- TCS
- INFY
- HDFCBANK
- ICICIBANK

## Evidence

### Backtest

Historical performance was positive but did not beat the buy-and-hold benchmark on total return.

### Out-of-sample

The fixed strategy remained positive in the tested OOS period, but this does not establish future validity.

### Parameter robustness

Performance varied substantially across parameter combinations.

This creates overfitting risk.

### Cross-stock validation

The signal underperformed the unconditional 20-day baseline across all five stocks in the initial overlapping evaluation.

### Bootstrap

Four of five stocks had confidence intervals containing zero.

### Non-overlapping evaluation

Results became mixed across stocks.

### Distribution

Signal outcomes showed substantial dispersion.

Some positive means were above their medians, indicating that a relatively small number of large observations may influence averages.

### Expectancy

Pooled non-overlapping expectancy was positive before costs.

### Costs

Modeled costs progressively reduced expectancy.

### Execution

Using next-open execution changed the observed results materially.

### Walk-forward

Performance varied substantially across chronological periods.

### Market regimes

Strategy behavior varies across market regimes.

However, some individual stock/regime combinations have very small samples and should not be treated as reliable evidence.

## Final Status

V1 is NOT validated as a robust generalizable trading edge.

## Decision

Do not deploy V1 for live trading.

Use V1 as:

1. A baseline.
2. A research failure case.
3. A benchmark against future hypotheses.
4. A test of the research infrastructure.

## Next Phase

Build V2 hypotheses from economic reasoning rather than parameter optimization.

Potential research directions:

- trend strength
- volatility-adjusted momentum
- market regime filters
- relative strength
- volume confirmation
- mean-reversion hypotheses
- cross-sectional ranking

Every V2 hypothesis must be independently tested and documented.