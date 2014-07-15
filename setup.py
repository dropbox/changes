#!/usr/bin/env python
"""
changes
========

Magic.

:copyright: (c) 2014 Dropbox, Inc.
"""

from setuptools import setup, find_packages

tests_require = [
    'exam>=0.10.2,<0.11.0',
    'flake8>=2.1.0,<2.2.0',
    'loremipsum>=1.0.2,<1.1.0',
    'mercurial>=2.4',
    'mock>=1.0.1,<1.1.0',
    'pytest>=2.5.0,<2.6.0',
    'pytest-cov>=1.6,<1.7',
    'pytest-timeout>=0.3,<0.4',
    'pytest-xdist>=1.9,<1.10',
    'responses>=0.2.0,<0.3.0',
    'unittest2>=0.5.1,<0.6.0',
    # https://github.com/spulec/moto/archive/master.zip
    'moto',
]

install_requires = [
    'amqp>=1.4.2,<2.0.0',
    'alembic>=0.6.4,<0.7.0',
    'ansi2html>=1.0.5,<1.1.0',
    'anyjson>=0.3.3,<0.4.0',
    'argparse>=1.2.1,<1.3.0',
    'blinker>=1.3,<1.4',
    'boto>=2.25.0,<2.26.0',
    # celery 3.1.9 breaks TrackedTask (wraps is incorrect)
    'celery==3.1.8',
    'kombu>=3.0.8,<4.0.0',
    'enum34>=0.9.18,<0.10.0',
    'flask>=0.10.1,<0.11.0',
    'flask-debugtoolbar>=0.9.0,<0.10.0',
    'flask-mail>=0.9.0,<0.10.0',
    'flask-restful>=0.2.10,<0.2.11',
    'flask-sqlalchemy>=1.0,<1.1',
    'lxml>=3.2.3,<3.3.0',
    'raven>=4.0.4,<4.1.0',
    'redis>=2.8.0,<2.9.0',
    'requests>=2.3.0,<2.4.0',
    'oauth2client>=1.2,<1.3',
    'phabricator>=0.3.0,<0.4.0',
    'psycopg2>=2.5.1,<2.6.0',
    'python-dateutil>=2.1,<2.2',
    'simplejson>=3.3.0,<3.4.0',
    'sqlalchemy==0.9.4',
    'statprof',
    'toronado==0.0.4',
    'uwsgi>=2.0.4,<2.1.0',
]

setup(
    name='changes',
    version='0.1.0',
    author='Dropbox, Inc',
    description='',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires,
    extras_require={'tests': tests_require},
    tests_require=tests_require,
    include_package_data=True,
    classifiers=[
        '__DO NOT UPLOAD__',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
