from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, jsonify
)

from trade_engine.db import get_db


bp = Blueprint('account', __name__, url_prefix='/account')


@bp.get("/api/account/<int:account_id>")
def get_account(account_id):
    db = get_db()
    owner = db.execute("SELECT name FROM traders WHERE id = ?", (account_id,)).fetchone()
    if not owner:
        return jsonify({f"error": "Nincs ilyen számla, keresett számla: {account_id}"}), 404
    

    balance = db.execute(
        "SELECT * FROM accounts_wide WHERE trader_id = ?"
        , (account_id,)).fetchone()

    if balance is None:
        return jsonify({f"error": "Nem találtam meg ennek a tradernek a nyersanyagait"}), 404

    balance = dict(balance)


    g.balance = balance
    html = render_template("requests/balance.html")

    return jsonify({"owner_name": owner["name"], "html": html})