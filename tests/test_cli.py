from click.testing import CliRunner

from grablib.cli import cli

from .conftest import gettree, mktree


def test_simple_wrong_path():
    runner = CliRunner()
    result = runner.invoke(cli, ['download', '-f', 'test_file'])
    assert result.exit_code == 2
    assert result.output == ('Usage: cli [OPTIONS] [download / build]\n\n'
                             'Error: Invalid value for "-f" / "--config-file": Path "test_file" does not exist.\n')


def test_invalid_json(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.json': 'WRONG'
    })
    result = CliRunner().invoke(cli, ['download', '-f', 'grablib.json'])
    assert result.exit_code == 2
    assert result.output == ('JSONDecodeError: Expecting value: line 1 column 1 (char 0)\n'
                             'use "--verbosity high" for more details\n'
                             'Error: error loading "grablib.json"\n')


def test_just_build(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """
        build_root: "built_at"
        build:
          cat:
            "libraries.js":
              - "./foo.js"
        """,
        'foo.js': 'var v = "foo js";',
    })
    result = CliRunner().invoke(cli, ['download'])
    assert result.exit_code == 0
    assert tmpworkdir.join('built_at').check() is False
    result = CliRunner().invoke(cli, ['build'])
    assert result.exit_code == 0
    assert gettree(tmpworkdir.join('built_at')) == {'libraries.js': '/* === foo.js === */\nvar v = "foo js";\n'}
