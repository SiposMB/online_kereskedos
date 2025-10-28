from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, jsonify
)

from trade_engine.db import get_db

import click

import numpy as np
import time
# A piacon a részvények értékei adott időegységenként változnak, ilyenkor mindenkinél egyszerre megváltoznak az árfolyamok.
# Ekkor minden kereskedés már az új árfolyamon zajlik, de adunk 10 másodperc türelmi időt, vagyis 10 másodpercig még az előző áron váltunk nekik, mert jófejek vagyunk
# Ez lesz a középárfolyam, e körül fog majd alakulni az egyes kereskedők kínált ára

# Kell az indítástól eltelt idő, ezzel fogom seedelni az árakat
t_interval = 20 # s - 5 percenként van teljes árfolyamváltozás

# Csinálok egy blueprint-et, ami visszaadja az árakat
bp = Blueprint('prices', __name__, url_prefix='/prices')

# Jelenleg az (közép) árfolyam legyen egy random walk, egy drift-el
# Vagyis: dS = alpha * dt + sigma * dW
# Lazily-initialised, server-run-random market params.
# They are constant for all clients during the server process lifetime,
# but will be re-randomised each time the server restarts.
alpha = None
sigma = None

# Use a process-random generator (different on each restart).
_rng = np.random.default_rng()

def init_market_params(num_res):
    """Initialize alpha and sigma for num_res resources if not already set.
    Returns (alpha, sigma) as numpy arrays.
    Call this once you know the number of resources (e.g. in a request: g.num_res).
    """
    global alpha, sigma
    if alpha is None or sigma is None:
        alpha = _rng.random(num_res) * 9 + 2   # uniform in [2,11)
        sigma = _rng.random(num_res) * 8      # uniform in [0,8)
    return alpha, sigma

# A kezdőár legyen teljesen random

# Ezt úgy implementálom, az adatbázisban lesz egy tábla, ami tartalmazza az árakat minden pillanatban.
# Minden lekérésnél először megpróbálom lekérni az aktuális árat, és ha nincs akkor kiszámolom

# --- add this helper ---
def _get_num_res(db):
    """How many traded resources (excluding cash id=1)? Prefer interval 0."""
    # If already set on g, use it
    n = getattr(g, "num_res", None)
    if isinstance(n, int) and n > 0:
        return n

    # Try to infer from prices at interval 0 (created by init_price)
    row = db.execute(
        "SELECT COUNT(DISTINCT resource_id) AS c FROM prices WHERE N_interval = 0"
    ).fetchone()
    try:
        c = int(row["c"]) if row else 0
    except Exception:
        c = int(row[0]) if row else 0

    if c <= 0:
        # Fallback: count distinct resource_ids across the table
        row = db.execute(
            "SELECT COUNT(DISTINCT resource_id) AS c FROM prices"
        ).fetchone()
        try:
            c = int(row["c"]) if row else 0
        except Exception:
            c = int(row[0]) if row else 0

    if c <= 0:
        # Last resort: assume 4 (matches your init_price); you can raise instead
        c = 4

    g.num_res = c  # cache for the current request
    return c


def get_price_difference(seed):
    # Megadja a középárfolyam növekményét
    
    #  Kiszedem a modell paramétereit
    alpha, sigma = init_market_params(g.num_res)

    np.random.seed(seed)
    # Veszek egy fehér zajt ehhez:
    dW = np.random.normal(0, 1, size=g.num_res)    
    
    
    dS = alpha + sigma * dW
    return dS

def _load_prices_for_interval(db, interval):
    rows = db.execute(
        "SELECT resource_id, resource_price FROM prices WHERE N_interval = ? ORDER BY resource_id",
        (int(interval),)
    ).fetchall()
    if not rows:
        return None, None
    n = _get_num_res(db)
    if len(rows) < n:
        return None, None

    prices = []
    ids = []
    for r in rows:
        try:
            ids.append(int(r["resource_id"]))
            prices.append(float(r["resource_price"]))
        except Exception:
            prices.append(float(r[1]))
    return np.array(ids), np.array(prices, dtype=float)

def get_true_price(N_interval):
    target = int(N_interval)
    if target < 0:
        raise ValueError("N_interval must be >= 0")

    db = get_db()
    res_names = db.execute("SELECT id, name resource_name FROM resources").fetchall()
    num_res = _get_num_res(db)        # <-- derive and cache
    ids, prices = _load_prices_for_interval(db, target)

    if prices is not None:

        # Build a lookup of resource id -> resource name
        name_by_id = {}
        for r in res_names:
            try:
                rid = int(r["id"])
                name = r["resource_name"]
            except Exception:
                rid = int(r[0])
                name = r[1]
            name_by_id[rid] = name

        # Make a dict mapping resource name -> price
        price_dict = {}
        if prices is not None and ids is not None:
            for idx, rid in enumerate(ids):
                name = name_by_id.get(int(rid), f"resource_{int(rid)}")
                price_dict[name] = float(prices[idx])
            return price_dict

    # find latest existing interval to step from
    prev = target - 1
    prev_prices = None
    while prev >= 0:
        ids, prev_prices = _load_prices_for_interval(db, prev)
        if prev_prices is not None:
            break
        prev -= 1
    if prev_prices is None:
        raise RuntimeError("No base prices found. Run `flask --app trade_engine init-price` first.")

    # ensure market params sized correctly
    init_market_params(num_res)

    # step forward deterministically per interval
    current = prev
    prices = prev_prices.copy()
    while current < target:
        current += 1
        rng = np.random.default_rng(current)
        dW = rng.normal(0.0, 1.0, size=num_res)
        dS = alpha + sigma * dW
        print("prices:", prices, "dS:", dS)
        prices = prices + dS
        for idx, res_price in enumerate(prices):
            res_id = idx + 2  # 1 is cash
            db.execute(
                "INSERT INTO prices (resource_id, N_interval, resource_price) VALUES (?, ?, ?)",
                (res_id, current, float(res_price))
            )
        db.commit()


    # Build a lookup of resource id -> resource name
    name_by_id = {}
    for r in res_names:
        try:
            rid = int(r["id"])
            name = r["resource_name"]
        except Exception:
            rid = int(r[0])
            name = r[1]
        name_by_id[rid] = name

    # Make a dict mapping resource name -> price
    price_dict = {}
    if prices is not None and ids is not None:
        for idx, rid in enumerate(ids):
            name = name_by_id.get(int(rid), f"resource_{int(rid)}")
            price_dict[name] = float(prices[idx])
    if prices is not None:
        return price_dict

@bp.post("/get_price")
def get_price():
    client_id = int(request.json['id'])
    db = get_db()
    num_res = _get_num_res(db)

    N_interval = int(time.time() // t_interval)
    prices = get_true_price(N_interval)

    # deterministic per (client, interval) vendor deviation
    seed = client_id * max(1, N_interval)
    rng = np.random.default_rng(seed)
    vendor_sigma = rng.random() * 3.0

    keys = list(prices.keys())
    vals = np.floor(np.asarray(list(prices.values())) + rng.normal(0.0, vendor_sigma, size=num_res))
    result = [{"name": k, "vendor_price": float(v)} for k, v in zip(keys, vals)]
    return jsonify(result)


def init_price():
    # Adok egy kezdőárat minden nyersanyagnak
    db = get_db()

    # Kezdőárak
    initial_prices = np.array([
        3,
        4,
        5,
        6
    ])

    # Get the current interval:
    N_interval = time.time() // t_interval

    # Remove any existing initial prices and insert the defaults at interval 0
    db.execute("DELETE FROM prices WHERE N_interval = ?", (N_interval,))
    
    for idx, res_price in enumerate(initial_prices):
        res_id = idx + 2  # resources start at id 2
        db.execute(
            "INSERT INTO prices (resource_id, N_interval, resource_price) VALUES (?, ?, ?)",
            (res_id, N_interval, float(res_price))
        )
    db.commit()
    
# Csinálok egy parancsot amivel a kezdőárakat be tudom állítani
@click.command('init-price')
def init_price_command():
    init_price()
    click.echo('Initialized the prices.')
    
def check_price():
    db = get_db()
    rows = db.execute("SELECT resource_id, resource_price, MAX(N_interval) FROM prices GROUP BY resource_id").fetchall()
    prices = [dict(row) for row in rows]

    return prices

# Ezzel checkolni lehet a jelenlegi árat
@click.command('check-price')
def check_price_command():
    prices = check_price()
    click.echo(prices)

def init_app(app):
    app.cli.add_command(init_price_command)
    app.cli.add_command(check_price_command)


