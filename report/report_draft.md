# Research Paper Draft (fill in / expand; numbers come from outputs/key_findings.txt)

## 1. Introduction
Nassau Candy sells 15 products in 3 divisions (Chocolate, Sugar, Other). Sales volume alone hides which products truly create profit. Objective: measure margin, profit per unit and profit contribution; find margin risks; recommend pricing/sourcing/portfolio actions.

## 2. Data & Cleaning
10,194 order lines, Jan 2024 - Dec 2025, 18 fields. Steps and counts: see outputs/cleaning_log.txt.
- No missing values, no Sales<=0 / Cost<=0, Gross Profit = Sales - Cost on every row.
- Product label standardised ("Wonka Bar -Scrumdiddlyumptious").
- Dates are day-first. Ship Date is invalid (ship 904-1,642 days after order) so it was excluded.
- 313 rows identical except Row ID were kept; removing them moves overall margin 65.91% -> 65.86%.

## 3. Methodology
Gross margin = profit / sales (weighted, not average of rows); profit per unit; revenue and profit contribution; margin volatility = std of monthly margin (products with >= 3 active months); Pareto; quadrant split at medians; rule-based risk flags (state thresholds).

## 4. Findings (insert charts from charts/)
1. Overall: sales 141,784; gross profit 93,443; margin 65.9%.
2. Chocolate = 92.9% of sales, 95.1% of profit (margin 67.5%). Other = 6.8% of sales, 4.6% of profit (margin 44.8%). Sugar is only 0.3% of sales (40 rows).
3. Concentration: 5 of 15 products (33%) give 80% of both revenue and profit; top 5 = 95.1% of profit. Top product (Scrumdiddlyumptious) = 20.7% of profit. -> dependency risk.
4. Kazookles: margin 7.7%, profit/unit 0.25 on 371 units -> main reason "Other" division is weak. Action: reprice or renegotiate cost; discontinue if neither works.
5. Lickable Wallpaper: 50% margin but highest profit/unit (10.00) - growth candidate.
6. Factory view: The Other Factory margin 11.9% vs Lot's O' Nuts 69.1%.
7. Sugar products (SweeTARTS, Nerds, Fun Dip) have margins 40-47% on tiny volume -> discontinuation review.
(Add: margin volatility, region x division heatmap, what-if example.)

## 5. Recommendations
Reprice/renegotiate Kazookles; review the low-volume Sugar items; protect and grow the top Wonka Bars; test a price increase on strong sellers (use the what-if tool); reduce reliance on 5 products by growing Lickable Wallpaper / high-margin niche items.

## 6. Limitations
Only 15 products; Ship Date unusable; no demand/price-elasticity data; cost is manufacturing cost only; currency not stated; 2 years of data.

## 7. Conclusion

---
# Executive Summary (1 page, plain language)
- Headline: the business is healthy (65.9% margin) but depends on 5 products for ~95% of profit.
- Problem: Kazookles earns 7.7% margin; Other division margin is 44.8%.
- Actions: (1) reprice/renegotiate Kazookles, (2) review 3 low-volume Sugar items, (3) grow Lickable Wallpaper, (4) protect top Wonka Bars.
- Expected impact: quantify with the what-if tool.
