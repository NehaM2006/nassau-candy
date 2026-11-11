"""Run:  python analysis.py   -> cleans data, computes everything, saves CSVs + charts for your paper."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import *

df, log = clean_data()
df.to_csv(CLEAN, index=False)
(BASE / "outputs" / "cleaning_log.txt").write_text("\n".join(log))
print("\n".join(log))

pm = quadrant(add_flags(product_metrics(df)))
dm = division_metrics(df)
pm.to_csv(BASE / "outputs" / "product_metrics.csv", index=False)
dm.to_csv(BASE / "outputs" / "division_metrics.csv", index=False)
reg = df.groupby(["Region", "Division"]).agg(S=("Sales", "sum"), P=("Gross Profit", "sum")).reset_index()
reg["Margin %"] = reg.P / reg.S * 100
reg.to_csv(BASE / "outputs" / "region_division_margin.csv", index=False)
fac = df.groupby("Factory").agg(Sales=("Sales", "sum"), Profit=("Gross Profit", "sum")).reset_index()
fac["Margin %"] = fac.Profit / fac.Sales * 100
fac.to_csv(BASE / "outputs" / "factory_margin.csv", index=False)

pr, n80p = pareto(pm, "Profit")
rv, n80r = pareto(pm, "Sales")
N = len(pm)
tot_s, tot_p = df["Sales"].sum(), df["Gross Profit"].sum()

# sensitivity: remove rows identical except Row ID
dd = df.drop_duplicates(subset=[c for c in df.columns if c != "Row ID"])
sens = (dd["Gross Profit"].sum() / dd["Sales"].sum() * 100)

lines = [
    f"Total sales: {tot_s:,.2f} | total gross profit: {tot_p:,.2f} | overall margin: {tot_p/tot_s*100:.2f}%",
    f"Date range: {df['Order Date'].min().date()} to {df['Order Date'].max().date()}",
    f"Products for 80% of revenue: {n80r} of {N} ({n80r/N*100:.0f}%)",
    f"Products for 80% of profit : {n80p} of {N} ({n80p/N*100:.0f}%)",
    f"Top product profit share: {pr.iloc[0]['Product Name']} = {pr.iloc[0]['Profit Contribution %']:.1f}%",
    f"Top 5 products profit share: {pr.head(5)['Profit Contribution %'].sum():.1f}%",
    f"Sensitivity (duplicates removed) margin: {sens:.2f}% vs {tot_p/tot_s*100:.2f}%",
    "", "Risk flags:", pm[["Product Name", "Margin %", "Risk Flag", "Quadrant"]].round(2).to_string(index=False),
    "", "Division metrics:", dm.round(2).to_string(index=False),
    "", "Factory margin:", fac.round(2).to_string(index=False),
]
(BASE / "outputs" / "key_findings.txt").write_text("\n".join(lines))
print("\n".join(lines))

# ---------------- charts ----------------
C = BASE / "charts"
def save(name):
    plt.tight_layout(); plt.savefig(C / name, dpi=150); plt.close()

s = pm.sort_values("Margin %")
plt.figure(figsize=(9, 6)); plt.barh(s["Product Name"], s["Margin %"], color="#c0504d")
plt.axvline(tot_p / tot_s * 100, ls="--", c="k", label="Overall margin"); plt.legend()
plt.xlabel("Gross margin %"); plt.title("Product margin leaderboard"); save("01_margin_leaderboard.png")

s = pm.sort_values("Profit")
plt.figure(figsize=(9, 6)); plt.barh(s["Product Name"], s["Profit"], color="#4f81bd")
plt.xlabel("Gross profit"); plt.title("Profit contribution by product"); save("02_profit_by_product.png")

x = np.arange(len(dm)); w = 0.38
plt.figure(figsize=(7, 5)); plt.bar(x - w/2, dm["Sales"], w, label="Sales"); plt.bar(x + w/2, dm["Profit"], w, label="Profit")
plt.xticks(x, dm["Division"]); plt.legend(); plt.title("Revenue vs profit by division"); save("03_division_rev_vs_profit.png")

plt.figure(figsize=(8, 5))
df.boxplot(column="Margin %", by="Division", grid=False); plt.suptitle(""); plt.title("Order-line margin distribution by division")
plt.ylabel("Margin %"); save("04_margin_boxplot_division.png")

for name, p, col in [("05_pareto_profit.png", pr, "Profit"), ("06_pareto_revenue.png", rv, "Sales")]:
    fig, ax = plt.subplots(figsize=(10, 5)); ax.bar(p["Product Name"], p[col], color="#4f81bd")
    ax.tick_params(axis="x", rotation=75); ax2 = ax.twinx()
    ax2.plot(p["Product Name"], p["Cumulative %"], "o-", c="#c0504d"); ax2.axhline(80, ls="--", c="gray"); ax2.set_ylim(0, 105)
    ax.set_title(f"Pareto - {col}"); save(name)

plt.figure(figsize=(8, 6))
sub = df.sample(min(4000, len(df)), random_state=1)
plt.scatter(sub["Sales"], sub["Cost"], s=6, alpha=.4); mx = sub["Sales"].max()
plt.plot([0, mx], [0, mx], "r--", label="Break-even (Cost = Sales)"); plt.legend()
plt.xlabel("Sales"); plt.ylabel("Cost"); plt.title("Cost vs Sales (order lines)"); save("07_cost_vs_sales.png")

plt.figure(figsize=(9, 6)); plt.scatter(pm["Sales"], pm["Margin %"], s=80)
for _, r in pm.iterrows(): plt.annotate(r["Product Name"].replace("Wonka Bar - ", "WB-"), (r["Sales"], r["Margin %"]), fontsize=7)
plt.axvline(pm["Sales"].median(), ls=":", c="gray"); plt.axhline(pm["Margin %"].median(), ls=":", c="gray")
plt.xscale("log"); plt.xlabel("Sales (log)"); plt.ylabel("Margin %"); plt.title("Sales vs margin quadrant"); save("08_quadrant.png")

mm = df.groupby("Month").agg(S=("Sales", "sum"), P=("Gross Profit", "sum")); mm["m"] = mm.P / mm.S * 100
plt.figure(figsize=(9, 4)); plt.plot(mm.index, mm["m"], marker="o"); plt.title("Monthly overall margin %"); plt.ylabel("%"); save("09_monthly_margin.png")
print("\nDone. See outputs/ and charts/")
