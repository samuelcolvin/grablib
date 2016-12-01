import pytest

from grablib import Grab
from grablib.common import GrablibError

from .conftest import gettree, mktree


def test_cat(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
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
          debug: true
          cat:
            "libraries.js":
              - "./foo.js"
              - "./bar.js"
        """,
        'foo.js': 'var v = "foo js";\n    vindent = true;',
        'bar.js': 'var v = "bar js";',
    })
    Grab().build()
    assert {
        'libraries.js':
            '/* === foo.js === */\n'
            'var v = "foo js";\n'
            '    vindent = true;\n'
            '/* === bar.js === */\n'
            'var v = "bar js";\n'
    } == gettree(tmpworkdir.join('built_at'))


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


def test_sass_debug(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          debug: true
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
