.. :changelog:

History
-------

0.7.2 (2018-04-16)
------------------
* allow custom function mapping for sass generation

0.7.1 (2018-04-08)
------------------
* tweak hash insertion
* correct deploy tag name

0.7.0 (2018-04-08)
------------------
* uprev
* tweak type annotations
* add hash insertion in output names to sass generation
* drop support for python 3.5

0.6.1 (2017-07-12)
------------------
* uprev
* propagate false on logs

0.6.0 (2017-04-18)
------------------
* allow node module resolution of sass imports via ``NM/``
* add size display to sass generation

0.5.2 (2017-02-03)
------------------
* using prettier arrow in logs :-)

0.5.1 (2017-01-17)
------------------
* fix ``--debug vs/ --no-debug``
* fix replace with debug
* add ``DL/`` and ``SRC/`` clever sass import prefixes

0.5.0 (2017-01-14)
------------------
* git tag check on build
* add ``replace`` argument to ``build > sass`` to allow output files to be modified
  with regex find & replace statements.
* adding support for deleting stale files defined in ``.grablib.lock``

0.4.0 (2017-01-02)
------------------
* Add ``build`` extra requirement for setup
* overhall logging
* switch ``verbosity`` cli option to ``--verbose/--quiet``
* package updates

0.3.0 (2016-12-01)
------------------
* lots of major changes
* add ``.grablib.lock``
* move to sass css compilation
