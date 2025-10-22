-- schema.sql

PRAGMA foreign_keys = ON;

-- Drop in correct dependency order
DROP TABLE IF EXISTS steals;
DROP TABLE IF EXISTS ledger;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS resources;
DROP TABLE IF EXISTS traders;

-- Traders
CREATE TABLE traders (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

-- Resources catalog
CREATE TABLE resources (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  code  TEXT NOT NULL UNIQUE,   -- short symbol, e.g. WOOD
  name  TEXT NOT NULL
);

-- Seed resources (remove the Python list, this is pure SQL)
INSERT INTO resources (code, name) VALUES
  ("CASH", "Cash")
  ('WOOD',  'Wood'),
  ('STONE', 'Stone'),
  ('IRON',  'Iron'),
  ('FOOD',  'Food');

-- Accounts: normalized balances (one row per trader per resource)
-- You can keep 'cash' per trader in a separate table; here we keep it in traders for simplicity.
-- If you prefer per-trader cash, uncomment the cash column below and add triggers/updates accordingly.
-- ALTER TABLE traders ADD COLUMN cash INTEGER NOT NULL DEFAULT 0;
-- (Or keep a separate balances table for cash as resource-like.)

CREATE TABLE accounts (
  trader_id   INTEGER NOT NULL,
  resource_id INTEGER NOT NULL,
  amount      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (trader_id, resource_id),
  FOREIGN KEY (trader_id)   REFERENCES traders(id)   ON DELETE CASCADE,
  FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE RESTRICT,
  CHECK (amount >= 0)
);

-- Trades ledger
CREATE TABLE ledger (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  trader_id   INTEGER NOT NULL,
  resource_id INTEGER NOT NULL,
  cash_paid   INTEGER NOT NULL,   -- positive means paid, negative means received
  amount      INTEGER NOT NULL,   -- positive means acquired, negative means sold
  trade_time  TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (trader_id)   REFERENCES traders(id)   ON DELETE CASCADE,
  FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE RESTRICT
);

-- Steals log
CREATE TABLE steals (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  stealer_id     INTEGER NOT NULL,
  stolen_from_id INTEGER NOT NULL,
  resource_id    INTEGER NOT NULL,
  amount         INTEGER NOT NULL CHECK (amount > 0),
  steal_time     TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (stealer_id)     REFERENCES traders(id)   ON DELETE CASCADE,
  FOREIGN KEY (stolen_from_id) REFERENCES traders(id)   ON DELETE CASCADE,
  FOREIGN KEY (resource_id)    REFERENCES resources(id) ON DELETE RESTRICT
);

-- Optional: a convenience VIEW that pivots accounts into wide columns per resource.
-- This gives you columns WOOD, STONE, IRON, FOOD without denormalizing storage.
CREATE VIEW accounts_wide AS
WITH base AS (
  SELECT
    t.id   AS trader_id,
    t.name AS trader_name,
    r.code,
    a.amount
  FROM traders t
  JOIN accounts a ON a.trader_id = t.id
  JOIN resources r ON r.id = a.resource_id
)
SELECT
  trader_id,
  trader_name,
  COALESCE(MAX(CASE WHEN code = 'CASH'  THEN amount END), 0) AS CASH,
  COALESCE(MAX(CASE WHEN code = 'WOOD'  THEN amount END), 0) AS WOOD,
  COALESCE(MAX(CASE WHEN code = 'STONE' THEN amount END), 0) AS STONE,
  COALESCE(MAX(CASE WHEN code = 'IRON'  THEN amount END), 0) AS IRON,
  COALESCE(MAX(CASE WHEN code = 'FOOD'  THEN amount END), 0) AS FOOD
FROM base
GROUP BY trader_id, trader_name;
