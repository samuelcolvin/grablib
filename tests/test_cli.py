from click.testing import CliRunner

from grablib.cli import cli

from .conftest import mktree


def test_simple_wrong_path():
    runner = CliRunner()
    result = runner.invoke(cli, ['download', '-f', 'test_file'])
    assert result.exit_code == 2
    assert result.output == ('Usage: cli [OPTIONS] [download (default) / build]\n\n'
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
