from flask import render_template
from buildbox.api.base import MethodView


class IndexView(MethodView):
    def get(self):
        return render_template('index.html')
