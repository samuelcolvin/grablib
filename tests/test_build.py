import pytest

from grablib import Grab
from grablib.common import GrablibError

from .conftest import gettree, mktree


def test_simple(tmpworkdir):
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
    Grab().build()
    assert gettree(tmpworkdir.join('built_at')) == {
        'libraries.js':
            '/* === foo.js === */\n'
            'var v = "foo js";\n'
            '    vindent = true;\n'
            '/* === bar.js === */\n'
            'var v = "bar js";\n'
    }


def test_minify(tmpworkdir):
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


def test_src_wrong(tmpworkdir):
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


def test_download_root(tmpworkdir):
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


def test_regex(tmpworkdir):
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
