import os

import sentry_sdk
from flask import Flask
from flask_babel import Babel
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


def create_app(config: object) -> Flask:
    """create and configure the isithot Flask application.

    :param config: Configuration object to use for the Flask app.

    :return: Configured Flask application instance.
    """
    sentry_sdk.init(
        dsn=os.environ.get('MONITOR_SENTRY_DSN'),
        integrations=[FlaskIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=float(
            os.environ.get('MONITOR_SENTRY_SAMPLE_RATE', 0.0),
        ),
    )

    app = Flask(__name__)
    app.config.from_object(config)

    from isithot.cache import cache
    cache.init_app(app)

    from isithot.blueprints.isithot import isithot
    from isithot.blueprints.isithot import get_locale

    app.register_blueprint(isithot)
    Babel(app, locale_selector=get_locale)

    return app


if __name__ == '__main__':
    from isithot.config import Config

    app = create_app(Config)
    app.run(debug=True)
