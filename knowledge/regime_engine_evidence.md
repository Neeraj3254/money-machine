# Regime Engine Evidence — V1

## Purpose

Evaluate whether a leakage-free NIFTY 50 market-regime classification
provides a robust conditional edge for the existing V1 portfolio strategy.

The regime engine is descriptive research infrastructure.

It is NOT currently a trading filter.

---

# 1. Regime Construction

Market regimes are based on:

- 20-day NIFTY 50 volatility
- 60-day NIFTY 50 return

Regimes:

- LOW_VOL_UP
- LOW_VOL_DOWN
- MED_VOL_UP
- MED_VOL_DOWN
- HIGH_VOL_UP
- HIGH_VOL_DOWN

The leakage-free engine requires 252 historical volatility observations
before producing a valid regime.

Thresholds are based only on historical information available at the
time of classification.

First valid regime date:

2020-02-13

---

# 2. Portfolio Sample

Original stateful portfolio trades:

184

Trades before regime engine became valid:

13

Valid regime-attributed trades:

171

Unique entry dates:

154

Transaction-cost assumption:

0.10% per side

The analysis uses the existing V1 strategy without changing its signal,
parameters, holding period, or position-sizing logic.

---

# 3. Time Stability

Leakage-free regime × time analysis showed substantial variation.

Examples:

MED_VOL_UP average return:

2020–2021: +3.04%
2022–2023: +0.37%
2024–2025: +2.15%

LOW_VOL_UP:

2020–2021: +1.09%
2022–2023: -0.74%
2024–2025: -0.73%

HIGH_VOL_UP:

2020–2021: +3.55%
2022–2023: -4.65%
2024–2025: +4.79%

Therefore regime-conditioned performance is time-dependent.

---

# 4. Same-Period Regime Effects

Definition:

Regime Effect =
Regime Average Return
-
Same-Period Other-Regime Average Return

Examples:

2024–2025 HIGH_VOL_UP:

+4.68 percentage points

2024–2025 LOW_VOL_UP:

-3.35 percentage points

2022–2023 LOW_VOL_UP:

+2.55 percentage points

These effects are descriptive observations.

They are not treated as validated edges.

---

# 5. Date-Clustered Permutation Test

Randomization unit:

Entry_Date

All portfolio trades occurring on the same entry date remain together.

10,000 permutations were used for each period × regime combination.

Some unadjusted p-values were relatively small, including:

2024–2025 HIGH_VOL_UP:
p = 0.0245

2024–2025 LOW_VOL_UP:
p = 0.0372

However, 17 period × regime comparisons were examined.

After multiple-comparison control, these results do not provide robust
evidence of a regime effect.

---

# 6. Pooled Leakage-Free Test

Valid trades:

171

Unique entry dates:

154

Regimes tested:

6

10,000 permutations per regime.

Results:

HIGH_VOL_DOWN:
Effect = +0.79%
Raw p = 0.7069
Adjusted p = 1.0000

HIGH_VOL_UP:
Effect = +2.97%
Raw p = 0.0535
Adjusted p = 0.3210

LOW_VOL_DOWN:
Effect = -2.10%
Raw p = 0.3630
Adjusted p = 1.0000

LOW_VOL_UP:
Effect = -1.97%
Raw p = 0.0752
Adjusted p = 0.4512

MED_VOL_DOWN:
Effect = -3.06%
Raw p = 0.1954
Adjusted p = 1.0000

MED_VOL_UP:
Effect = +2.09%
Raw p = 0.1206
Adjusted p = 0.7235

No regime survives the multiple-comparison control.

---

# 7. Research Decision

STATUS:

REGIME EDGE NOT VALIDATED

The regime engine is retained as research infrastructure.

It must NOT currently be used as:

- a hard entry filter
- a hard exit filter
- a position-sizing rule
- a parameter-selection mechanism
- evidence that V1 has a validated regime-dependent edge

If regime information is used in future V2 research, it should initially
be treated as an explanatory/contextual feature and tested prospectively
without optimizing the existing strategy around these historical results.

---

# 8. Important Research Constraint

Do not revisit the regime definitions merely because the results are
not statistically strong.

Any future change to:

- volatility lookback
- return lookback
- regime thresholds
- number of regimes

must be treated as a NEW experiment.

It must receive a new experiment ID and independent validation.

---

# 9. Current Conclusion

The leakage-free regime engine successfully provides historical market
context.

However:

NO ROBUST REGIME EDGE HAS BEEN ESTABLISHED FOR V1.

The regime engine remains useful as:

- research context
- diagnostic information
- future feature candidate
- future prospective evaluation input

It is not currently a validated source of alpha.