"""Shared functions: cleaning + metrics. Used by analysis.py and app.py"""
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).parent
RAW = BASE / "data" / "Nassau_Candy_Distributor.csv"
CLEAN = BASE / "data" / "cleaned.csv"

# Product -> factory (from the project brief)
FACTORY_MAP = {
    "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
    "Wonka Bar - Scrumdiddlyumptious": "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's",
    "Laffy Taffy": "Sugar Shack", "SweeTARTS": "Sugar Shack", "Nerds": "Sugar Shack",
    "Fun Dip": "Sugar Shack", "Fizzy Lifting Drinks": "Sugar Shack",
    "Everlasting Gobstopper": "Secret Factory", "Lickable Wallpaper": "Secret Factory",
    "Wonka Gum": "Secret Factory",
    "Hair Toffee": "The Other Factory", "Kazookles": "The Other Factory",
}


def clean_data(raw_path=RAW):
    """Returns (clean_df, log_list). Every step is logged with counts."""
    log = []
    df = pd.read_csv(raw_path)
    log.append(f"Raw rows loaded: {len(df):,} | columns: {df.shape[1]}")

    # 1. strip whitespace in column names and text columns
    df.columns = df.columns.str.strip()
    for c in df.columns:
        if df[c].dtype == object or str(df[c].dtype).startswith("str"):
            df[c] = df[c].astype(str).str.strip()

    # 2. dates (file is day-first: 03-01-2024 = 3 Jan 2024)
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="%d-%m-%Y", errors="coerce")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="%d-%m-%Y", errors="coerce")
    bad = int(df["Order Date"].isna().sum())
    df = df.dropna(subset=["Order Date"])
    log.append(f"Invalid Order Date rows removed: {bad}")
    lag = (df["Ship Date"] - df["Order Date"]).dt.days
    log.append(f"Ship Date check: lag ranges {lag.min()} to {lag.max()} days (impossible). "
               f"Ship Date NOT used in the analysis.")

    # 3. standardise labels
    df["Product Name"] = df["Product Name"].str.replace(r"\s*-\s*", " - ", regex=True)
    df["Product Name"] = df["Product Name"].str.replace(r"\s+", " ", regex=True)
    df["Division"] = df["Division"].str.title()
    df["Region"] = df["Region"].str.title()
    log.append(f"Standardised labels -> {df['Product Name'].nunique()} unique products, "
               f"{df['Division'].nunique()} divisions")

    # 4. numeric validation
    for c in ["Sales", "Units", "Gross Profit", "Cost"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n = len(df)
    df = df.dropna(subset=["Sales", "Cost", "Gross Profit"])
    log.append(f"Rows with missing Sales/Cost/Profit removed: {n - len(df)}")
    n = len(df)
    df = df[(df["Sales"] > 0) & (df["Cost"] > 0)]
    log.append(f"Rows with Sales<=0 or Cost<=0 removed: {n - len(df)}")

    # 5. missing/invalid units -> impute from the product's median price per unit
    bad_units = df["Units"].isna() | (df["Units"] <= 0)
    if bad_units.any():
        ok = ~bad_units
        price = (df.loc[ok, "Sales"] / df.loc[ok, "Units"]).groupby(df.loc[ok, "Product Name"]).median()
        est = (df.loc[bad_units, "Sales"] / df.loc[bad_units, "Product Name"].map(price)).round()
        df.loc[bad_units, "Units"] = est.clip(lower=1)
        df = df.dropna(subset=["Units"])
    log.append(f"Rows with missing/invalid Units imputed: {int(bad_units.sum())}")
    df["Units"] = df["Units"].astype(int)

    # 6. profit consistency: Gross Profit should equal Sales - Cost
    mism = (df["Sales"] - df["Cost"] - df["Gross Profit"]).abs() > 0.01
    df.loc[mism, "Gross Profit"] = df["Sales"] - df["Cost"]
    log.append(f"Rows where Gross Profit != Sales - Cost (recalculated): {int(mism.sum())}")

    # 7. duplicates
    d_id = int(df["Row ID"].duplicated().sum())
    df = df.drop_duplicates(subset="Row ID")
    d_rep = int(df.drop(columns=["Row ID"]).duplicated().sum())
    log.append(f"Duplicate Row IDs removed: {d_id}")
    log.append(f"Rows identical except Row ID: {d_rep} (KEPT - plausible repeat line items; "
               f"sensitivity check in analysis.py)")

    # 8. helper columns
    df["Factory"] = df["Product Name"].map(FACTORY_MAP)
    df["Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    df["Cost per Unit"] = df["Cost"] / df["Units"]
    df["Price per Unit"] = df["Sales"] / df["Units"]
    df["Margin %"] = df["Gross Profit"] / df["Sales"] * 100
    log.append(f"Final clean rows: {len(df):,}")
    return df.reset_index(drop=True), log


def product_metrics(df):
    g = df.groupby(["Product Name", "Division", "Factory"], dropna=False).agg(
        Sales=("Sales", "sum"), Profit=("Gross Profit", "sum"), Cost=("Cost", "sum"),
        Units=("Units", "sum"), Orders=("Row ID", "count")).reset_index()
    g["Margin %"] = g["Profit"] / g["Sales"] * 100
    g["Profit per Unit"] = g["Profit"] / g["Units"]
    g["Cost Ratio %"] = g["Cost"] / g["Sales"] * 100
    g["Revenue Contribution %"] = g["Sales"] / g["Sales"].sum() * 100
    g["Profit Contribution %"] = g["Profit"] / g["Profit"].sum() * 100
    # margin volatility = std of monthly margin (needs >= 3 active months)
    m = df.groupby(["Product Name", "Month"]).agg(s=("Sales", "sum"), p=("Gross Profit", "sum")).reset_index()
    m["mm"] = m["p"] / m["s"] * 100
    vol = m.groupby("Product Name")["mm"].agg(["std", "count"])
    vol.loc[vol["count"] < 3, "std"] = np.nan
    g["Margin Volatility (std pts)"] = g["Product Name"].map(vol["std"])
    return g.sort_values("Profit", ascending=False).reset_index(drop=True)


def add_flags(pm, margin_threshold=50.0, low_sales_pct=1.0):
    """Rule-based risk flags (state these rules in your paper)."""
    pm = pm.copy()
    low_margin = (pm["Margin %"] < margin_threshold).tolist()
    low_sales = (pm["Revenue Contribution %"] < low_sales_pct).tolist()
    flags = []
    for lm, ls in zip(low_margin, low_sales):
        if lm and ls:
            flags.append("Discontinuation review")
        elif lm:
            flags.append("Reprice / renegotiate cost")
        elif ls:
            flags.append("Low volume - monitor")
        else:
            flags.append("Healthy")
    pm["Risk Flag"] = flags
    return pm


def quadrant(pm):
    s_med, m_med = pm["Sales"].median(), pm["Margin %"].median()

    def q(r):
        hs, hm = r["Sales"] >= s_med, r["Margin %"] >= m_med
        if hs and hm:
            return "Star (high sales, high margin)"
        if hs:
            return "Volume trap (high sales, low margin)"
        if hm:
            return "Niche / growth (low sales, high margin)"
        return "Weak (low sales, low margin)"
    pm = pm.copy()
    pm["Quadrant"] = pm.apply(q, axis=1)
    return pm


def pareto(pm, col):
    p = pm.sort_values(col, ascending=False).reset_index(drop=True)
    p["Cumulative %"] = p[col].cumsum() / p[col].sum() * 100
    p["Rank"] = np.arange(1, len(p) + 1)
    n80 = int((p["Cumulative %"] < 80).sum() + 1)
    return p, n80


def division_metrics(df):
    d = df.groupby("Division").agg(Sales=("Sales", "sum"), Profit=("Gross Profit", "sum"),
                                   Units=("Units", "sum"), Products=("Product Name", "nunique")).reset_index()
    d["Margin %"] = d["Profit"] / d["Sales"] * 100
    d["Revenue Share %"] = d["Sales"] / d["Sales"].sum() * 100
    d["Profit Share %"] = d["Profit"] / d["Profit"].sum() * 100
    d["Share Gap (pts)"] = d["Profit Share %"] - d["Revenue Share %"]
    return d.sort_values("Profit", ascending=False)
