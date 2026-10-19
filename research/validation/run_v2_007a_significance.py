from research.market.panel import (
    build_research_panel,
    filter_available_market_data,
)

from research.market.features import add_price_features
from research.market.market_context import attach_market_context

from research.market.cross_sectional import (
    build_cross_sectional_dataset,
    add_next_session_return,
    assign_momentum_quantiles,
)

from research.validation.baseline import (
    prepare_v2_007a_dataset,
    calculate_v2_007a_baseline,
)

from research.validation.significance import (
    permutation_test_mean_spread,
    bootstrap_mean_spread,
    summarize_significance,
)


print("=== BUILDING V2-007A DATASET ===")


panel = build_research_panel(
    "2026-01-01",
    "2026-10-01",
)

panel = filter_available_market_data(panel)

features = add_price_features(panel)

features = attach_market_context(features)

research = build_cross_sectional_dataset(features)

research = add_next_session_return(research)

research = assign_momentum_quantiles(research)


valid = prepare_v2_007a_dataset(research)

print("Eligible observations:", len(valid))
print(
    "Dates:",
    valid["TRADE_DATE"].nunique(),
)
print(
    "Securities:",
    valid["ISIN"].nunique(),
)


print()
print("=== CALCULATING V2-007A BASELINE ===")


baseline = calculate_v2_007a_baseline(valid)

print(baseline)


print()
print("=== PERMUTATION TEST ===")


permutation = permutation_test_mean_spread(
    baseline,
    spread_col="Q1_MINUS_Q5",
    n_permutations=10_000,
    random_state=42,
)

for key, value in permutation.items():
    print(f"{key}: {value}")


print()
print("=== BOOTSTRAP ===")


bootstrap = bootstrap_mean_spread(
    baseline,
    spread_col="Q1_MINUS_Q5",
    n_bootstrap=10_000,
    random_state=42,
)

for key, value in bootstrap.items():
    print(f"{key}: {value}")


print()
print("=== SIGNIFICANCE SUMMARY ===")


summary = summarize_significance(
    permutation,
    bootstrap,
)

for key, value in summary.items():
    print(f"{key}: {value}")