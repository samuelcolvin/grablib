grablib
=======

|Build Status| |codecov.io| |PyPI Status| |license|

Copyright (C) 2013-2016 Samuel Colvin

Kind of like bower, but in Python, and simpler, and with some more features.

**grablib** can:

* download files from urls, including extracting selectively from zip files.
* compile sass/scss/css using `libsass`_.
* concatenate and minify javascript using `jsmin`_.

Definition files can either be JSON or YAML (see `examples`_).

CLI Usage
---------

Define your static files thus: (``grablib.yml``)

.. code:: yaml

    download_root: "static/libs"
    download:
      "http://code.jquery.com/jquery-1.11.3.js": "js/jquery.js"
      "https://github.com/twbs/bootstrap-sass/archive/v3.3.6.zip":
        "bootstrap-sass-3.3.6/assets/(.+)$": "bootstrap-sass/"

      "GITHUB/codemirror/CodeMirror/5.8.0/lib/codemirror.js": "codemirror/"
      # simple file to import and compile bootstrap from above, generally this would be in your code
      "https://gist.githubusercontent.com/samuelcolvin/22116e988b70781696fcdecc597ca94f/raw/build_bootstrap.scss": "/"

    debug: true
    build_root: "static/prod"
    build:
      cat:
        "libraries.js":
          - "DL/js/jquery.js"
          - "DL/codemirror/codemirror.js"
      sass:
        "css": "DL/"

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
.. _jsmin: https://bitbucket.org/dcs/jsmin/
.. _examples: examples
