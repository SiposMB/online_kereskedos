PRAGMA foreign_keys = ON;

-- ---------- parameters ----------
WITH params(num_traders, num_trades, num_steals) AS (VALUES (20, 400, 60))
-- ---------- clear old data ----------
DELETE FROM steals;
DELETE FROM ledger;
DELETE FROM accounts;
DELETE FROM traders;

-- ---------- create traders ----------
;
WITH
  params(num_traders, num_trades, num_steals) AS (VALUES (20, 400, 60)),
  seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n+1 FROM seq, params WHERE n < params.num_traders
  )
INSERT INTO traders(name)
SELECT printf('Trader %03d', n) FROM seq;

-- If you keep cash per trader, uncomment the next line once (schema change):
--ALTER TABLE traders ADD COLUMN cash INTEGER NOT NULL DEFAULT 0;

-- ---------- ensure accounts matrix (all traders × all resources) ----------
-- INSERT INTO accounts (trader_id, resource_id, amount)
-- SELECT t.id, r.id, 0
-- FROM traders t
-- CROSS JOIN resources r
-- ON CONFLICT(trader_id, resource_id) DO NOTHING;

-- ---------- random ledger (buys/sells) ----------

WITH
  params(num_traders, num_trades, num_steals) AS (VALUES (20, 400, 60)),
  seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n+1 FROM seq, params WHERE n < params.num_trades
  )
INSERT INTO ledger (trader_id, resource_id, cash_paid, amount, trade_time)
SELECT
  -- random trader & resource
  (SELECT id FROM traders ORDER BY abs(random()) LIMIT 1) AS trader_id,
  (SELECT id FROM resources ORDER BY abs(random()) LIMIT 1) AS resource_id,
  -- buy or sell
  CASE abs(random()) % 2
    WHEN 0 THEN  -- BUY: acquire qty>0, pay cash>0
      ((abs(random()) % 46) + 5) * ((abs(random()) % 9) + 1)   -- price * qty
    ELSE         -- SELL: give qty<0, receive cash<0
      -((abs(random()) % 46) + 5) * ((abs(random()) % 9) + 1)
  END AS cash_paid,
  CASE abs(random()) % 2
    WHEN 0 THEN  ((abs(random()) % 9) + 1)   -- BUY qty>0
    ELSE         -((abs(random()) % 9) + 1)  -- SELL qty<0
  END AS amount,
  datetime('now', printf('-%d hours', abs(random() % 720))) AS trade_time;

-- ---------- random steals ----------
;
WITH
  params(num_traders, num_trades, num_steals) AS (VALUES (20, 400, 60)),
  seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n+1 FROM seq, params WHERE n < params.num_steals
  ),
  pairs AS (
    SELECT
      (SELECT id FROM traders ORDER BY abs(random()) LIMIT 1) AS a,
      (SELECT id FROM traders ORDER BY abs(random()) LIMIT 1) AS b
    FROM seq
  )
INSERT INTO steals (stealer_id, stolen_from_id, resource_id, amount, steal_time)
SELECT
  CASE WHEN a=b THEN (SELECT id FROM traders t ORDER BY abs(random()) LIMIT 1) ELSE a END AS stealer_id,
  CASE WHEN a=b THEN (SELECT id FROM traders t ORDER BY abs(random()) LIMIT 1) ELSE b END AS stolen_from_id,
  (SELECT id FROM resources ORDER BY abs(random()) LIMIT 1) AS resource_id,
  (abs(random()) % 5) + 1 AS amount,
  datetime('now', printf('-%d hours', abs(random() % 720))) AS steal_time
FROM pairs;

-- ---------- recompute accounts from events ----------
WITH totals AS (
  SELECT
    t.id   AS trader_id,
    r.id   AS resource_id,
    COALESCE((
      SELECT SUM(l.amount)
      FROM ledger l
      WHERE l.trader_id = t.id AND l.resource_id = r.id
    ), 0) +
    COALESCE((
      SELECT SUM(s.amount)
      FROM steals s
      WHERE s.stealer_id = t.id AND s.resource_id = r.id
    ), 0) -
    COALESCE((
      SELECT SUM(s2.amount)
      FROM steals s2
      WHERE s2.stolen_from_id = t.id AND s2.resource_id = r.id
    ), 0) AS total_amount
  FROM traders t
  CROSS JOIN resources r
)
UPDATE accounts AS a
SET amount = (
  SELECT total_amount
  FROM totals
  WHERE totals.trader_id = a.trader_id
    AND totals.resource_id = a.resource_id
);

-- ---------- (optional) recompute traders.cash if column exists ----------
-- cash change is negative of cash_paid (paying reduces cash, receiving increases)
UPDATE traders
SET cash = cash - COALESCE((
  SELECT SUM(cash_paid)
  FROM ledger l
  WHERE l.trader_id = traders.id
), 0)
WHERE EXISTS (SELECT 1 FROM pragma_table_info('traders') WHERE name='cash');
