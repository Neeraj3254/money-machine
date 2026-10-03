# Experiment V2-001 — Relative Strength

## Status

REGISTERED

## Hypothesis

A stock's return relative to the NIFTY 50 may contain incremental
information beyond the stock's own absolute momentum.

---

# Baseline

The frozen V1 signal is:

Return_20D > 0
AND SMA_20 > SMA_50
AND Close > SMA_200

V1 remains unchanged.

V2-001 must not modify the V1 signal.

---

# New Information

Relative strength:

Stock 20-day return
minus
NIFTY 50 20-day return

Definition:

Relative_Return_20D =
Stock_Return_20D - NIFTY_Return_20D

---

# Proposed V2 Signal

The first experiment will test whether the relative-strength feature
contains incremental predictive information.

The experiment will initially evaluate:

Relative_Return_20D > 0

against:

Relative_Return_20D <= 0

The purpose is diagnostic evaluation first.

It is NOT yet a portfolio trading rule.

---

# Target

Forward 20-trading-day stock return.

---

# Primary Comparison

Compare:

1. Positive relative-strength observations
2. Negative/non-positive relative-strength observations
3. Existing V1 signal
4. Unconditional forward-return baseline

---

# Primary Metrics

- Average forward 20D return
- Median forward 20D return
- Positive-return rate
- Difference versus baseline
- Expectancy
- Sample size

---

# Robustness Tests

If the initial diagnostic is informative, later stages may evaluate:

- cross-stock consistency
- chronological stability
- out-of-sample behavior
- transaction costs
- parameter sensitivity
- regime interaction

These are separate stages.

---

# Leakage Rules

The NIFTY return used by the feature must be known at the signal date.

No future NIFTY prices may enter the feature.

Forward returns are evaluation targets only.

No feature or threshold may use future observations.

---

# Experiment Discipline

Do not optimize the lookback period after seeing the result.

20 days is selected because V1 already uses a 20-day momentum horizon.

Any alternative lookback is a separate experiment.

---

# Failure Conditions

The hypothesis is considered unsupported if:

- relative-strength groups do not differ meaningfully from baseline
- the effect disappears across stocks
- the effect is unstable across time
- the effect depends on a small number of observations
- leakage is discovered
- realistic costs eliminate the effect

---

# Decision Rule

A positive historical result alone does not validate the hypothesis.

The feature must demonstrate incremental and reasonably stable evidence
before becoming a candidate for V2 portfolio construction.

---

# Experiment ID

V2-001

# Hypothesis Family

Cross-sectional / market-relative information

## Final Result

### V2-001 Binary Relative Strength

Relative_Return_20D > 0 was compared against <= 0 using forward 20-day returns.

Result:

- Signal observations: 3,687
- Signal frequency: 48.83%
- Pooled baseline average forward 20D return: +1.2261%
- Positive relative-strength average forward 20D return: +0.8292%
- Incremental return: -0.3969 percentage points
- Positive-rate difference: -3.46 percentage points

The binary positive-relative-strength hypothesis failed the first descriptive gate.

### V2-001 Cross-Sectional Ranking

Stocks were ranked by Relative_Return_20D within each date.

Top 2 stocks were compared against Bottom 2 stocks using forward 20-day returns.

Result:

- Evaluation dates: 1,510
- Top-2 average forward return: +0.9459%
- Bottom-2 average forward return: +1.2058%
- Top-minus-bottom spread: -0.2599%
- Positive spread dates: 47.68%

The observed spread was negative.

### Permutation Test

A date-level cross-sectional permutation test with 10,000 permutations was performed.

- Observed spread: -0.2599%
- Permutation mean: -0.0016%
- Permutation standard deviation: 0.1444%
- 95% null interval: [-0.2811%, +0.2817%]
- Two-sided p-value: 0.0705

The observed spread lies inside the 95% permutation null interval.

Therefore, the experiment does not establish a statistically convincing positive cross-sectional relative-strength effect at the 5% level.

## Final Decision

V2-001 is NOT VALIDATED.

The relative-strength feature may still contain information in particular stocks or regimes, but this experiment does not provide sufficient evidence to convert it into a trading rule.

No trading strategy, position-sizing rule, or regime filter will be created from V2-001.

The hypothesis is frozen in its current form to avoid repeated tuning after observing results.