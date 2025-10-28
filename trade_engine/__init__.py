import os

from flask import Flask, render_template, g, jsonify

import time

starttime = time.time()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'trade_engine.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    
    # Add database functionality
    from . import db
    # Hook up everything as defined in db.py
    db.init_app(app)

    from . import account
    app.register_blueprint(account.bp)

    from . import prices
    app.register_blueprint(prices.bp)
    prices.init_app(app)

    @app.route("/")
    def render_app():
        # 4 darab nyersanyagom van
        g.num_res = 4
        g.starttime = starttime
        return render_template("main_page.html")

    return app
