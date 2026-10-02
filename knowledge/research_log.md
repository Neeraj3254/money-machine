# Research Log

## Frozen Hypothesis v1

Signal:

- Return_20D > 0
- SMA_20 > SMA_50
- Close > SMA_200

Holding period:

- 20 trading days

## Tests Completed

### Single-stock baseline
Reliance was tested first.

### Backtest
The strategy produced positive historical returns but underperformed buy-and-hold on total return.

### Transaction-cost stress
Costs materially reduced performance.

### Out-of-sample
The fixed strategy produced positive results in the tested development and OOS periods.

### Parameter robustness
Performance varied substantially across parameter combinations.

### Regime analysis
Performance varied across volatility regimes.

### Multi-stock validation
Tested:

- RELIANCE
- TCS
- INFY
- HDFCBANK
- ICICIBANK

The signal underperformed the unconditional 20-day baseline on all five stocks using overlapping observations.

### Bootstrap test
Four of five stocks had confidence intervals containing zero.

HDFCBANK showed an interval entirely below zero.

### Non-overlapping test
Results became mixed:

- RELIANCE positive
- TCS positive
- INFY negative
- HDFCBANK negative
- ICICIBANK negative

### Distribution analysis
Signal outcomes showed substantial dispersion and small sample sizes.

## Current Research Status

The frozen hypothesis has NOT demonstrated a robust, generalizable edge.

Do not optimize the original parameters merely to improve historical performance.

Next focus:

1. Economic realism
2. Execution assumptions
3. Cost sensitivity
4. Walk-forward stability
5. Better statistical validation
6. New hypotheses only after documenting the failure of v1