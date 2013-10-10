from flask import render_template
from changes.api.base import MethodView


class IndexView(MethodView):
    def get(self, path=''):
        return render_template('index.html')
