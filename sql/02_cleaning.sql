-- Cleaning layer: one view per raw table that needs fixing.
-- Nothing is deleted from raw; problems are either removed here (duplicates)
-- or flagged so every later query can decide what to do with them.
-- Rerunnable: drops and recreates the clean schema.

DROP SCHEMA IF EXISTS clean CASCADE;
CREATE SCHEMA clean;

-- Required visits per store per month, by grade (the coverage target).
CREATE VIEW clean.grade_targets AS
SELECT * FROM (VALUES ('A', 8), ('B', 4), ('C', 2)) AS t(grade, visits_per_month);

-- Great-circle distance in metres between two points.
CREATE FUNCTION clean.distance_m(lat1 numeric, lng1 numeric, lat2 numeric, lng2 numeric)
RETURNS numeric LANGUAGE sql IMMUTABLE AS $$
    SELECT (2 * 6371000 * asin(sqrt(
        power(sin(radians(lat2 - lat1) / 2), 2)
        + cos(radians(lat1)) * cos(radians(lat2)) * power(sin(radians(lng2 - lng1) / 2), 2)
    )))::numeric
$$;

-- Stores: phone numbers come in several formats ("+66 (0) 7407 8161",
-- "075931034", ...). Normalise to the 10-digit local form 0XXXXXXXXX.
CREATE VIEW clean.stores AS
WITH digits AS (
    SELECT s.*, regexp_replace(phone, '\D', '', 'g') AS phone_digits
    FROM raw.stores s
)
SELECT
    store_id, store_name, channel, grade, territory_id, district,
    lat, lng, rep_id, agent_id, owner_name,
    CASE
        WHEN phone_digits LIKE '660%' THEN substr(phone_digits, 3)        -- +66 (0) ...
        WHEN phone_digits LIKE '66%'  THEN '0' || substr(phone_digits, 3) -- +66 ...
        ELSE phone_digits
    END AS phone,
    location_source, created_date
FROM digits;

-- Visits: drop duplicate submissions, then flag the remaining problems.
-- A duplicate is a second check-in by the same rep at the same store within
-- 2 minutes of the previous one.
CREATE VIEW clean.visits AS
WITH ordered AS (
    SELECT
        v.*,
        lag(checkin_at) OVER (PARTITION BY rep_id, store_id ORDER BY checkin_at, visit_id) AS prev_checkin_at
    FROM raw.visits v
),
deduped AS (
    SELECT * FROM ordered
    WHERE prev_checkin_at IS NULL OR checkin_at - prev_checkin_at > interval '2 minutes'
)
SELECT
    d.visit_id,
    d.rep_id,
    d.store_id,
    d.plan_id,
    d.plan_id IS NOT NULL                                           AS is_planned,
    d.checkin_at,
    d.checkout_at,
    d.checkin_at::date                                              AS visit_date,
    round(extract(epoch FROM d.checkout_at - d.checkin_at) / 60, 1) AS duration_min,
    round(clean.distance_m(s.lat, s.lng, d.checkin_lat, d.checkin_lng)) AS distance_from_store_m,
    d.photo_count,
    clean.distance_m(s.lat, s.lng, d.checkin_lat, d.checkin_lng) > 300 AS flag_gps_far,
    d.checkout_at IS NULL                                           AS flag_missing_checkout,
    d.checkout_at - d.checkin_at < interval '2 minutes'             AS flag_too_short,
    d.photo_count = 0                                               AS flag_no_photo
FROM deduped d
JOIN raw.stores s USING (store_id);

-- A visit counts towards coverage only when the rep was really at the store
-- and stayed a meaningful time. A missing check-out alone does not void it.
CREATE VIEW clean.valid_visits AS
SELECT * FROM clean.visits
WHERE NOT flag_gps_far
  AND NOT coalesce(flag_too_short, false);

-- How many rows each check caught: the data-quality scorecard.
CREATE VIEW clean.data_quality_summary AS
SELECT 'duplicate submission' AS issue,
       (SELECT count(*) FROM raw.visits) - (SELECT count(*) FROM clean.visits) AS visits,
       (SELECT count(*) FROM raw.visits) AS out_of
UNION ALL
SELECT 'GPS > 300 m from store', count(*) FILTER (WHERE flag_gps_far), count(*) FROM clean.visits
UNION ALL
SELECT 'missing check-out', count(*) FILTER (WHERE flag_missing_checkout), count(*) FROM clean.visits
UNION ALL
SELECT 'visit under 2 minutes', count(*) FILTER (WHERE flag_too_short), count(*) FROM clean.visits
UNION ALL
SELECT 'no photo', count(*) FILTER (WHERE flag_no_photo), count(*) FROM clean.visits;
