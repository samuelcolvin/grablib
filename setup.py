#!/usr/bin/python
import imp
import sys
from setuptools import setup

description = "Utility for defining then downloading, concatenating and minifying your project's external library files"
long_description = description
if 'upload' in sys.argv:
    try:
        import pypandoc
    except ImportError:
        print('unable to import pypandoc, not generating rst long_description')
    else:
        long_description = pypandoc.convert('README.md', 'rst')

# importing just the files avoids importing the full package with external dependencies which might not be installed
version = imp.load_source('version', 'grablib/version.py')

setup(
    name='grablib',
    version=str(version.VERSION),
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
