from werkzeug.middleware.proxy_fix import ProxyFix

from isithot.app import create_app
from isithot.config import Config

app = create_app(Config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
