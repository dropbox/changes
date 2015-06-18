from flask import current_app as app, Response
from flask.helpers import send_from_directory
from flask.views import MethodView
import mimetypes


class StaticView(MethodView):
    # hacky_vendor_root: if present and the url starts with vendor/, use that root
    # instead. Used because the new ui uses vendor libraries stored in the
    # original dir
    def __init__(self, root, hacky_vendor_root=None, cache_timeout=0):
        self.root = root
        self.hacky_vendor_root = hacky_vendor_root
        self.cache_timeout = app.config['SEND_FILE_MAX_AGE_DEFAULT']

    def get(self, filename):
        root = self.root

        if filename.startswith("vendor/") and self.hacky_vendor_root:
            root = self.hacky_vendor_root

        # We do this in debug to work around http://stackoverflow.com/q/17460463/871202
        # By reading the file into memory ourselves, we seem to avoid hitting that
        # VirtualBox issue in dev. In prod, it's unchanged and we just send_from_directory
        if app.debug:
            full_name = root + "/" + filename

            if filename:
                mimetype = mimetypes.guess_type(filename)[0]
            else:
                mimetype = 'application/octet-stream'
            return Response(
                open(full_name),
                mimetype=mimetype,
                headers={
                    "Content-Disposition": "filename=" + filename
                }
            )
        else:
            return send_from_directory(
                root, filename, cache_timeout=self.cache_timeout)
