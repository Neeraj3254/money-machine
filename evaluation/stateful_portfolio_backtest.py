import argparse
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "portfolio_signals.csv"
)

INITIAL_CAPITAL = 100_000.0

HOLDING_DAYS = 20

MAX_POSITION_WEIGHT = 0.30

MAX_TOTAL_EXPOSURE = 1.00


# ============================================================
# COMMAND-LINE CONFIGURATION
# ============================================================

parser = argparse.ArgumentParser(
    description="Stateful portfolio backtest with transaction costs."
)

parser.add_argument(
    "--cost",
    type=float,
    default=0.0,
    help=(
        "Transaction cost per side as a decimal. "
        "Example: 0.001 = 0.1%% per side."
    ),
)

args = parser.parse_args()

TRANSACTION_COST_PER_SIDE = args.cost


# ============================================================
# VALIDATE COST
# ============================================================

if TRANSACTION_COST_PER_SIDE < 0:
    raise ValueError(
        "Transaction cost cannot be negative."
    )

if TRANSACTION_COST_PER_SIDE >= 1:
    raise ValueError(
        "Transaction cost must be less than 1. "
        "Example: use 0.001 for 0.1%%."
    )


# ============================================================
# OUTPUT FILES
# ============================================================

COST_TAG = (
    f"{TRANSACTION_COST_PER_SIDE:.4f}"
    .replace(".", "_")
)

TRADES_OUTPUT = (
    BASE_DIR
    / "data"
    / "processed"
    / f"stateful_portfolio_trades_cost_{COST_TAG}.csv"
)

EQUITY_OUTPUT = (
    BASE_DIR
    / "data"
    / "processed"
    / f"stateful_portfolio_equity_cost_{COST_TAG}.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file not found:\n{INPUT_FILE}"
    )


df = pd.read_csv(
    INPUT_FILE,
    parse_dates=["Date"],
)


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

required_columns = {
    "Date",
    "Stock",
    "Open",
    "Close",
    "Signal",
}

missing_columns = (
    required_columns
    - set(df.columns)
)

if missing_columns:
    raise ValueError(
        "Missing required columns: "
        f"{sorted(missing_columns)}"
    )


# ============================================================
# CLEAN AND SORT DATA
# ============================================================

df = (
    df
    .dropna(
        subset=[
            "Date",
            "Stock",
            "Open",
            "Close",
        ]
    )
    .sort_values(
        ["Stock", "Date"]
    )
    .reset_index(drop=True)
)


# ============================================================
# NORMALIZE SIGNAL
# ============================================================

if df["Signal"].dtype != bool:

    df["Signal"] = (
        df["Signal"]
        .astype(str)
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
        .fillna(False)
    )


# ============================================================
# BASIC DATA VALIDATION
# ============================================================

if (df["Open"] <= 0).any():
    raise ValueError(
        "Invalid non-positive Open price detected."
    )

if (df["Close"] <= 0).any():
    raise ValueError(
        "Invalid non-positive Close price detected."
    )


duplicate_rows = df.duplicated(
    subset=["Stock", "Date"]
).sum()

if duplicate_rows > 0:
    raise ValueError(
        f"Found {duplicate_rows} duplicate "
        "Stock/Date rows."
    )


# ============================================================
# CREATE ENTRY / EXIT DATES
# ============================================================

# Signal is generated using today's information.
#
# We therefore enter on the NEXT trading day's Open.
#
# If:
#
# Signal = Day 0
# Entry  = Day 1
#
# and we want to hold for 20 trading sessions,
# the exit occurs on Day 21.
#
# Therefore:
#
# Entry_Date = shift(-1)
# Exit_Date  = shift(-(HOLDING_DAYS + 1))
# ============================================================

df["Entry_Date"] = (
    df
    .groupby("Stock")["Date"]
    .shift(-1)
)

df["Exit_Date"] = (
    df
    .groupby("Stock")["Date"]
    .shift(-(HOLDING_DAYS + 1))
)


# ============================================================
# PRICE LOOKUP TABLE
# ============================================================

price_data = (
    df[
        [
            "Stock",
            "Date",
            "Open",
            "Close",
        ]
    ]
    .set_index(
        ["Stock", "Date"]
    )
    .sort_index()
)


def get_price(
    stock,
    current_date,
    column,
):
    """
    Return a price for a specific stock/date.

    Returns None when the requested
    stock/date combination does not exist.
    """

    key = (
        stock,
        pd.Timestamp(current_date),
    )

    if key not in price_data.index:
        return None

    value = price_data.loc[
        key,
        column,
    ]

    return float(value)


# ============================================================
# PORTFOLIO STATE
# ============================================================

cash = float(INITIAL_CAPITAL)

active_positions = []

pending_entries = []

completed_trades = []

equity_records = []


# ============================================================
# TRADING DATES
# ============================================================

dates = sorted(
    df["Date"]
    .dropna()
    .unique()
)


# ============================================================
# MAIN BACKTEST LOOP
# ============================================================

for current_date in dates:

    current_date = pd.Timestamp(
        current_date
    )

    # ========================================================
    # 1. EXIT POSITIONS AT TODAY'S OPEN
    # ========================================================

    remaining_positions = []

    for position in active_positions:

        # Position is not ready to exit.
        if current_date != position["Exit_Date"]:

            remaining_positions.append(
                position
            )

            continue

        stock = position["Stock"]

        exit_price = get_price(
            stock,
            current_date,
            "Open",
        )

        # If exit price is unavailable,
        # keep the position alive.
        if exit_price is None:

            remaining_positions.append(
                position
            )

            continue

        # ----------------------------------------------------
        # GROSS EXIT VALUE
        # ----------------------------------------------------

        gross_exit_value = (
            position["Shares"]
            * exit_price
        )

        # ----------------------------------------------------
        # EXIT TRANSACTION COST
        # ----------------------------------------------------

        exit_cost = (
            gross_exit_value
            * TRANSACTION_COST_PER_SIDE
        )

        # ----------------------------------------------------
        # NET CASH RECEIVED
        # ----------------------------------------------------

        net_exit_value = (
            gross_exit_value
            - exit_cost
        )

        cash += net_exit_value

        # ----------------------------------------------------
        # TRADE P&L
        # ----------------------------------------------------

        gross_pnl = (
            gross_exit_value
            - position["Capital"]
        )

        net_pnl = (
            gross_pnl
            - position["Entry_Cost"]
            - exit_cost
        )

        if position["Capital"] > 0:

            net_return = (
                net_pnl
                / position["Capital"]
            )

        else:

            net_return = 0.0

        # ----------------------------------------------------
        # RECORD COMPLETED TRADE
        # ----------------------------------------------------

        completed_trades.append(
            {
                "Stock": stock,

                "Signal_Date": (
                    position["Signal_Date"]
                ),

                "Entry_Date": (
                    position["Entry_Date"]
                ),

                "Exit_Date": current_date,

                "Entry_Price": (
                    position["Entry_Price"]
                ),

                "Exit_Price": exit_price,

                "Capital": (
                    position["Capital"]
                ),

                "Shares": (
                    position["Shares"]
                ),

                "Entry_Cost": (
                    position["Entry_Cost"]
                ),

                "Exit_Cost": exit_cost,

                "Entry_Portfolio_Equity": (
                    position[
                        "Entry_Portfolio_Equity"
                    ]
                ),

                "Target_Weight": (
                    position["Target_Weight"]
                ),

                "Entry_Weight": (
                    position["Entry_Weight"]
                ),

                "Return": net_return,

                "PnL": net_pnl,
            }
        )

    # Replace active positions
    # with positions that remain open.
    active_positions = remaining_positions


    # ========================================================
    # 2. EXECUTE PENDING ENTRIES AT TODAY'S OPEN
    # ========================================================

    todays_entries = [
        entry
        for entry in pending_entries
        if entry["Entry_Date"] == current_date
    ]

    pending_entries = [
        entry
        for entry in pending_entries
        if entry["Entry_Date"] != current_date
    ]


    if todays_entries:

        # ----------------------------------------------------
        # VALUE CURRENT OPEN POSITIONS
        # ----------------------------------------------------

        open_position_value = 0.0

        for position in active_positions:

            open_price = get_price(
                position["Stock"],
                current_date,
                "Open",
            )

            if open_price is not None:

                open_position_value += (
                    position["Shares"]
                    * open_price
                )


        # ----------------------------------------------------
        # PORTFOLIO EQUITY AT OPEN
        # ----------------------------------------------------

        equity_at_open = (
            cash
            + open_position_value
        )


        # ----------------------------------------------------
        # CURRENT EXPOSURE
        # ----------------------------------------------------

        if equity_at_open > 0:

            current_exposure = (
                open_position_value
                / equity_at_open
            )

        else:

            current_exposure = 0.0


        # ----------------------------------------------------
        # REMAINING PORTFOLIO CAPACITY
        # ----------------------------------------------------

        remaining_exposure = max(
            0.0,
            MAX_TOTAL_EXPOSURE
            - current_exposure,
        )


        # ----------------------------------------------------
        # STOCKS ALREADY HELD
        # ----------------------------------------------------

        held_stocks = {
            position["Stock"]
            for position in active_positions
        }


        # ----------------------------------------------------
        # REMOVE DUPLICATE SAME-STOCK ENTRIES
        # ----------------------------------------------------

        eligible_entries = []

        seen_stocks = set()

        for entry in todays_entries:

            stock = entry["Stock"]

            if stock in held_stocks:
                continue

            if stock in seen_stocks:
                continue

            seen_stocks.add(stock)

            eligible_entries.append(
                entry
            )


        # ====================================================
        # ALLOCATION
        # ====================================================

        if eligible_entries:

            number_of_entries = len(
                eligible_entries
            )


            # ------------------------------------------------
            # EQUAL TARGET WEIGHT
            # ------------------------------------------------
            #
            # Example:
            #
            # 5 signals:
            #     100% / 5 = 20% each
            #
            # 2 signals:
            #     100% / 2 = 50%
            #
            # But maximum per stock = 30%.
            #
            # Therefore:
            #
            # 2 signals -> 30% each
            # 5 signals -> 20% each
            #
            # ------------------------------------------------

            if number_of_entries > 0:

                target_weight = min(
                    MAX_POSITION_WEIGHT,
                    remaining_exposure
                    / number_of_entries,
                )

            else:

                target_weight = 0.0


            # ------------------------------------------------
            # REQUESTED CAPITAL
            # ------------------------------------------------

            requested_capital = (
                equity_at_open
                * target_weight
            )


            # ------------------------------------------------
            # TOTAL CAPITAL REQUESTED
            # ------------------------------------------------

            total_requested = (
                requested_capital
                * number_of_entries
            )


            # ------------------------------------------------
            # TOTAL CASH REQUIRED
            # ------------------------------------------------
            #
            # Important:
            #
            # If capital = ₹20,000
            # and cost = 0.1%,
            #
            # cash required =
            #
            # ₹20,000 + ₹20
            #
            # = ₹20,020
            #
            # We therefore scale using the FULL
            # cash requirement including costs.
            # ------------------------------------------------

            total_cash_required = (
                total_requested
                * (
                    1.0
                    + TRANSACTION_COST_PER_SIDE
                )
            )


            # ------------------------------------------------
            # SCALE IF CASH IS INSUFFICIENT
            # ------------------------------------------------

            if total_cash_required > cash:

                if total_cash_required > 0:

                    scale_factor = (
                        cash
                        / total_cash_required
                    )

                else:

                    scale_factor = 0.0

            else:

                scale_factor = 1.0


            # ------------------------------------------------
            # CREATE ALL ENTRIES AS ONE BATCH
            # ------------------------------------------------

            for entry in eligible_entries:

                stock = entry["Stock"]

                entry_price = get_price(
                    stock,
                    current_date,
                    "Open",
                )

                if (
                    entry_price is None
                    or entry_price <= 0
                ):
                    continue


                # ------------------------------------------------
                # FINAL CAPITAL ALLOCATION
                # ------------------------------------------------

                capital = (
                    requested_capital
                    * scale_factor
                )


                if capital <= 0:
                    continue


                # ------------------------------------------------
                # ENTRY TRANSACTION COST
                # ------------------------------------------------

                entry_cost = (
                    capital
                    * TRANSACTION_COST_PER_SIDE
                )


                # ------------------------------------------------
                # TOTAL CASH NEEDED
                # ------------------------------------------------

                cash_required = (
                    capital
                    + entry_cost
                )


                # ------------------------------------------------
                # FINAL SAFETY CHECK
                # ------------------------------------------------

                if cash_required > cash + 1e-9:

                    continue


                # ------------------------------------------------
                # NUMBER OF SHARES
                # ------------------------------------------------

                shares = (
                    capital
                    / entry_price
                )


                if shares <= 0:
                    continue


                # ------------------------------------------------
                # PAY FOR POSITION
                # ------------------------------------------------

                cash -= cash_required


                # ------------------------------------------------
                # ACTIVATE POSITION
                # ------------------------------------------------

                active_positions.append(
                    {
                        "Stock": stock,

                        "Signal_Date": (
                            entry["Signal_Date"]
                        ),

                        "Entry_Date": current_date,

                        "Entry_Price": (
                            entry_price
                        ),

                        "Exit_Date": (
                            entry["Exit_Date"]
                        ),

                        "Capital": capital,

                        "Shares": shares,

                        "Entry_Cost": entry_cost,

                        "Entry_Portfolio_Equity": (
                            equity_at_open
                        ),

                        "Target_Weight": (
                            target_weight
                        ),

                        "Entry_Weight": (
                            capital
                            / equity_at_open
                            if equity_at_open > 0
                            else 0.0
                        ),
                    }
                )


    # ========================================================
    # 3. MARK ACTIVE POSITIONS TO MARKET
    # ========================================================

    market_value = 0.0

    for position in active_positions:

        close_price = get_price(
            position["Stock"],
            current_date,
            "Close",
        )

        if close_price is None:
            continue

        market_value += (
            position["Shares"]
            * close_price
        )


    # ========================================================
    # 4. DAILY PORTFOLIO EQUITY
    # ========================================================

    portfolio_equity = (
        cash
        + market_value
    )


    if portfolio_equity > 0:

        exposure = (
            market_value
            / portfolio_equity
        )

    else:

        exposure = 0.0


    equity_records.append(
        {
            "Date": current_date,

            "Cash": cash,

            "Market_Value": market_value,

            "Portfolio_Equity": (
                portfolio_equity
            ),

            "Exposure": exposure,

            "Active_Positions": len(
                active_positions
            ),
        }
    )


    # ========================================================
    # 5. SCHEDULE TODAY'S SIGNALS
    # ========================================================
    #
    # The signal is known at today's close.
    #
    # We therefore DO NOT enter today.
    #
    # Entry happens tomorrow's Open.
    # ========================================================

    todays_signals = df[
        (df["Date"] == current_date)
        & (df["Signal"] == True)
    ]


    held_stocks = {
        position["Stock"]
        for position in active_positions
    }


    pending_stocks = {
        entry["Stock"]
        for entry in pending_entries
    }


    for _, signal in todays_signals.iterrows():

        stock = signal["Stock"]

        entry_date = signal["Entry_Date"]

        exit_date = signal["Exit_Date"]


        # ----------------------------------------------------
        # ENTRY DATE MUST EXIST
        # ----------------------------------------------------

        if pd.isna(entry_date):
            continue


        # ----------------------------------------------------
        # EXIT DATE MUST EXIST
        # ----------------------------------------------------

        if pd.isna(exit_date):
            continue


        # ----------------------------------------------------
        # DO NOT CREATE SAME-STOCK OVERLAP
        # ----------------------------------------------------

        if stock in held_stocks:
            continue


        if stock in pending_stocks:
            continue


        # ----------------------------------------------------
        # SCHEDULE ENTRY
        # ----------------------------------------------------

        pending_entries.append(
            {
                "Stock": stock,

                "Signal_Date": current_date,

                "Entry_Date": pd.Timestamp(
                    entry_date
                ),

                "Exit_Date": pd.Timestamp(
                    exit_date
                ),
            }
        )


        pending_stocks.add(stock)


# ============================================================
# CREATE OUTPUT DATAFRAMES
# ============================================================

trades = pd.DataFrame(
    completed_trades
)

equity_curve = pd.DataFrame(
    equity_records
)


if equity_curve.empty:

    raise SystemExit(
        "No equity records were generated."
    )


# ============================================================
# FINAL PORTFOLIO VALUE
# ============================================================

final_value = float(
    equity_curve.iloc[-1][
        "Portfolio_Equity"
    ]
)


total_return = (
    final_value
    / INITIAL_CAPITAL
) - 1.0


# ============================================================
# TRADE STATISTICS
# ============================================================

if not trades.empty:

    winning_trades = int(
        (
            trades["Return"] > 0
        ).sum()
    )

    losing_trades = int(
        (
            trades["Return"] < 0
        ).sum()
    )

else:

    winning_trades = 0

    losing_trades = 0


# ============================================================
# VALIDATION CHECKS
# ============================================================

if not trades.empty:

    # --------------------------------------------------------
    # NO LOOK-AHEAD
    # --------------------------------------------------------

    assert (
        trades["Entry_Date"]
        > trades["Signal_Date"]
    ).all(), (
        "Look-ahead detected: "
        "entry date is not after signal date."
    )


    # --------------------------------------------------------
    # POSITIVE CAPITAL
    # --------------------------------------------------------

    assert (
        trades["Capital"] > 0
    ).all(), (
        "Invalid trade capital detected."
    )


    # --------------------------------------------------------
    # POSITIVE SHARES
    # --------------------------------------------------------

    assert (
        trades["Shares"] > 0
    ).all(), (
        "Invalid share quantity detected."
    )


    # --------------------------------------------------------
    # POSITION WEIGHT LIMIT
    # --------------------------------------------------------

    max_entry_weight = (
        trades["Entry_Weight"].max()
    )

    assert (
        max_entry_weight
        <= MAX_POSITION_WEIGHT + 1e-9
    ), (
        "Position weight exceeded limit: "
        f"{max_entry_weight:.6f}"
    )


# ============================================================
# EXPOSURE VALIDATION
# ============================================================

max_exposure = float(
    equity_curve["Exposure"].max()
)

assert (
    max_exposure
    <= MAX_TOTAL_EXPOSURE + 1e-9
), (
    "Portfolio exposure exceeded limit: "
    f"{max_exposure:.6f}"
)


# ============================================================
# BASIC CASH VALIDATION
# ============================================================

assert cash >= -1e-6, (
    f"Final cash became negative: {cash}"
)


# ============================================================
# SAVE RESULTS
# ============================================================

trades.to_csv(
    TRADES_OUTPUT,
    index=False,
)

equity_curve.to_csv(
    EQUITY_OUTPUT,
    index=False,
)


# ============================================================
# REPORT
# ============================================================

print()
print("=" * 70)
print("STATEFUL PORTFOLIO BACKTEST")
print("=" * 70)

print(
    f"Transaction cost/side: "
    f"{TRANSACTION_COST_PER_SIDE:.2%}"
)

print(
    f"Initial capital:       "
    f"₹{INITIAL_CAPITAL:,.2f}"
)

print(
    f"Final value:           "
    f"₹{final_value:,.2f}"
)

print(
    f"Total return:          "
    f"{total_return:.2%}"
)

print()

print(
    f"Completed trades:      "
    f"{len(trades)}"
)

print(
    f"Winning trades:        "
    f"{winning_trades}"
)

print(
    f"Losing trades:         "
    f"{losing_trades}"
)


if not trades.empty:

    trade_win_rate = (
        winning_trades
        / len(trades)
    )

    average_trade = (
        trades["Return"].mean()
    )

    median_trade = (
        trades["Return"].median()
    )

    best_trade = (
        trades["Return"].max()
    )

    worst_trade = (
        trades["Return"].min()
    )

    print()

    print(
        f"Trade win rate:        "
        f"{trade_win_rate:.2%}"
    )

    print(
        f"Average trade:         "
        f"{average_trade:.2%}"
    )

    print(
        f"Median trade:          "
        f"{median_trade:.2%}"
    )

    print(
        f"Best trade:            "
        f"{best_trade:.2%}"
    )

    print(
        f"Worst trade:           "
        f"{worst_trade:.2%}"
    )


print()

print(
    f"Max exposure:          "
    f"{equity_curve['Exposure'].max():.2%}"
)

print(
    f"Average exposure:      "
    f"{equity_curve['Exposure'].mean():.2%}"
)

print(
    f"Max active positions:  "
    f"{equity_curve['Active_Positions'].max()}"
)

print()

print(
    f"Open positions:        "
    f"{len(active_positions)}"
)

print()

print(
    f"Trades saved:          "
    f"{TRADES_OUTPUT}"
)

print(
    f"Equity saved:          "
    f"{EQUITY_OUTPUT}"
)

print()

print(
    "Validation checks:     PASSED"
)

print("=" * 70)