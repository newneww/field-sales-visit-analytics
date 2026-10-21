-- Schema for the field-sales visit dataset.
-- Raw tables mirror the generated CSV files one to one; data-quality issues
-- (duplicates, missing check-outs, far-away GPS) are kept on purpose and are
-- handled later in 02_cleaning.sql.
-- Timestamps are Bangkok local time (Asia/Bangkok), stored without a zone.

DROP SCHEMA IF EXISTS raw CASCADE;
CREATE SCHEMA raw;
SET search_path TO raw;

CREATE TABLE territories (
    territory_id   text PRIMARY KEY,
    asm_id         text NOT NULL
);

CREATE TABLE reps (
    rep_id         text PRIMARY KEY,
    rep_name       text NOT NULL,
    nickname       text,
    role           text NOT NULL CHECK (role IN ('Sales Rep', 'ASM')),
    territory_id   text REFERENCES territories,
    manager_id     text REFERENCES reps,
    hire_date      date
);

CREATE TABLE agents (
    agent_id       text PRIMARY KEY,
    agent_name     text NOT NULL,
    territory_id   text NOT NULL REFERENCES territories
);

CREATE TABLE stores (
    store_id         text PRIMARY KEY,
    store_name       text NOT NULL,
    channel          text NOT NULL,
    grade            char(1) NOT NULL CHECK (grade IN ('A', 'B', 'C')),
    territory_id     text NOT NULL REFERENCES territories,
    district         text NOT NULL,
    lat              numeric(9, 6) NOT NULL,
    lng              numeric(9, 6) NOT NULL,
    rep_id           text NOT NULL REFERENCES reps,
    agent_id         text NOT NULL REFERENCES agents,
    owner_name       text,
    phone            text,           -- free text, formats vary on purpose
    location_source  text NOT NULL,  -- 'osm' or 'synthetic'
    created_date     date NOT NULL
);

CREATE TABLE skus (
    sku_id          text PRIMARY KEY,
    sku_name        text NOT NULL,
    category        text NOT NULL,
    pack            text NOT NULL,
    unit_price_thb  numeric(10, 2) NOT NULL
);

CREATE TABLE visit_plans (
    plan_id       text PRIMARY KEY,
    rep_id        text NOT NULL REFERENCES reps,
    store_id      text NOT NULL REFERENCES stores,
    plan_date     date NOT NULL,
    submitted_at  timestamp NOT NULL,
    approved_at   timestamp,
    approved_by   text REFERENCES reps
);

CREATE TABLE visits (
    visit_id      text PRIMARY KEY,
    rep_id        text NOT NULL REFERENCES reps,
    store_id      text NOT NULL REFERENCES stores,
    plan_id       text REFERENCES visit_plans,  -- NULL = unplanned visit
    checkin_at    timestamp NOT NULL,
    checkout_at   timestamp,                    -- NULL = forgot to check out
    checkin_lat   numeric(9, 6) NOT NULL,
    checkin_lng   numeric(9, 6) NOT NULL,
    photo_count   smallint NOT NULL
);

CREATE TABLE order_lines (
    visit_id        text NOT NULL REFERENCES visits,
    sku_id          text NOT NULL REFERENCES skus,
    qty_cases       integer NOT NULL,
    unit_price_thb  numeric(10, 2) NOT NULL,
    amount_thb      numeric(12, 2) NOT NULL,
    PRIMARY KEY (visit_id, sku_id)
);

CREATE TABLE agent_stock (
    week_start    date NOT NULL,   -- Monday of the week
    agent_id      text NOT NULL REFERENCES agents,
    sku_id        text NOT NULL REFERENCES skus,
    opening_qty   integer NOT NULL,
    received_qty  integer NOT NULL,
    demand_qty    integer NOT NULL,  -- cases ordered by stores this week
    sold_qty      integer NOT NULL,  -- cases actually delivered
    closing_qty   integer NOT NULL,
    PRIMARY KEY (week_start, agent_id, sku_id)
);

CREATE INDEX ON visits (rep_id, checkin_at);
CREATE INDEX ON visits (store_id);
CREATE INDEX ON visit_plans (rep_id, plan_date);
