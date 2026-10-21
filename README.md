# Field Sales Visit Analytics

End-to-end analysis of a beverage company's field sales team: how well reps
cover their stores, how closely they follow the monthly visit plan, how
productive a field day is, how clean the data is, and where distributor stock
runs out.

**Stack:** PostgreSQL · SQL · Python (pandas) · Looker Studio / Power BI · Excel

> Status: work in progress. Data generator and database schema are done;
> analysis, dashboard and report are next.

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
  01_schema.sql   tables (raw layer)
docs/
  data-dictionary.md
```

## Quick start

```bash
pip install -r requirements.txt

# 1. (optional) regenerate the data; the CSVs are already in data/output/
python data/generator/generate.py

# 2. load into any PostgreSQL, e.g. a free Neon database
export DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"
python data/load_postgres.py
```

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
