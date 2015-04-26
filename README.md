grablib
=======

[![Build Status](https://travis-ci.org/samuelcolvin/grablib.svg?branch=master)](https://travis-ci.org/samuelcolvin/grablib)
[![Coverage Status](https://coveralls.io/repos/samuelcolvin/grablib/badge.svg?branch=master)](https://coveralls.io/r/samuelcolvin/grablib?branch=master)
[![PyPI Status](https://img.shields.io/pypi/v/grablib.svg?style=flat)](https://pypi.python.org/pypi/grablib)

Copyright (C) 2013-2014 [Samuel Colvin](http://www.scolvin.com) <S@muelColvin.com>

Python tool and library for downloading, concatenating and minifying library files (eg. Javascript and CSS) 
so they don't clog up your repo.

Definition files can either be JSON or Python (see [examples](examples)). So the versions of libraries used in your 
project can be defined in version control without the need for files from external projects.

    usage: grablib [-h] [-t LIBS_ROOT] [-s LIBS_ROOT_SLIM] [-w OVERWRITE]
                   [-p FILE_PERMISSIONS] [-v {0,1,2,3}] [--no-colour]
                   [file-path-or-json]
    
    grablib
    
    Utility for defining then downloading, concatenating and minifying your
    projects external library files eg. Javascript, CSS.
    
    grablib Version: 0.1
    (https://github.com/samuelcolvin/grablib).
    All optional arguments can also be set in the definition file.
    
    positional arguments:
      file-path-or-json     path to JSON or python file or valid JSON string, defaults to "grablib.json".
    
    optional arguments:
      -h, --help            show this help message and exit
      -t LIBS_ROOT, --libs-root LIBS_ROOT
                            Root directory to put downloaded files in, defaults to the working directory.
      -s LIBS_ROOT_SLIM, --libs-root-slim LIBS_ROOT_SLIM
                            Root directory to put slimmed files in, defaults to libs_root.
      -w OVERWRITE, --overwrite OVERWRITE
                            Overwrite existing files, default is not to download a library if the file already exists
      -p FILE_PERMISSIONS, --file-permissions FILE_PERMISSIONS
                            Explicitly set file permission for each file downloaded, eg. 666
      -v {0,1,2,3}, --verbosity {0,1,2,3}
                            Verbosity Level 0 (nothing except errors), 1 (a little), 2 (default), 3 (everything)
      --no-colour           Do not use color term to colourise output

You can also call grablib from inside python:

    import grablib
    
    grablib.grab('path/to/definitions.json|py')

    # or with options overridden
    grablib.grab('path/to/definitions.json|py', verbosity=3)
