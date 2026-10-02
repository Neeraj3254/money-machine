import pandas as pd
from pathlib import Path


INPUT_PATH = Path(
    "data/processed/pooled_expectancy.csv"
)

COSTS = [
    0.001,
    0.002,
    0.004,
    0.006,
    0.010
]


df = pd.read_csv(INPUT_PATH)

gross_returns = df["Return"]

print("=" * 70)
print("TRANSACTION COST SENSITIVITY")
print("=" * 70)

results = []

for cost in COSTS:

    net_returns = gross_returns - cost

    winners = net_returns[net_returns > 0]
    losers = net_returns[net_returns < 0]

    win_rate = (
        len(winners) / len(net_returns)
    )

    loss_rate = (
        len(losers) / len(net_returns)
    )

    average_win = (
        winners.mean()
        if len(winners)
        else 0
    )

    average_loss = (
        abs(losers.mean())
        if len(losers)
        else 0
    )

    expectancy = (
        win_rate * average_win
        - loss_rate * average_loss
    )

    profit_factor = (
        winners.sum()
        / abs(losers.sum())
        if len(losers)
        else 0
    )

    results.append({
        "Cost_Per_Trade": cost,
        "Win_Rate": win_rate,
        "Expectancy": expectancy,
        "Profit_Factor": profit_factor
    })


results_df = pd.DataFrame(results)

display_df = results_df.copy()

display_df["Cost_Per_Trade"] *= 100
display_df["Win_Rate"] *= 100
display_df["Expectancy"] *= 100

print(
    display_df.round(3).to_string(index=False)
)

output_path = (
    Path("data/processed")
    / "cost_sensitivity.csv"
)

results_df.to_csv(
    output_path,
    index=False
)

print(f"\nSaved to: {output_path}")

print("\n" + "=" * 70)
print("COST SENSITIVITY COMPLETE")
print("=" * 70)