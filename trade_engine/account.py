from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from flasker.db import get_db


bp = Blueprint('account', __name__, url_prefix='/account')


# a simple page that says hello
@bp.route('/')
def account_info():
    return render_template('account.html')

@bp.route("/submit_trade")
def submit_trade():
    return ""