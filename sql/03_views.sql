-- Analytics layer: views shaped for dashboards (Looker Studio / Power BI).
-- Each view answers one family of business questions and has one row per
-- clearly stated grain. Built on the clean schema from 02_cleaning.sql.
-- Rerunnable: drops and recreates the analytics schema.

DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA analytics;

-- One flat row per visit with everything a dashboard filter might need.
-- Grain: visit.
CREATE VIEW analytics.visits_enriched AS
SELECT
    v.visit_id,
    v.visit_date,
    date_trunc('month', v.visit_date)::date AS visit_month,
    to_char(v.visit_date, 'Dy')             AS weekday,
    v.checkin_at,
    v.checkout_at,
    v.duration_min,
    v.distance_from_store_m,
    v.is_planned,
    v.flag_gps_far,
    v.flag_missing_checkout,
    v.flag_too_short,
    v.flag_no_photo,
    NOT (v.flag_gps_far OR coalesce(v.flag_too_short, false)) AS is_valid,
    v.rep_id,
    r.rep_name,
    r.manager_id AS asm_id,
    s.store_id,
    s.store_name,
    s.channel,
    s.grade,
    s.territory_id,
    s.district,
    s.lat,
    s.lng,
    coalesce(o.order_value_thb, 0) AS order_value_thb,
    coalesce(o.order_cases, 0)     AS order_cases,
    o.visit_id IS NOT NULL         AS has_order
FROM clean.visits v
JOIN raw.reps r USING (rep_id)
JOIN clean.stores s USING (store_id)
LEFT JOIN (
    SELECT visit_id, sum(amount_thb) AS order_value_thb, sum(qty_cases) AS order_cases
    FROM raw.order_lines
    GROUP BY visit_id
) o USING (visit_id);

-- Coverage: did each store get the visits its grade requires?
-- Grain: store x month. Months in which a store opened are left out,
-- because the store was not around for the whole month.
CREATE VIEW analytics.store_month_coverage AS
WITH months AS (
    SELECT generate_series(
        (SELECT date_trunc('month', min(plan_date)) FROM raw.visit_plans),
        (SELECT date_trunc('month', max(plan_date)) FROM raw.visit_plans),
        interval '1 month'
    )::date AS month
),
actual AS (
    SELECT store_id, date_trunc('month', visit_date)::date AS month, count(*) AS valid_visits
    FROM clean.valid_visits
    GROUP BY 1, 2
)
SELECT
    m.month,
    s.store_id,
    s.store_name,
    s.channel,
    s.grade,
    s.territory_id,
    s.district,
    s.rep_id,
    t.visits_per_month                                  AS required_visits,
    coalesce(a.valid_visits, 0)                         AS valid_visits,
    least(coalesce(a.valid_visits, 0), t.visits_per_month)::numeric
        / t.visits_per_month                            AS coverage_ratio,
    coalesce(a.valid_visits, 0) >= t.visits_per_month   AS met_target,
    coalesce(a.valid_visits, 0) = 0                     AS not_visited
FROM months m
JOIN clean.stores s ON s.created_date < m.month
JOIN clean.grade_targets t USING (grade)
LEFT JOIN actual a ON a.store_id = s.store_id AND a.month = m.month;

-- Plan vs actual: how much of the approved plan was carried out.
-- A plan counts as done when a valid visit links to it.
-- Grain: rep x month.
CREATE VIEW analytics.rep_plan_vs_actual AS
WITH plans AS (
    SELECT rep_id, date_trunc('month', plan_date)::date AS month, count(*) AS planned
    FROM raw.visit_plans
    GROUP BY 1, 2
),
done AS (
    SELECT rep_id, date_trunc('month', visit_date)::date AS month,
           count(DISTINCT plan_id) FILTER (WHERE is_planned) AS planned_done,
           count(*) FILTER (WHERE NOT is_planned)            AS unplanned
    FROM clean.valid_visits
    GROUP BY 1, 2
)
SELECT
    p.month,
    p.rep_id,
    r.rep_name,
    r.territory_id,
    r.manager_id AS asm_id,
    p.planned,
    coalesce(d.planned_done, 0) AS planned_done,
    coalesce(d.unplanned, 0)    AS unplanned,
    round(coalesce(d.planned_done, 0)::numeric / p.planned, 3) AS plan_completion
FROM plans p
JOIN raw.reps r USING (rep_id)
LEFT JOIN done d USING (rep_id, month);

-- Field-day productivity.
-- Grain: rep x working day with at least one visit.
CREATE VIEW analytics.rep_daily_productivity AS
SELECT
    visit_date,
    rep_id,
    rep_name,
    territory_id,
    count(*)                                     AS visits,
    count(*) FILTER (WHERE is_valid)             AS valid_visits,
    min(checkin_at)::time                        AS first_checkin,
    max(coalesce(checkout_at, checkin_at))::time AS last_activity,
    round(extract(epoch FROM max(coalesce(checkout_at, checkin_at)) - min(checkin_at)) / 3600, 2)
                                                 AS field_hours,
    round(avg(duration_min), 1)                  AS avg_visit_min,
    round(sum(duration_min) / 60, 2)             AS in_store_hours,
    sum(order_value_thb)                         AS order_value_thb,
    count(*) FILTER (WHERE has_order)            AS visits_with_order
FROM analytics.visits_enriched
GROUP BY visit_date, rep_id, rep_name, territory_id;

-- Sales from store orders.
-- Grain: day x store x SKU.
CREATE VIEW analytics.sales_lines AS
SELECT
    v.visit_date,
    date_trunc('month', v.visit_date)::date AS visit_month,
    v.rep_id,
    v.territory_id,
    v.store_id,
    v.channel,
    v.grade,
    k.sku_id,
    k.sku_name,
    k.category,
    sum(o.qty_cases)  AS cases,
    sum(o.amount_thb) AS amount_thb
FROM raw.order_lines o
JOIN analytics.visits_enriched v USING (visit_id)
JOIN raw.skus k USING (sku_id)
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10;

-- Distributor stock health.
-- Grain: week x agent x SKU.
CREATE VIEW analytics.stock_weekly AS
SELECT
    st.week_start,
    st.agent_id,
    a.agent_name,
    a.territory_id,
    st.sku_id,
    k.sku_name,
    k.category,
    st.opening_qty,
    st.received_qty,
    st.demand_qty,
    st.sold_qty,
    st.closing_qty,
    st.demand_qty - st.sold_qty                        AS lost_cases,
    (st.demand_qty - st.sold_qty) * k.unit_price_thb   AS lost_value_thb,
    st.demand_qty > st.sold_qty                        AS is_stockout,
    CASE WHEN st.demand_qty = 0 THEN 1
         ELSE round(st.sold_qty::numeric / st.demand_qty, 3) END AS fill_rate
FROM raw.agent_stock st
JOIN raw.agents a USING (agent_id)
JOIN raw.skus k USING (sku_id);
