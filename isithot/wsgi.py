from werkzeug.middleware.proxy_fix import ProxyFix

from web.isithot.app import create_app
from web.isithot.config import Config

app = create_app(Config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
