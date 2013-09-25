from buildbox.web.base_handler import BaseRequestHandler


class IndexHandler(BaseRequestHandler):
    def get(self):
        return self.render('index.html')
