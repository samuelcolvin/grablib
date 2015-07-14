grablib
=======

[![Build Status](https://travis-ci.org/samuelcolvin/grablib.svg?branch=master)](https://travis-ci.org/samuelcolvin/grablib)
[![Coverage Status](https://coveralls.io/repos/samuelcolvin/grablib/badge.svg?branch=master)](https://coveralls.io/r/samuelcolvin/grablib?branch=master)
[![PyPI Status](https://img.shields.io/pypi/v/grablib.svg?style=flat)](https://pypi.python.org/pypi/grablib)

Copyright (C) 2013-2015 Samuel Colvin

Python tool and library for downloading, concatenating and minifying static files. Minification works with both
javascript via [jsmin](https://bitbucket.org/dcs/jsmin/) and 
css via [csscompressor](https://github.com/sprymix/csscompressor).

Definition files can either be JSON or Python (see [examples](examples)). So the versions of libraries 
used in your project can be defined in version control without the need for files from external projects.

Define your static files thus: (`grablib.json`)
```json
{
  "libs_root": "static_files",
  "sites":
  {
    "github": "https://raw.githubusercontent.com",
    "typeahead": "{{ github }}/twitter/typeahead.js/v0.10.2/dist"
  },
  "libs":
  {
    "{{ typeahead }}/typeahead.jquery.js": "js/ta_raw/{{ filename }}",
    "{{ typeahead }}/bloodhound.js": "js/ta_raw/{{ filename }}",
    "{{ github }}/twbs/bootstrap/v3.3.5/dist/css/bootstrap.min.css": "{{ filename }}",
    "{{ github }}/twbs/bootstrap/v3.3.5/dist/js/bootstrap.min.js": "{{ filename }}"
  },
  "minify_libs_root": "static_files/minified",
  "minify":
  {
    "typeahead_combined.min.js": [".*/ta_raw/.*"]
  }
}
```

Then download and minify you static files with just:

```shell
grablib
```

You can also call grablib from python:

```python
import grablib

grablib.grab('path/to/definitions.json|py')

# or with options overridden
grablib.grab('path/to/definitions.json|py', verbosity=3)
```
