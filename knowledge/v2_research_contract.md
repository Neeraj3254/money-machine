# V2 Research Contract

## Starting Point

V2 begins after the V1 research checkpoint:

Commit:
b355cf0

V1 is frozen.

V1 must not be modified to improve historical results.

---

# 1. V1 Status

V1 was not validated as a robust general trading edge.

Evidence included:

- benchmark comparison
- stateful backtesting
- transaction-cost sensitivity
- risk metrics
- out-of-sample testing
- parameter robustness
- cross-stock validation
- statistical testing
- walk-forward analysis
- portfolio attribution
- regime attribution
- leakage-free regime analysis
- date-clustered permutation testing
- pooled regime-effect testing

Therefore V1 remains a research baseline.

---

# 2. Regime Engine Status

The leakage-free NIFTY 50 regime engine is retained.

It is NOT currently a validated alpha source.

It must not be converted into a hard trading filter based only on
historical observations from V1.

Future changes to the regime definition constitute new experiments.

---

# 3. V2 Principle

V2 is not:

"Find a better parameter combination for V1."

V2 is:

"Test whether additional information can improve risk-adjusted
decision quality while surviving realistic validation."

---

# 4. Separation of Concerns

V2 experiments must separate:

Data
→ Features
→ Hypothesis
→ Signal
→ Portfolio construction
→ Execution assumptions
→ Costs
→ Risk
→ Evaluation

Changing one layer must not silently change another.

---

# 5. Experiment Control

Every V2 experiment must record:

- Experiment ID
- Hypothesis
- Data source
- Feature definition
- Signal definition
- Portfolio rules
- Execution assumptions
- Transaction costs
- Evaluation period
- Out-of-sample period
- Metrics
- Failure conditions
- Final conclusion

---

# 6. Leakage Control

No future information may influence:

- feature construction
- regime classification
- parameter selection
- signal generation
- position sizing
- model training
- validation decisions

Any leakage discovered invalidates the affected experiment.

---

# 7. Primary Objective

The primary objective is not:

- accuracy
- win rate
- number of profitable trades
- maximum historical return

The research objective is:

Robust risk-adjusted expected value under realistic assumptions.

Important measurements include:

- expectancy
- drawdown
- volatility
- Sharpe
- Calmar
- cost sensitivity
- temporal stability
- cross-sectional stability
- parameter stability
- out-of-sample behavior

---

# 8. Multiple Testing

Trying many hypotheses or parameters increases the probability of
finding apparently successful historical patterns by chance.

Therefore:

- experiments must be registered
- hypotheses must be documented before evaluation where practical
- failed experiments must be preserved
- results must not be selectively reported
- multiple-comparison effects must be considered

---

# 9. V2 Regime Rule

The regime engine may initially be used as:

- contextual information
- diagnostic information
- a feature candidate

It may not become a hard filter until a separately designed experiment
demonstrates robustness.

---

# 10. Human Oversight

No live trading.

No broker execution.

No automatic capital deployment.

Research outputs may eventually produce trade proposals, but a human
remains the final decision-maker.

---

# 11. Research Philosophy

The system should prefer:

Evidence over intuition.

Robustness over optimization.

Risk-adjusted value over raw return.

Out-of-sample evidence over in-sample performance.

Simple explanations over unexplained complexity.

Failure discovery over confirmation seeking.

---

# 12. V2 Gate

A V2 idea should not advance toward deployment merely because it improves
historical return.

It must survive:

1. Leakage audit
2. Cost audit
3. Risk audit
4. Time stability test
5. Out-of-sample test
6. Parameter robustness test
7. Cross-sectional test where applicable
8. Failure-mode analysis

Only then can it become a candidate for further research.