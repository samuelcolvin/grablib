#!/usr/bin/python
import imp
import sys
from setuptools import setup

description = 'Utility for defining then downloading and preprocessing external static files.'
long_description = description

if 'sdist' in sys.argv:
    import pypandoc
    with open('README.md', 'r') as f:
        text = f.read()
    text = text[:text.find('<!-- end description -->')].strip('\n ')
    long_description = pypandoc.convert(text, 'rst', format='md')

# importing just this file avoids importing the full package with external dependencies which might not be installed
version = imp.load_source('version', 'grablib/version.py')

setup(
    name='grablib',
    version=str(version.VERSION),
    description=description,
    long_description=long_description,
    classifiers=[
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    keywords='css,sass,scss,build,static,download',
    author='Samuel Colvin',
    license='MIT',
    author_email='S@muelColvin.com',
    url='https://github.com/samuelcolvin/grablib',
    packages=['grablib'],
    include_package_data=True,
    zip_safe=True,
    platforms='any',
    entry_points="""
        [console_scripts]
        grablib=grablib.cli:cli
    """,
    test_suite='runtests',
    install_requires=[
        'click>=6.6',
        'csscompressor==0.9.3',
        'jsmin==2.2.1',
        'PyYAML>=3.11',
        'requests>=2.10.0',
    ],
)
