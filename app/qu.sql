-- =============================
-- Schema migration: incidents upvotes
-- =============================
-- Run with:
--   psql -d klaconnect -f app/qu.sql

-- Add upvotes column to incidentstablenew if missing
ALTER TABLE IF EXISTS incidentstablenew
    ADD COLUMN IF NOT EXISTS upvotes INTEGER NOT NULL DEFAULT 0;

-- Optional: helpful indexes
CREATE INDEX IF NOT EXISTS idx_incidents_status_date ON incidentstablenew(status, datecreated DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_category_date ON incidentstablenew(incidentcategoryid, datecreated DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_upvotes ON incidentstablenew(upvotes DESC);

-- Verify
-- SELECT column_name, data_type FROM information_schema.columns
--   WHERE table_name = 'incidentstablenew' AND column_name = 'upvotes';

-- =============================
-- Activity Logs table
-- =============================
CREATE TABLE IF NOT EXISTS activitylogs (
    id                  text PRIMARY KEY,
    action_type         text,
    module              text,
    userid              text,
    email               text,
    method              text,
    path                text,
    ip                  text,
    user_agent          text,
    status_code         integer,
    request_body_json   text,
    response_body_json  text,
    datecreated         timestamp without time zone DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activitylogs_created  ON activitylogs(datecreated DESC);
CREATE INDEX IF NOT EXISTS idx_activitylogs_user     ON activitylogs(userid);
CREATE INDEX IF NOT EXISTS idx_activitylogs_module   ON activitylogs(module);
CREATE INDEX IF NOT EXISTS idx_activitylogs_action   ON activitylogs(action_type);