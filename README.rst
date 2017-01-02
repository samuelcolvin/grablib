grablib
=======

|Build Status| |codecov.io| |PyPI Status| |license|

Copyright (C) 2013-2017 Samuel Colvin

Kind of like bower, but in Python, and simpler, and with some more features.

**grablib** can:

* download files from urls, including extracting selectively from zip files.
* create ``.grablib.lock`` which retains hashes of all downloaded files meaning assets can't change unexpectedly.
* compile sass/scss/css using `libsass`_.
* concatenate and minify javascript using `jsmin`_.

Definition files can either be JSON or YAML (see `examples`_).

Installation
------------

grablib requires **python 3.5+**.

.. code::

    pip install grablib[build]

(You can also use simply ``pip install grablib`` to install without build requirements,
this is useful when you're not using grablib for building as it avoids installing
``jsmin`` and ``libsass`` which can be slow.)


CLI Usage
---------

Define your static files thus: (``grablib.yml``)

.. code:: yaml

    download_root: 'static/libs'
    download:
      'http://code.jquery.com/jquery-1.11.3.js': 'js/jquery.js'
      'https://github.com/twbs/bootstrap-sass/archive/v3.3.6.zip':
        'bootstrap-sass-3.3.6/assets/(.+)$': 'bootstrap-sass/'

      'GITHUB/codemirror/CodeMirror/5.8.0/lib/codemirror.js': 'codemirror/'
      # simple scss file to import and compile bootstrap from above,
      # generally this would be in your code
      # this file just reads "@import 'bootstrap-sass/stylesheets/bootstrap';"
      'https://git.io/v1Z5J': 'build_bootstrap.scss'

    debug: true
    build_root: 'static/prod'
    build:
      # delete the entire static/prod directory before building, this is required for sass,
      # and generally safer
      wipe: '.*'
      cat:
        # concatenate jquery and codemirror into "libraries.js"
        # it won't get minified as debug is true, but without that it would
        'libraries.js':
          - 'DL/js/jquery.js'
          - 'DL/codemirror/codemirror.js'
      sass:
        # compile all css, scss and sass files which don't start with _ from the "download_root"
        # into the "css" directory, here that will just be build_bootstrap.scss which will
        # build the whole of bootstrap.
        # debug: true means you'll get map files and a copy of sass files so maps work properly.
        'css': 'DL/'

Then download and build you static files with just:

.. code::

    grablib

Library Usage
-------------

You can also call grablib from python:

.. code:: python

    from grablib import Grab

    grab = Grab('path/to/definitions.json|yml')
    grab.download()
    grab.build()

.. |Build Status| image:: https://travis-ci.org/samuelcolvin/grablib.svg?branch=master
   :target: https://travis-ci.org/samuelcolvin/grablib
.. |codecov.io| image:: http://codecov.io/github/samuelcolvin/grablib/coverage.svg?branch=master
   :target: http://codecov.io/github/samuelcolvin/grablib?branch=master
.. |PyPI Status| image:: https://img.shields.io/pypi/v/grablib.svg?style=flat
   :target: https://pypi.python.org/pypi/grablib
.. |license| image:: https://img.shields.io/pypi/l/grablib.svg
   :target: https://github.com/samuelcolvin/grablib
.. _libsass: https://pypi.python.org/pypi/libsass/0.11.2
.. _jsmin: https://github.com/tikitu/jsmin
.. _examples: examples
