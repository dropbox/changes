"""Sets up webassets environment so that static bundles can be pre-built.

Changes by default, generates bundled css files on the first request using flask-assets.
The webassets CLI allows them to be generated manually beforehand. This module is required
by the webassets CLI for building web assets.
Example usage: `env/bin/webassets -m changes.webassets_env build`

These bundle definitions are gotten from webapp/html/webapp.html.
"""
from flask_assets import Bundle

from changes.config import create_app, configure_assets

app = create_app()
environment = configure_assets(app)
environment.register("css", Bundle("css/bundle_definition.less",
                                   filters="less",
                                   output="dist/bundled.css",
                                   depends=["**/*.less", "css/bundle_definition.less"]))
environment.register("colorblind_css", Bundle("css/bundle_definition_colorblind.less",
                                              filters="less",
                                              output="dist/bundled_colorblind.css",
                                              depends=["**/*.less", "css/bundle_definition_colorblind.less"]))

if app.config['WEBAPP_CUSTOM_CSS']:
    environment.register("css_custom", Bundle("css/bundle_definition_custom.less",
                                              filters="less",
                                              output="dist/bundled_with_custom.css",
                                              depends=["**/*.less", "custom/**/*.less"]))
    environment.register("colorblind_css_custom", Bundle("css/bundle_definition_custom_colorblind.less",
                                                         filters="less",
                                                         output="dist/bundled_with_custom_colorblind.css",
                                                         depends=["**/*.less", "custom/**/*.less"]))
