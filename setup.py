from importlib.machinery import SourceFileLoader
from pathlib import Path
from setuptools import setup

description = 'Utility for defining then downloading and preprocessing external static files.'
THIS_DIR = Path(__file__).resolve().parent
try:
    long_description = (THIS_DIR / 'README.rst').read_text()
except FileNotFoundError:
    long_description = description + '.\n\nSee https://github.com/samuelcolvin/grablib for documentation.'

# importing just this file avoids importing the full package with external dependencies which might not be installed
version = SourceFileLoader('version', 'grablib/version.py').load_module()

setup(
    name='grablib',
    version=version.VERSION,
    description=description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    classifiers=[
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
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
    python_requires='>=3.6',
    entry_points="""
        [console_scripts]
        grablib=grablib.cli:cli
    """,
    install_requires=[
        'click>=6.6',
        'ruamel.yaml>=0.15.37',
        'requests>=2.20',
    ],
    extras_require={
        'build': [
            'jsmin>=2.2.1',
            'libsass>=0.14.4',
        ],
    }
)
