import flask


def create_app(**config):
    app = flask.Flask(__name__)
    app.config['DEBUG'] = True
    app.config['HTTP_PORT'] = 5000
    app.config.update(config)
    return app


app = create_app()

# register views
import buildbox.web.frontend  # NOQA
