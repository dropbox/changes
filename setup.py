#!/usr/bin/env python
"""
buildbox
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
    'flake8',
    'mock',
    'pytest',
]

install_requires = [
    'alembic',
    'enum34',
    'futures',
    'tornado',
    'requests',
    'psycopg2',
    'simplejson',
]


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='buildbox',
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
