# Data dictionary

All tables live in the `raw` schema. Timestamps are Bangkok local time.

```
territories 1─* reps (Sales Rep) 1─* stores *─1 agents
                  │                  │
                  1                  1
                  *                  *
             visit_plans 1───0..1 visits 1─* order_lines *─1 skus
agents 1─* agent_stock *─1 skus
```

## territories
| column | type | description |
|---|---|---|
| territory_id | text | `BKK-East`, `BKK-North`, `BKK-West`, `BKK-South` |
| asm_id | text | area sales manager in charge |

## reps
| column | type | description |
|---|---|---|
| rep_id | text | `R01`-`R08` for sales reps, `ASM-01`/`ASM-02` for managers |
| rep_name, nickname | text | synthetic Thai names |
| role | text | `Sales Rep` or `ASM` |
| territory_id | text | empty for ASMs |
| manager_id | text | the rep's ASM |
| hire_date | date | |

## agents
Distributors that hold stock and deliver store orders; one per territory.

| column | type | description |
|---|---|---|
| agent_id | text | `AG-01`-`AG-04` |
| agent_name | text | |
| territory_id | text | |

## stores
| column | type | description |
|---|---|---|
| store_id | text | `ST-0001`-`ST-0480` |
| store_name | text | |
| channel | text | Grocery, Minimart, Convenience, Restaurant, Bar |
| grade | char | A / B / C; sets the monthly visit target (8 / 4 / 2) |
| territory_id, district | text | |
| lat, lng | numeric | store location |
| rep_id | text | rep responsible for the store |
| agent_id | text | distributor that supplies the store |
| owner_name, phone | text | phone formats are inconsistent on purpose |
| location_source | text | `osm` (real OpenStreetMap place) or `synthetic` |
| created_date | date | about 5% of stores open during the period |

## skus
| column | type | description |
|---|---|---|
| sku_id | text | `SKU-001`-`SKU-012` |
| sku_name, pack | text | |
| category | text | Lager, Premium, Craft, Draught, Soda, Water |
| unit_price_thb | numeric | price per case |

## visit_plans
One row per planned store visit, submitted by the rep and approved by the ASM.

| column | type | description |
|---|---|---|
| plan_id | text | |
| rep_id, store_id | text | |
| plan_date | date | |
| submitted_at, approved_at | timestamp | the whole month's plan is submitted at once |
| approved_by | text | ASM id |

## visits
One row per check-in.

| column | type | description |
|---|---|---|
| visit_id | text | |
| rep_id, store_id | text | |
| plan_id | text | NULL when the visit was not in the plan |
| checkin_at | timestamp | |
| checkout_at | timestamp | NULL when the rep forgot to check out |
| checkin_lat, checkin_lng | numeric | phone GPS at check-in |
| photo_count | smallint | |

Known data-quality issues (injected on purpose):

| issue | share of visits | how to spot it |
|---|---|---|
| GPS far from store | ~3% | distance from store > 300 m |
| missing check-out | ~2% | `checkout_at IS NULL` |
| very short visit | ~1% | under 2 minutes |
| duplicate submission | ~0.5% | same rep, store and plan, check-in within 90 seconds |

## order_lines
| column | type | description |
|---|---|---|
| visit_id, sku_id | text | primary key together |
| qty_cases | integer | |
| unit_price_thb, amount_thb | numeric | amount = qty x price |

## agent_stock
Weekly stock movement per distributor and SKU.

| column | type | description |
|---|---|---|
| week_start | date | Monday |
| agent_id, sku_id | text | |
| opening_qty, received_qty | integer | cases |
| demand_qty | integer | cases ordered by stores that week |
| sold_qty | integer | cases delivered; below demand_qty = stock-out |
| closing_qty | integer | |
