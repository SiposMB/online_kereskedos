from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, jsonify
)

from trade_engine.db import get_db

import numpy as np
import time
# A piacon a részvények értékei adott időegységenként változnak, ilyenkor mindenkinél egyszerre megváltoznak az árfolyamok.
# Ekkor minden kereskedés már az új árfolyamon zajlik, de adunk 10 másodperc türelmi időt, vagyis 10 másodpercig még az előző áron váltunk nekik, mert jófejek vagyunk
# Ez lesz a középárfolyam, e körül fog majd alakulni az egyes kereskedők kínált ára

# Kell az indítástól eltelt idő, ezzel fogom seedelni az árakat
t_interval = 300 # s - 5 percenként van teljes árfolyamváltozás

# Csinálok egy blueprint-et, ami visszaadja az árakat
bp = Blueprint('prices', __name__, url_prefix='/prices')

# Jelenleg az (közép) árfolyam legyen egy random walk, egy drift-el
# Vagyis: dS = alpha * dt + sigma * dW

# A kezdőár legyen teljesen random
# true_prices = np.random.rand(g.num_res) * 500 # 0 - 500 pénz


def calc_vendor_price(current_price, seed):
    np.random.seed(seed)
    alpha = np.random.rand(g.num_res) * 5 + 2 
    sigma = np.random.rand(g.num_res) * 9 + 0.5
    # Felfele mennek az árak... - jobb venni dolgokat mint nem

    dW = np.random.normal(0.5, 9, g.num_res)

    
    return current_price + alpha + sigma * dW


@bp.post("/get_price")
def get_price():
    if request.method == 'POST':
        client_id = int(request.json['id'])

        # Az adott kliens egyedi seed-je az intervallumban
        N_interval = time.time() // t_interval
        
        seed = client_id * N_interval

        return jsonify(N_interval, seed)

        # A kliens által kínált ár az ő egyedi zaja, és a középárfolyam
    return ''