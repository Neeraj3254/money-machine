# Confidence Protocol

## Purpose

Confidence must represent evidence quality and empirical reliability,
not how convincing the language sounds.

---

# 1. Confidence Is Not Certainty

The system must never claim:

- Guaranteed profit
- Certain prediction
- Zero-risk trade
- Perfect accuracy

All market predictions are uncertain.

---

# 2. Sources of Confidence

Confidence may depend on:

1. Historical evidence
2. Sample size
3. Out-of-sample performance
4. Model calibration
5. Regime compatibility
6. Data quality
7. Strategy robustness
8. Agreement between independent models
9. Cost-adjusted performance
10. Contradictory evidence

---

# 3. Probability Must Be Empirical

If a model predicts:

80% probability of success

then, across many comparable predictions, approximately 80% should
succeed if the model is well calibrated.

The number must be tested.

---

# 4. Sample Size Matters

Example:

Model A:

8 successful predictions out of 10.

Observed accuracy = 80%.

This is weak evidence because the sample is small.

Model B:

800 successful predictions out of 1000.

Observed accuracy = 80%.

This provides substantially more evidence, although other problems may
still exist.

---

# 5. Confidence Reduction Factors

Reduce confidence when:

- Sample size is small
- Data quality is uncertain
- Market regime is unusual
- Historical evidence is weak
- Out-of-sample results are poor
- Transaction costs eliminate the edge
- Slippage is significant
- Contradictory evidence exists
- Strategy parameters are unstable
- Model drift is detected

---

# 6. Confidence Must Be Calibrated

Track:

Predicted probability
vs
Actual outcome

Example:

Predicted probability:

0.80

Actual long-run success:

0.60

The model is overconfident.

The system must learn from this difference.

---

# 7. Independent Evidence

Confidence should increase when independent sources support the same
hypothesis.

Example:

Price momentum
+
Volume confirmation
+
Market regime confirmation

is stronger evidence than repeatedly measuring the same momentum signal.

Correlation between signals must be considered.

---

# 8. Contradictory Evidence

The system must actively search for evidence against its prediction.

Example:

Positive momentum
BUT

- Market volatility is extreme
- Volume is declining
- Sector is weakening

Confidence should decrease.

---

# 9. Confidence Output

Every prediction should report:

Estimated Probability:
Evidence Strength:
Sample Size:
Out-of-Sample Evidence:
Calibration Evidence:
Contradictory Evidence:
Data Quality:
Uncertainty:

---

# 10. Confidence Categories

Use these only as descriptive internal categories:

HIGH EVIDENCE
MEDIUM EVIDENCE
LOW EVIDENCE
INSUFFICIENT EVIDENCE

These are evidence classifications, not guarantees of outcome.

---

# Core Rule

Confidence must come from measured evidence.

Confidence language must never substitute for evidence.