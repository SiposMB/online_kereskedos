import sqlite3
from datetime import datetime

import click
from flask import current_app, g


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def fill_dummy_data():
    db = get_db()

    with current_app.open_resource('create_dummy_data.sql') as f:
        db.executescript(f.read().decode('utf8'))


    db.commit()

@click.command('dummy-db')
def fill_dummy_db_command():
    """Feltöltöm az adatbázist kamu adatokkal"""
    fill_dummy_data()
    click.echo('Filled database with dummy data.')

def get_traders():
    db = get_db()

    traders = db.execute(
        "SELECT * FROM traders"
    ).fetchall()
    traders = {row["resource_code"]: row["qty"] for row in traders}

    balance = db.execute(
        "SELECT * FROM accounts_wide",).fetchall()
    balance = {row["resource_code"]: row["qty"] for row in balance}


    return traders, balance

@click.command('print-traders')
def print_traders_command():
    """Feltöltöm az adatbázist kamu adatokkal"""
    traders, _ = get_traders()
    click.echo(traders)

sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(fill_dummy_db_command)
    app.cli.add_command(print_traders_command)