#!/usr/bin/python

from setuptools import setup
from grablib import VERSION

description = "Utility for defining then downloading, concatenating and minifying your project's external library files"
try:
    import pypandoc
except ImportError:
    print('unable to import pypandoc, not generating rst long_description')
    long_description = description
else:
    long_description = pypandoc.convert('README.md', 'rst')

setup(
    name='grablib',
    version=str(VERSION),
    description=description,
    long_description=long_description,
    author='Samuel Colvin',
    license='MIT',
    author_email='S@muelColvin.com',
    url='https://github.com/samuelcolvin/grablib',
    packages=['grablib'],
    platforms='any',
    scripts=['grablib/bin/grablib'],
    test_suite='runtests',
    install_requires=[
        'requests>=2.3.0',
        'termcolor>=1.1.0',
        'slimit>=0.8.1'
    ],
)
