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
  -- random trader & non-CASH resource
  (SELECT id FROM traders ORDER BY abs(random()) LIMIT 1) AS trader_id,
  (SELECT id FROM resources WHERE code <> 'CASH' ORDER BY abs(random()) LIMIT 1) AS resource_id,
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

-- Make sure every (trader, resource) row exists (including CASH)
INSERT OR IGNORE INTO accounts (trader_id, resource_id, amount)
SELECT t.id, r.id, 0
FROM traders t
CROSS JOIN resources r;

-- ---------- recompute accounts from events ----------
WITH totals AS (
  SELECT
    t.id   AS trader_id,
    r.id   AS resource_id,
    r.code AS code,
    -- quantities come from ledger.amount ± steals; CASH comes from -SUM(cash_paid)
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
    ), 0) AS qty_total,
    COALESCE((
      SELECT -SUM(l2.cash_paid)          -- paying reduces CASH; receiving increases
      FROM ledger l2
      WHERE l2.trader_id = t.id
    ), 0) AS cash_total
  FROM traders t
  CROSS JOIN resources r
)
UPDATE accounts AS a
SET amount = CASE
  WHEN (SELECT code FROM resources WHERE id = a.resource_id) = 'CASH'
    THEN MAX(0, (SELECT cash_total FROM totals
                 WHERE totals.trader_id = a.trader_id
                   AND totals.resource_id = a.resource_id))
  ELSE
    MAX(0, (SELECT qty_total FROM totals
            WHERE totals.trader_id = a.trader_id
              AND totals.resource_id = a.resource_id))
END;


-- Dummy accounts
BEGIN;

-- 0) Make sure every (trader, resource) row exists
INSERT OR IGNORE INTO accounts (trader_id, resource_id, amount)
SELECT t.id, r.id, 0
FROM traders t
CROSS JOIN resources r;

-- 1) Randomize balances per row (CASH gets a bigger random range)
UPDATE accounts
SET amount = CASE (
    SELECT code FROM resources WHERE id = accounts.resource_id
  )
  WHEN 'CASH' THEN abs(random() % 20000) + 1000   -- 1,000 .. 20,999
  ELSE abs(random() % 50) + 1                      -- 1 .. 50
END;

COMMIT;
