from buildbox.web.base_handler import BaseRequestHandler


class BuildListHandler(BaseRequestHandler):
    def get(self):
        return self.render("build_list.html")
