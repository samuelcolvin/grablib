#!/usr/bin/python

import os, re

from setuptools import setup

description = 'Utility for defining and downloading your projects external library files'
docs_file = 'GrabLib/docs.txt'
try:
    long_description = open(docs_file, 'r').read()
except IOError:
    print '%s not found, long_description is short' % docs_file
    long_description = description

setup(name='GrabLib',
    version = '0.02',
    description = description,
    long_description = long_description,
    author = 'Samuel Colvin',
    license = 'MIT',
    author_email = 'S@muelColvin.com',
    url = 'https://github.com/samuelcolvin/GrabLib',
    packages = ['GrabLib'],
    platforms = 'any',
    scripts = ['GrabLib/bin/grablib'],
    install_requires=[
        'termcolor>=1.1.0',
        'six>=1.6.1'
    ],
)