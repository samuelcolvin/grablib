import pytest

from grablib import Grab
from grablib.common import GrablibError, setup_logging

from .conftest import gettree, mktree


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
    assert {
        'foo.css': '.foo .bar {\n  color: black; }\n\n/*# sourceMappingURL=foo.map */',
        '.src': {
            'foo.scss': '.foo { .bar {color: black;}}'
        },
        'foo.map': '{\n\t"version": 3,\n\t"file": ".src/foo.css",\n\t'
                   '"sources": [\n\t\t".src/foo.scss"\n\t],\n\t"mappings": "AAAA,AAAO,IAAH,CAAG,IAAI,...'
    } == gettree(tmpworkdir.join('built_at/css'))


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
