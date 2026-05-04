# Olist E-Commerce Sales Intelligence

> Research Question: Which product categories, regions, and seasons drive the most
> revenue — and what predicts a high-value customer?

Stack: Python · DuckDB · SQL · Scikit-learn · Prophet · Streamlit · Plotly  
Data: [Olist Brazilian E-Commerce — Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (9 relational tables, 100k+ orders)

---

## How to Reproduce

1. Install dependencies
pip install duckdb pandas numpy matplotlib seaborn plotly scikit-learn streamlit prophet kaggle
```

2. Download the dataset
kaggle datasets download -d olistbr/brazilian-ecommerce --unzip -p data/
```

**3. Run the pipeline in order
python src/01_setup_db.py
python src/02_eda.py
python src/03_rfm.py
python src/04_forecasting.py
python -m streamlit run src/05_dashboard.py
```

---

## 🔬 Key Findings

### 1. Revenue & Growth
- Revenue grew approximately 20x between September 2016 and November 2017,
  then plateaued at a sustained R$1.0M–R$1.2M per month through 2018 — a
  classic hypergrowth-to-maturity curve.
- November 2017 was the single peak month (~R$1.2M, 7,000+ orders), almost
  certainly driven by Black Friday demand.
- A sharp revenue dip followed in December 2017, suggesting Black Friday pulled
  demand forward and suppressed Christmas spending.

### 2. Top Product Categories
- **Health & beauty** is the #1 revenue category (~R$1.25M), narrowly ahead of
  watches & gifts (~R$1.2M) and bed, bath & table (~R$1.05M).
- The top 5 categories generate disproportionately more revenue than categories
  6–15, which cluster tightly between R$0.4M–R$0.8M.
- Lifestyle and home categories dominate over technology, indicating the typical
  Olist customer shops for personal and household goods.

### 3. Regional Concentration
- São Paulo (SP) generates ~R$5.8M— nearly 3x the revenue of Rio de Janeiro
  (RJ) at ~R$2.1M, the second-placed state.
- The majority of Brazilian states contribute negligibly to revenue, representing
  a large untapped market opportunity.
- Northern states (AP, RR, AC, RO) show near-zero revenue, consistent with high
  freight-to-price ratios acting as a purchase barrier in remote regions.

### 4. When Customers Buy
- Monday and Tuesday are the highest-volume order days, with Monday producing
  the single strongest weekly effect (+~R$3,800 above average).
- Saturday is the weakest day by far (~R$6,000 below average), indicating
  Brazilians browse and buy during working hours, not weekends.
- Orders peak between 10am and 8pm on weekdays. The 0–7am window is nearly
  inactive across all days.

### 5. Customer Satisfaction
- The review distribution is heavily right-skewed: **57,328 five-star reviews**
  out of ~99,000 total (~77% of customers gave 4 or 5 stars).
- However, **11,424 one-star reviews** represent a polarised minority — more than
  the 2-star and 3-star groups combined, suggesting a split experience: most
  customers are satisfied, but unhappy customers are very unhappy.

### 6. Customer Segmentation (RFM + K-Means)
- **"Needs Attention"** is the largest segment (~20,000 customers) but generates
  only moderate revenue — the biggest opportunity for targeted re-engagement.
- **"At Risk"** customers generate the highest revenue of any segment (~R$3.0M),
  meaning the business's most valuable customers are actively disengaging.
  Retaining even a fraction would have outsized revenue impact.
- **Champions** (only ~5,000 customers) generate ~R$2.0M — approximately 4x the
  per-customer revenue of the average segment.
- K-Means clustering (k=4) identified four distinct customer profiles:

  | Cluster | Profile | Avg Recency | Avg Spend |
  |---|---|---|---|
  | C0 | Recent mid-spenders | 180 days | R$167 |
  | C1 | Low-value dormant | 208 days | R$54 |
  | C2 | High-value churned | 349 days | R$496 |
  | C3 | Lost low-spenders | 472 days | R$96 |

- **Cluster 2 is the most actionable insight**: the highest-spending customers
  are also the most dormant (349 days since last purchase on average). A
  targeted win-back campaign for this group offers the highest potential ROI.

### 7. Revenue Forecast (Prophet)
- The 90-day Prophet forecast projects **daily revenue rising from ~R$25,000–
  R$35,000 toward R$50,000–R$70,000** by end of the forecast window, driven
  by detected year-end seasonal uplift.
- **Weekly seasonality:** Monday adds ~R$3,800 above trend; Saturday subtracts
  ~R$6,000 — consistent with the EDA findings.
- **Yearly seasonality:** November produces the strongest positive seasonal spike
  (~+R$22,000/day); January produces the deepest trough (−R$14,000/day) — a
  classic Brazilian retail calendar pattern.
- The confidence interval widens toward the end of the 90-day window, reflecting
  honest model uncertainty further from the training data.

---

##  Technical Highlights

- SQL: Multi-table joins across 9 relational tables, window functions
  (`OVER`, `NTILE`, running totals), CTEs for cohort analysis, `QUALIFY` for
  top-N per group
- Python: Pandas for data wrangling, Scikit-learn for K-Means clustering and
  PCA, Prophet for time-series forecasting, Plotly + Matplotlib for
  visualisation
- DuckDB: In-process SQL database — no server required, queries run directly
  on CSV files and Pandas dataframes
- Streamlit: Interactive dashboard with live SQL queries on every filter
  change (date range, state)
