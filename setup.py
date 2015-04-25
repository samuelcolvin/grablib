#!/usr/bin/python

from setuptools import setup
from grablib import VERSION

description = "Utility for defining then downloading, concatenating and minifying your project's external library files"
long_description = open('long_description.rst').read()

setup(
    name='grablib',
    version=str(VERSION),
    description=description,
    long_description=long_description,
    author='Samuel Colvin',
    license='MIT',
    author_email='S@muelColvin.com',
    url='https://github.com/samuelcolvin/grablib',
    packages=['GrabLib'],
    platforms='any',
    scripts=['grablib/bin/grablib'],
    install_requires=[
      'requests>=2.2.1',
      'termcolor>=1.1.0',
      'six>=1.6.1',
      'slimit>=0.8.1',
      'argparse>=1.2.1'
    ],
)
