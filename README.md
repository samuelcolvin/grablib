grablib
=======

[![Build Status](https://travis-ci.org/samuelcolvin/grablib.svg?branch=master)](https://travis-ci.org/samuelcolvin/grablib)
[![codecov.io](http://codecov.io/github/samuelcolvin/grablib/coverage.svg?branch=master)](http://codecov.io/github/samuelcolvin/grablib?branch=master)
[![PyPI Status](https://img.shields.io/pypi/v/grablib.svg?style=flat)](https://pypi.python.org/pypi/grablib)

Copyright (C) 2013-2016 Samuel Colvin

Kind of like bower, but in Python, and simpler, and with some more features.

**grablib** can:
* download files from urls, including extracting selectively from zip files.
* compile sass/scss/css using [libsass](https://pypi.python.org/pypi/libsass/0.11.2).
* contatenate and minify javascript using [jsmin](https://bitbucket.org/dcs/jsmin/).

Definition files can either be JSON or YAML (see [examples](examples)).

## CLI Usage

Define your static files thus: (`grablib.yml`)
```yml
download_root: "static/libs"
download:
  "http://code.jquery.com/jquery-1.11.3.js": "js/jquery.js"
  "https://github.com/twbs/bootstrap-sass/archive/v3.3.6.zip":
    "bootstrap-sass-3.3.6/assets/(fonts/bootstrap/.+)": ""
    "bootstrap-sass-3.3.6/assets/(.+)$": "bootstrap-sass/"

  "GITHUB/codemirror/CodeMirror/5.8.0/lib/codemirror.js": "codemirror/"
  # simple file to import and compile bootstrap from above, generally this would be in your code
  "https://gist.githubusercontent.com/samuelcolvin/22116e988b70781696fcdecc597ca94f/raw/build_bootstrap.scss": "/"

build_root: "static/prod"
build:
  cat:
    "libraries.js":
      - "DL/js/jquery.js"
      - "DL/codemirror/codemirror.js"
  sass:
    "css": "DL/"
```

Then download and build you static files with just:

```shell
grablib
```

## Library Usage

You can also call grablib from python:

```python
from grablib import Grab

grab = Grab('path/to/definitions.json|yml')
grab.download()
grab.build()
```
