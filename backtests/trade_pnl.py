import pandas as pd

INPUT_PATH = "data/processed/reliance_features.csv"

INITIAL_CAPITAL = 100000

print("=" * 60)
print("TRADE-LEVEL P&L ENGINE v0.2")
print("=" * 60)

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

# --------------------------------------------------
# 1. SIGNAL
# --------------------------------------------------

df["Signal"] = (
    (df["Return_20D"] > 0) &
    (df["SMA_20"] > df["SMA_50"]) &
    (df["Close"] > df["SMA_200"])
)

df["Position"] = (
    df["Signal"]
    .shift(1)
    .fillna(False)
    .astype(bool)
)

# --------------------------------------------------
# 2. ENTRY / EXIT EVENTS
# --------------------------------------------------

previous_position = (
    df["Position"]
    .shift(1)
    .fillna(False)
    .astype(bool)
)

entries = (
    df["Position"] &
    ~previous_position
)

exits = (
    ~df["Position"] &
    previous_position
)

# --------------------------------------------------
# 3. BUILD TRADE RECORDS
# --------------------------------------------------

trades = []

entry_date = None
entry_price = None

for date, row in df.iterrows():

    if entries.loc[date]:

        entry_date = date
        entry_price = row["Close"]

    elif exits.loc[date] and entry_date is not None:

        exit_date = date
        exit_price = row["Close"]

        gross_return = (
            exit_price / entry_price
        ) - 1

        trades.append({
            "Entry_Date": entry_date,
            "Exit_Date": exit_date,
            "Entry_Price": entry_price,
            "Exit_Price": exit_price,
            "Gross_Return": gross_return
        })

        entry_date = None
        entry_price = None

# --------------------------------------------------
# 4. DATAFRAME
# --------------------------------------------------

trades = pd.DataFrame(trades)

# --------------------------------------------------
# 5. COMPOUND CAPITAL
# --------------------------------------------------

capital = INITIAL_CAPITAL

capital_after = []

gross_pnl_list = []

for trade_return in trades["Gross_Return"]:

    pnl = capital * trade_return

    capital = capital + pnl

    gross_pnl_list.append(pnl)

    capital_after.append(capital)

trades["Gross_PnL"] = gross_pnl_list

trades["Capital_After_Trade"] = capital_after

# --------------------------------------------------
# 6. SUMMARY
# --------------------------------------------------

print(
    f"\nInitial capital: "
    f"₹{INITIAL_CAPITAL:,.2f}"
)

print(
    f"Completed trades: "
    f"{len(trades)}"
)

if len(trades) > 0:

    wins = (
        trades["Gross_Return"] > 0
    )

    losses = (
        trades["Gross_Return"] < 0
    )

    print(
        f"Winning trades: "
        f"{wins.sum()}"
    )

    print(
        f"Losing trades: "
        f"{losses.sum()}"
    )

    print(
        f"Win rate: "
        f"{wins.mean():.2%}"
    )

    print(
        f"Average trade return: "
        f"{trades['Gross_Return'].mean():.2%}"
    )

    print(
        f"Average gross P&L: "
        f"₹{trades['Gross_PnL'].mean():,.2f}"
    )

    print(
        f"Best trade: "
        f"{trades['Gross_Return'].max():.2%}"
    )

    print(
        f"Worst trade: "
        f"{trades['Gross_Return'].min():.2%}"
    )

    print(
        f"\nFinal compounded capital: "
        f"₹{capital:,.2f}"
    )

    print(
        f"Compounded return: "
        f"{(capital / INITIAL_CAPITAL - 1):.2%}"
    )

    print("\nFirst 10 trades:")

    print(
        trades.head(10)
        .to_string(index=False)
    )

    trades.to_csv(
        "data/processed/momentum_trades.csv",
        index=False
    )

    print(
        "\nSaved to: "
        "data/processed/momentum_trades.csv"
    )

print("\n" + "=" * 60)
print("TRADE-LEVEL P&L COMPLETE")
print("=" * 60)