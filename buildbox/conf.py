import os
import os.path

root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

settings = {
    'static_path': os.path.join(root, 'static'),
    'template_path': os.path.join(root, 'templates'),
    'debug': True,
    'database': 'postgresql:///buildbox',
    'koality.url': 'https://build.itc.dropbox.com',
    'koality.api_key': 'he8i7mxdzrocn6rg9qv852occkvpih9b',
}
