import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = BASE_DIR / "data" / "processed" / "reliance_features.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "stateful_trades.csv"

HOLDING_DAYS = 20


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(DATA_FILE, parse_dates=["Date"])

df = df.sort_values("Date").reset_index(drop=True)


# ============================================================
# V1 SIGNAL
# ============================================================

df["Signal"] = (
    (df["Return_20D"] > 0)
    & (df["SMA_20"] > df["SMA_50"])
    & (df["Close"] > df["SMA_200"])
)


# ============================================================
# STATEFUL TRADE SIMULATION
# ============================================================

trades = []

i = 0
trade_id = 1

while i < len(df) - HOLDING_DAYS - 1:

    # --------------------------------------------------------
    # FLAT STATE
    # --------------------------------------------------------

    if not df.loc[i, "Signal"]:
        i += 1
        continue

    # --------------------------------------------------------
    # ENTER ON NEXT TRADING DAY OPEN
    # --------------------------------------------------------

    entry_idx = i + 1

    if entry_idx >= len(df):
        break

    entry_date = df.loc[entry_idx, "Date"]
    entry_price = df.loc[entry_idx, "Open"]

    # --------------------------------------------------------
    # EXIT AFTER HOLDING PERIOD
    # --------------------------------------------------------

    exit_idx = entry_idx + HOLDING_DAYS

    if exit_idx >= len(df):
        break

    exit_date = df.loc[exit_idx, "Date"]
    exit_price = df.loc[exit_idx, "Open"]

    # --------------------------------------------------------
    # TRADE RETURN
    # --------------------------------------------------------

    trade_return = (exit_price / entry_price) - 1

    trades.append(
        {
            "Trade_ID": trade_id,
            "Signal_Date": df.loc[i, "Date"],
            "Entry_Date": entry_date,
            "Entry_Price": entry_price,
            "Exit_Date": exit_date,
            "Exit_Price": exit_price,
            "Holding_Days": HOLDING_DAYS,
            "Return": trade_return,
            "Win": trade_return > 0,
        }
    )

    trade_id += 1

    # --------------------------------------------------------
    # IMPORTANT:
    # JUMP TO EXIT
    #
    # This prevents overlapping trades.
    # --------------------------------------------------------

    i = exit_idx


# ============================================================
# CREATE TRADE DATAFRAME
# ============================================================

trades_df = pd.DataFrame(trades)


# ============================================================
# SAVE RESULTS
# ============================================================

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

trades_df.to_csv(OUTPUT_FILE, index=False)


# ============================================================
# SUMMARY
# ============================================================

print("=" * 60)
print("STATEFUL BACKTEST")
print("=" * 60)

print(f"Total trades: {len(trades_df)}")

if len(trades_df) > 0:

    win_rate = trades_df["Win"].mean()

    avg_return = trades_df["Return"].mean()

    median_return = trades_df["Return"].median()

    print(f"Win rate: {win_rate:.2%}")
    print(f"Average trade return: {avg_return:.2%}")
    print(f"Median trade return: {median_return:.2%}")

    print(
        f"Best trade: "
        f"{trades_df['Return'].max():.2%}"
    )

    print(
        f"Worst trade: "
        f"{trades_df['Return'].min():.2%}"
    )

print()
print(f"Saved: {OUTPUT_FILE}")