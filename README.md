# Field Sales Visit Analytics

End-to-end analysis of a beverage company's field sales team: how well reps
cover their stores, how closely they follow the monthly visit plan, how
productive a field day is, how clean the data is, and where distributor stock
runs out.

**Stack:** PostgreSQL · SQL · Python (pandas) · Looker Studio / Power BI · Excel

> Status: work in progress. Data, SQL cleaning, analytics views and the
> exploratory notebook are done; dashboard and written report are next.

## Key findings so far

| | Finding |
|---|---|
| Coverage | Stores of every grade get only ~80% of their required visits; just 24% of A-store months hit the 8-visit target |
| Plan vs actual | Team completes 78% of planned visits; one rep (R06) completes 58% and ends the field day ~1.5 h earlier |
| When visits are lost | Saturday completion is 68% vs 80% on weekdays; Aug–Sep (rainy season) drops ~6 points |
| Data quality | ~9% of visits carry an issue (GPS > 300 m from store, no check-out, < 2 min, no photo); 0.6% were duplicate submissions |
| Stock | Craft beer grows from 7% to 11.5% of cases, while three craft/draught items at two distributors lose ~340k THB of orders to stock-outs |

Details and charts: [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb).

## The app behind the data

I designed and built the system that collects this kind of data: a field-sales
app (mobile, for reps) and an admin console (web, for managers), used in
production by a beverage company's sales team. Shown here with the synthetic
data, renamed and rebranded:
[**see all screens and my role →**](docs/app/README.md)

| Mobile: store list | Mobile: GPS check-in | Admin: visit dashboard |
|---|---|---|
| <img src="docs/app/app-02-stores.png" width="220"> | <img src="docs/app/app-03-checkin.png" width="220"> | <img src="docs/app/admin-01-visits.png" width="420"> |

## The business

*FieldPulse* is a fictional beverage company in Bangkok (beer, soda, water).

- 8 sales reps in 4 territories, managed by 2 area sales managers (ASM)
- 480 stores graded **A / B / C**; the grade sets how often a store must be
  visited each month (A = 8, B = 4, C = 2)
- Each month a rep submits a visit plan, the ASM approves it, and the rep
  checks in and out at each store with GPS and photos, sometimes taking an order
- 4 distributors ("agents") hold the stock that store orders draw on

The dataset covers **April to September 2026**: about 10,000 planned visits,
8,800 actual visits and 9,000 order lines.

## Business questions

1. **Coverage:** Are A/B/C stores visited as often as their grade requires?
2. **Plan vs actual:** How much of the approved plan is carried out, and by whom?
3. **Productivity:** Stores per day, time in store, start and end of the field day.
4. **Data quality:** Check-ins far from the store, missing check-outs, very
   short visits, duplicate submissions.
5. **Distributor stock:** Which SKUs run out, where, and how much demand is lost?
6. **Recommendations:** What would close the coverage gap?

## Repository layout

```
data/
  generator/      Python that builds the dataset (fixed seed: reproducible)
  output/         the generated CSV files, ready to use
  load_postgres.py  creates the schema and loads the CSVs into PostgreSQL
sql/
  01_schema.sql   raw layer: tables mirroring the CSV files
  02_cleaning.sql clean layer: de-duplication, phone clean-up, data-quality flags
  03_views.sql    analytics layer: dashboard-ready views
  04_analysis.sql one query block per business question
notebooks/
  01_eda.ipynb    exploratory analysis with charts
docs/
  data-dictionary.md
```

### Data layers

| Schema | What it holds |
|---|---|
| `raw` | the CSVs as delivered, problems included |
| `clean` | `stores` (phones normalised), `visits` (duplicates removed, issues flagged), `valid_visits`, `data_quality_summary` |
| `analytics` | `visits_enriched` (one flat row per visit), `store_month_coverage`, `rep_plan_vs_actual`, `plan_visits` (one row per planned visit), `rep_daily_productivity`, `sales_lines`, `stock_weekly`, `visit_quality` (one row per check-in, issues as 0/1) |

## Quick start

```bash
pip install -r requirements.txt

# 1. (optional) regenerate the data; the CSVs are already in data/output/
python data/generator/generate.py

# 2. load into any PostgreSQL (e.g. a free Neon database);
#    this also builds the clean and analytics views
export DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"
python data/load_postgres.py

# 3. explore
jupyter notebook notebooks/01_eda.ipynb
```

The queries in `sql/04_analysis.sql` can also be pasted block by block into
any SQL editor, such as the Neon SQL Editor.

Optional: `python data/generator/fetch_osm_stores.py` downloads real shop and
restaurant locations in Bangkok from OpenStreetMap; the next run of
`generate.py` then places stores at those locations instead of random points.

## About the data

All people, stores, products and numbers are **synthetic**, generated with
Python and [Faker](https://faker.readthedocs.io/). The data is built to
behave like a real field sales operation: working days skip Sundays and Thai
public holidays, reps skip more visits on Saturdays and in the rainy season,
craft beer demand grows month by month, and about 5% of visits carry
deliberate data-quality problems to find and clean.

Store locations from the optional OpenStreetMap step are
© OpenStreetMap contributors, under the
[Open Database License](https://www.openstreetmap.org/copyright).
