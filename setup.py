#!/usr/bin/env python
"""
changes
========

Magic.

:copyright: (c) 2013 Dropbox, Inc.
"""

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys

setup_requires = []

if 'test' in sys.argv:
    setup_requires.append('pytest')

tests_require = [
    'exam',
    'flake8',
    'loremipsum',
    'httpretty',
    'mock',
    'pytest',
    'pytest-cov',
    'pytest-timeout',
    'pytest-xdist',
    'responses',
    'unittest2',
]

install_requires = [
    'argparse',
    'alembic',
    'blinker',
    'celery>=3.1,<3.2',
    'enum34',
    'flask',
    'flask-actions',
    'flask-mail',
    'flask-sqlalchemy',
    'gevent',
    'lxml',
    'more-itertools',
    'raven>=3.5.2',
    'redis',
    'requests',
    'oauth2client',
    'phabricator',
    'psycopg2',
    'python-dateutil',
    'simplejson',
    'unicode-slugify',
]


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['tests']
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='changes',
    version='0.1.0',
    author='Dropbox, Inc',
    description='',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
        'tests': tests_require,
    },
    tests_require=tests_require,
    cmdclass={'test': PyTest},
    include_package_data=True,
    classifiers=[
        '__DO NOT UPLOAD__',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
