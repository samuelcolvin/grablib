import builtins
import pytest
from pytest_toolbox import gettree, mktree

from grablib import Grab
from grablib.common import GrablibError, setup_logging


real_import = builtins.__import__


def mocked_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name in {'jsmin', 'sass'}:
        raise ImportError('fake error for %s' % name)
    return real_import(name, globals, locals, fromlist, level)


def test_cat(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        download:
          http://whatever.com/file: file.txt
        build_root: "built_at"
        build:
          cat:
            "libs.min.js":
              - "./foo.js"
              - "./bar.js"
        """,
        'foo.js': 'var v = "foo js";\n    vindent = true;',
        'bar.js': 'var v = "bar js";',
    })
    Grab().build()
    assert gettree(tmpworkdir.join('built_at')) == {
        'libs.min.js':
            '/* === foo.js === */\n'
            'var v="foo js";vindent=true;\n'
            '/* === bar.js === */\n'
            'var v="bar js";\n'
    }


def test_cat_debug(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          cat:
            "libraries.js":
              - "./foo.js"
              - "./bar.js"
        """,
        'foo.js': 'var v = "foo js";\n    vindent = true;',
        'bar.js': 'var v = "bar js";',
    })
    Grab(debug=True).build()
    assert {
        'libraries.js':
            '/* === foo.js === */\n'
            'var v = "foo js";\n'
            '    vindent = true;\n'
            '/* === bar.js === */\n'
            'var v = "bar js";\n'
    } == gettree(tmpworkdir.join('built_at'))


def test_cat_none(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          cat:
            "libs.min.js": []
        """
    })
    Grab().build()
    assert tmpworkdir.join('built_at').check() is False


def test_cat_src_wrong(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          cat:
            "libs.min.js": not_a_list
        """
    })
    with pytest.raises(GrablibError):
        Grab().build()


def test_cat_download_root(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        download_root: downloaded2
        build_root: "built_at"
        build:
          cat:
            "f.min.js":
              - "./foo.js"
              - "DL/bar.js"
        """,
        'foo.js': 'var v = "foo js";',
        'downloaded2/bar.js': 'var v = "bar js";',
    })
    Grab().build()
    assert gettree(tmpworkdir.join('built_at')) == {
        'f.min.js':
            '/* === foo.js === */\n'
            'var v="foo js";\n'
            '/* === bar.js === */\n'
            'var v="bar js";\n'
    }


def test_cat_regex(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          cat:
            "f.min.js":
              - src: "./foo.js"
                replace:
                  "change": "!new_value"
        """,
        'foo.js': 'var v = "change js";',
    })
    Grab().build()
    assert gettree(tmpworkdir.join('built_at')) == {
        'f.min.js':
            '/* === foo.js === */\n'
            'var v="!new_value js";\n'
    }


def test_sass(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          sass:
            "css": "sass_dir"
        """,
        'sass_dir': {
            'not_css.txt': 'not included',
            'adir/_mixin.scss': 'a { color: red};',
            'foo.scss': """
            @import 'adir/mixin';
            .foo {
              .bar {
                color: black;
                width: (60px / 6);
              }
            }
            """
        }
    })
    Grab().build()
    assert gettree(tmpworkdir.join('built_at')) == {
        'css': {
            'foo.css': 'a{color:red}.foo .bar{color:black;width:10px}\n'
        }
    }


def test_sass_exclude(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: 'built_at'
        build:
          sass:
            css:
              src: sass_dir
              exclude: 'adir/.*$'
        """,
        'sass_dir': {
            'adir/bar.scss': '.bar { color: red};',
            'foo.scss': '.foo { color: black;}'
        }
    })
    Grab().build()
    assert gettree(tmpworkdir.join('built_at')) == {
        'css': {
            'foo.css': '.foo{color:black}\n'
        }
    }


def test_sass_debug(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        debug: true
        build:
          sass:
            "css": "sass_dir"
        """,
        'sass_dir': {
            'foo.scss': '.foo { .bar {color: black;}}'
        }
    })
    Grab().build()
    tree = gettree(tmpworkdir.join('built_at/css'))
    foo_map = tree.pop('foo.map')
    assert {
        'foo.css': '.foo .bar {\n  color: black; }\n\n/*# sourceMappingURL=foo.map */',
        '.src': {
            'foo.scss': '.foo { .bar {color: black;}}'
        }
    } == tree
    assert foo_map.startswith('{\n\t"version": 3,\n\t"file": ".src/foo.css"')


def test_sass_debug_src_exists(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: 'built_at'
        debug: true
        build:
          sass:
            'css': 'sass_dir'
        """,
        'sass_dir': {
            'foo.scss': '.foo { .bar {color: black;}}'
        },
        'built_at/css/.src': {},
    })
    with pytest.raises(GrablibError) as excinfo:
        Grab().build()
    assert excinfo.value.args[0].startswith('With debug switched on the directory "')


def test_sass_error(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          sass:
            "css": "sass_dir"
        """,
        'sass_dir': {
            'foo.scss': '.foo { WRONG'
        }
    })
    with pytest.raises(GrablibError):
        Grab().build()


def test_rm_all(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          wipe: '.*'
        """,
        'built_at': {
            'foo/bar.js': 'x',
            'boom.txt': 'x',
        }
    })
    Grab().build()
    assert gettree(tmpworkdir.join('built_at')) == {}


def test_rm_some(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          wipe:
          - boom.txt
          - another_dir.*
        """,
        'built_at': {
            'foo/bar.js': 'x',
            'boom.txt': 'x',
            'another_dir': {
                'a.txt': 'x',
                'b.txt': 'x',
            },
            'remain.txt': 'y',
        }
    })
    setup_logging('DEBUG')
    Grab().build()
    assert {
        'foo': {
            'bar.js': 'x'
        },
        'remain.txt': 'y',
    } == gettree(tmpworkdir.join('built_at'))


def test_jsmin_import_error(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          cat:
            "libs.min.js":
              - "./bar.js"
        """,
        'bar.js': 'var v = "bar js";',
    })
    mock_import = mocker.patch('builtins.__import__')
    mock_import.side_effect = mocked_import
    with pytest.raises(GrablibError) as exc_info:
        Grab().build()
    assert exc_info.value.args[0] == ('Error importing jsmin. Build requirements probably not installed, '
                                      'run `pip install grablib[build]`')


def test_sass_import_error(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          sass:
            "css": "sass_dir"
        """,
        'sass_dir': {
            'adir/test.scss': 'a { color: red};',
        }
    })
    mock_import = mocker.patch('builtins.__import__')
    mock_import.side_effect = mocked_import
    with pytest.raises(GrablibError) as exc_info:
        Grab().build()
    assert exc_info.value.args[0] == ('Error importing sass. Build requirements probably not installed, '
                                      'run `pip install grablib[build]`')


def test_sass_replace(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: built_at
        debug: false
        build:
          sass:
            css:
              src: sass_dir
              replace:
                "foo.scss$":
                  black: white
                  'black;': "shouldn't change"
        """,
        'sass_dir': {
            'foo.scss': '.foo { .bar {color: black;}}',
            'bar.scss': 'a {color: black;}',
        }
    })
    Grab().build()
    assert {
        'foo.css': '.foo .bar{color:white}\n',
        'bar.css': 'a{color:black}\n',
    } == gettree(tmpworkdir.join('built_at/css'))


def test_sass_clever_import(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        download_root: downloaded2
        build_root: built_at
        debug: false
        build:
          sass:
            css: sass_dir
        """,
        'downloaded2': {
            'x.css': '.x {width:100px}'
        },
        'sass_dir': {
            'foo.scss': "@import 'SRC/path/to/bar';\n@import 'DL/x';",
            'path/to/_bar.scss': 'a {color: black;}'
        }
    })
    Grab().build()
    assert {
        'foo.css': 'a{color:black}.x{width:100px}\n',
    } == gettree(tmpworkdir.join('built_at/css'))


def test_sass_clever_import_debug(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: built_at
        debug: true
        build:
          sass:
            css: sass_dir
        """,
        'sass_dir': {
            'foo.scss': "@import 'SRC/bar';",
            '_bar.scss': 'a {color: black;}'
        }
    })
    Grab().build()
    tree = gettree(tmpworkdir.join('built_at/css'))
    tree.pop('foo.map')
    assert {
        '.src': {
            'foo.scss': "@import 'SRC/bar';",
            '_bar.scss': 'a {color: black;}'
        },
        'foo.css': 'a {\n  color: black; }\n\n'
                   '/*# sourceMappingURL=foo.map */'
    } == tree
