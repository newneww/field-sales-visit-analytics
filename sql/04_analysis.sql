-- Analysis queries: one block per business question in the README.
-- Run after 02_cleaning.sql and 03_views.sql. Each query is self-contained,
-- so any block can be copied into the Neon SQL Editor on its own.


-- =====================================================================
-- Q1. Coverage: are stores visited as often as their grade requires?
-- =====================================================================

-- 1a. Coverage by grade over the whole period.
SELECT
    grade,
    count(*)                                         AS store_months,
    round(avg(valid_visits), 2)                      AS avg_visits,
    max(required_visits)                             AS required,
    round(100 * avg(coverage_ratio), 1)              AS coverage_pct,
    round(100 * avg(met_target::int), 1)             AS pct_store_months_on_target,
    round(100 * avg(not_visited::int), 1)            AS pct_not_visited_at_all
FROM analytics.store_month_coverage
GROUP BY grade
ORDER BY grade;

-- 1b. Coverage of A-grade stores by rep: who leaves the key accounts uncovered?
SELECT
    c.rep_id,
    r.rep_name,
    c.territory_id,
    round(100 * avg(c.coverage_ratio), 1)  AS a_store_coverage_pct,
    round(100 * avg(c.met_target::int), 1) AS pct_on_target
FROM analytics.store_month_coverage c
JOIN raw.reps r USING (rep_id)
WHERE c.grade = 'A'
GROUP BY c.rep_id, r.rep_name, c.territory_id
ORDER BY a_store_coverage_pct;

-- 1c. Coverage trend by month and grade.
SELECT
    month,
    grade,
    round(100 * avg(coverage_ratio), 1) AS coverage_pct
FROM analytics.store_month_coverage
GROUP BY month, grade
ORDER BY month, grade;


-- =====================================================================
-- Q2. Plan vs actual: how much of the approved plan gets done?
-- =====================================================================

-- 2a. Plan completion by rep, with the team average for comparison.
SELECT
    rep_id,
    rep_name,
    territory_id,
    sum(planned)                                                   AS planned,
    sum(planned_done)                                              AS done,
    round(100.0 * sum(planned_done) / sum(planned), 1)             AS completion_pct,
    round(100.0 * sum(planned_done) / sum(planned)
          - 100.0 * sum(sum(planned_done)) OVER () / sum(sum(planned)) OVER (), 1)
                                                                   AS vs_team_pts,
    sum(unplanned)                                                 AS unplanned_visits
FROM analytics.rep_plan_vs_actual
GROUP BY rep_id, rep_name, territory_id
ORDER BY completion_pct;

-- 2b. Which days of the week lose the most planned visits?
WITH plan_status AS (
    SELECT
        p.plan_id,
        extract(isodow FROM p.plan_date)::int AS dow,
        to_char(p.plan_date, 'Dy')          AS weekday,
        EXISTS (SELECT 1 FROM clean.valid_visits v WHERE v.plan_id = p.plan_id) AS done
    FROM raw.visit_plans p
)
SELECT dow, weekday, count(*) AS planned, round(100 * avg(done::int), 1) AS completion_pct
FROM plan_status
GROUP BY dow, weekday
ORDER BY dow;

-- 2c. Completion by month: does the rainy season (Aug-Sep) hurt?
SELECT
    month,
    sum(planned)                                       AS planned,
    round(100.0 * sum(planned_done) / sum(planned), 1) AS completion_pct
FROM analytics.rep_plan_vs_actual
GROUP BY month
ORDER BY month;


-- =====================================================================
-- Q3. Productivity: what does a field day look like?
-- =====================================================================

-- 3a. Average field day per rep.
SELECT
    rep_id,
    rep_name,
    count(*)                                       AS field_days,
    round(avg(visits), 1)                          AS visits_per_day,
    round(avg(avg_visit_min), 1)                   AS avg_visit_min,
    to_char(avg(first_checkin), 'HH24:MI')         AS avg_first_checkin,
    to_char(avg(last_activity), 'HH24:MI')         AS avg_last_activity,
    round(avg(field_hours), 1)                     AS field_hours,
    round(100 * sum(in_store_hours) / sum(field_hours), 1) AS pct_time_in_store,
    round(sum(order_value_thb) / sum(visits))      AS order_value_per_visit_thb
FROM analytics.rep_daily_productivity
GROUP BY rep_id, rep_name
ORDER BY visits_per_day DESC;

-- 3b. Visit length and order strike rate by channel.
SELECT
    channel,
    count(*)                                         AS visits,
    round(percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_min)::numeric, 1) AS median_visit_min,
    round(100 * avg(has_order::int), 1)              AS strike_rate_pct,
    round(avg(order_value_thb) FILTER (WHERE has_order)) AS avg_order_thb
FROM analytics.visits_enriched
WHERE is_valid
GROUP BY channel
ORDER BY strike_rate_pct DESC;


-- =====================================================================
-- Q4. Data quality: how trustworthy is the visit data?
-- =====================================================================

-- 4a. Scorecard.
SELECT issue, visits, out_of, round(100.0 * visits / out_of, 2) AS pct
FROM clean.data_quality_summary;

-- 4b. Data-quality issues per rep: coaching targets.
SELECT
    rep_id,
    rep_name,
    count(*)                                                AS visits,
    round(100 * avg(flag_gps_far::int), 1)                  AS gps_far_pct,
    round(100 * avg(flag_missing_checkout::int), 1)         AS missing_checkout_pct,
    round(100 * avg(coalesce(flag_too_short, false)::int), 1) AS too_short_pct,
    round(100 * avg(flag_no_photo::int), 1)                 AS no_photo_pct
FROM analytics.visits_enriched
GROUP BY rep_id, rep_name
ORDER BY rep_id;


-- =====================================================================
-- Q5. Distributor stock: where does stock run out, and what does it cost?
-- =====================================================================

-- 5a. Stock-outs by distributor and SKU.
SELECT
    agent_id,
    sku_id,
    sku_name,
    count(*) FILTER (WHERE is_stockout)       AS stockout_weeks,
    count(*)                                  AS weeks,
    sum(lost_cases)                           AS lost_cases,
    sum(lost_value_thb)                       AS lost_value_thb,
    round(100.0 * sum(sold_qty) / nullif(sum(demand_qty), 0), 1) AS fill_rate_pct
FROM analytics.stock_weekly
GROUP BY agent_id, sku_id, sku_name
HAVING count(*) FILTER (WHERE is_stockout) > 0
ORDER BY lost_value_thb DESC;

-- 5b. Demand trend by category: which categories are growing?
SELECT
    visit_month,
    category,
    sum(cases)                                          AS cases,
    round(100.0 * sum(cases) / sum(sum(cases)) OVER (PARTITION BY visit_month), 1)
                                                        AS share_of_month_pct
FROM analytics.sales_lines
GROUP BY visit_month, category
ORDER BY visit_month, cases DESC;


-- =====================================================================
-- Q6. Recommendation input: what would full A-store coverage be worth?
-- =====================================================================

-- Average order value per valid visit by grade, and the visits A stores missed.
WITH value_per_visit AS (
    SELECT grade, avg(order_value_thb) AS thb_per_visit
    FROM analytics.visits_enriched
    WHERE is_valid
    GROUP BY grade
),
gap AS (
    SELECT grade, sum(greatest(required_visits - valid_visits, 0)) AS missed_visits
    FROM analytics.store_month_coverage
    GROUP BY grade
)
SELECT
    g.grade,
    g.missed_visits,
    round(v.thb_per_visit)                  AS thb_per_visit,
    round(g.missed_visits * v.thb_per_visit) AS potential_thb_over_period
FROM gap g
JOIN value_per_visit v USING (grade)
ORDER BY g.grade;
