GrabLib
=======

Python tool and library for downloading library files (eg. Javascript and CSS) so they don't clog up your repo.

Definition files can either be JSON or Python (see `/examples`). So the versions of libraries used in your project can be defined in version control without the need to include them all and clog things up.

The formats define the sames things, the following values can be set:
* **libs:** a dictionary of files to download and locations to put them, zip files may also be defined with multiple files extracted to different locations.
* **[OPTIONAL] libs_root:** the location to put the files, defaults to the working directory.
* **[OPTIONAL] verbosity:** Level 0 (nothing except errors), 1 (less),  2 (default), 3 (everything)
* **[OPTIONAL] overwrite:** bool, whether or not to overwrite files that already exist, default is not to download existing
* **[OPTIONAL] file_permissions:** explitly set files permissions
* **[OPTIONAL] sites:** dictionary of site names to urls to avoid repeating `https://raw.githubusercontent.com` many times.

All options settings (except sites) can also be overwritten at the command line, in python format or using the API a special output function may also be defined.

### TODO

* add javascript/css concatination and compression
* dry-run mode where links are check, zip files are opened but files are not actually put into place
* DONE try out coloured term with https://pypi.python.org/pypi/colorterm
* add example of getting local file with file:///home/samuel/...
* DONE add note on target at the beginning
* DONE decode json to an OrderedDict to maintain download order
* DONE add domain options so "http://github..." is written once
* DONE give better error if JSON can't be read
