GrabLib
=======

Copyright (C) 2013-2014 [Samuel Colvin](http://www.scolvin.com) <S@muelColvin.com>

Python tool and library for downloading, concatenating and minifying library files (eg. Javascript and CSS) so they don't clog up your repo.

Definition files can either be JSON or Python (see [examples](examples)). So the versions of libraries used in your project can be defined in version control without the need for files from external projects.

The formats define the same things, the following values can be set:

* **libs:** a dictionary of files to download and locations to put them, zip files may also be defined with multiple files extracted to different locations. If not specified nothing is downloaded.

* **slim:** Dictionary defining which files to concatenate and optionally minify using [slimit](https://github.com/rspivak/slimit). See examples for details.

* **libs_root:** Root directory to put downloaded files in, defaults to the working directory.

* **libs_root_slim:** Root directory to put slimmed files in, defaults to **libs_root**.

* **verbosity:** Level 0 (nothing except errors), 1 (a little),  2 (default), 3 (everything).

* **overwrite:** bool, whether or not to overwrite files that already exist, default is not to download existing.

* **file_permissions:** Explicitly set files' permissions.

* **sites:** Dictionary of site names to generate urls to avoid repeating `https://raw.githubusercontent.com` lots of times.

All options settings (except sites) can also be overwritten at the command line, in python format or using the API a special output function may also be defined.

You can also call GrabLib from inside python:

    import GrabLib
    GrabLib.process_file('path/to/definitions.json|py')

    # or with options overridden

    op_overide = GrabLib.EMPTY_OPTIONS
    op_overide['verbosity'] = 3
    GrabLib.process_file('path/to/definitions.json|py', op_overide)

Package available [on pip](https://pypi.python.org/pypi/GrabLib), source available [on github](https://github.com/samuelcolvin/GrabLib).
