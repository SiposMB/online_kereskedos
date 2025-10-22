from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, jsonify
)

from trade_engine.db import get_db


bp = Blueprint('account', __name__, url_prefix='/account')


@bp.route('/')
def account_info():
    return render_template('account.html')

@bp.route("/submit_trade")
def submit_trade():
    return ""

@bp.get("/api/account/<int:account_id>")
def get_account(account_id):
    db = get_db()
    owner = db.execute("SELECT name FROM traders WHERE id = ?", (account_id,)).fetchone()
    if not owner:
        return jsonify({"error": "Nincs ilyen számla"}), 404
    


    # 

    balance = db.execute(
        "SELECT * FROM accounts_wide WHERE trader_id = ?"
        , (account_id,)).fetchone()


    g.balance = {row["resource_code"]: row["qty"] for row in balance}
    html = render_template("")

    return jsonify({"owner_name": owner["name"], "html": html})