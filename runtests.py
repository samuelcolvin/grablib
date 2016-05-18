from __future__ import unicode_literals

import logging
import os
import sys
import filecmp
import unittest
import shutil
from tempfile import NamedTemporaryFile

from requests import ConnectionError
from click.testing import CliRunner

import grablib
from grablib.cli import cli
from grablib.common import logger

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import mock
except ImportError:
    # python3
    from unittest import mock


class GetStd(object):
    def __init__(self):
        self._stdout_value = None
        self._stderr_value = None

    def __enter__(self):
        self._stdout_ref = sys.stdout
        self._stdout = StringIO()
        sys.stdout = self._stdout
        self._stderr_ref = sys.stderr
        self._stderr = StringIO()
        sys.stderr = self._stderr
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._stdout_ref
        sys.stderr = self._stderr_ref

    @property
    def stdout(self):
        if self._stdout_value is None:
            self._stdout_value = self._stdout.getvalue().strip()
        return str(self._stdout_value)

    @property
    def stderr(self):
        if self._stderr_value is None:
            self._stderr_value = self._stderr.getvalue().strip()
        return str(self._stderr_value)


def local_requests_get(url, **kwargs):
    """
    overrides requests.get to return a local copy of the file
    :param args:
    :param kwargs:
    :return:
    """
    class MockResponse(object):
        status_code = 200

        def __init__(self):
            file_name = os.path.basename(url)
            if url == 'http://code_404.js':
                # special case to throw 404
                self.status_code = 404
                self.content = self.text = ''
                return
            file_path = os.path.join('test_files/download_file_cache', file_name)
            if not os.path.exists(file_path):
                raise ConnectionError('file does not exist locally')
            with open(file_path, 'rb') as f:
                raw_file = f.read()
            if url.endswith('css'):
                # this is a completely arbitrary variation to text each case
                # TODO we should do something clever here with unicode to force the UnicodeDecodeError
                self.content = self.text = raw_file
                self.headers = {'content-type': 'text'}
            else:
                self.content = raw_file
                self.headers = {'content-type': 'not-text'}
    return MockResponse()


def run_args(*args):
    runner = CliRunner()
    return runner.invoke(cli, args, catch_exceptions=False)


class HouseKeepingMixin(object):
    def _clear_dirs(self):
        for f in ('test-download-dir', 'test-minified-dir'):
            if os.path.exists(f):
                shutil.rmtree(f)

    def setUp(self):
        self._clear_dirs()
        self.tmp_file = NamedTemporaryFile(suffix='.json', mode='w')

    def file_write(self, content):
        self.tmp_file.write(content)
        self.tmp_file.flush()

    def tearDown(self):
        # duplicates above so we can switch this one off while we're looking at the files without breaking tests
        self._clear_dirs()
        self.tmp_file.close()


class CmdTestCase(HouseKeepingMixin, unittest.TestCase):
    maxDiff = None

    def test_simple_wrong_path(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['download', 'test_file'])
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.output, 'Usage: cli [OPTIONS] [download (default) / build] [CONFIG_FILE]\n\n'
                                        'Error: Invalid value for "config-file": Path "test_file" does not exist.\n')

    def test_simple_wrong_path_no_args(self):
        runner = CliRunner()
        result = runner.invoke(cli)
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.output, 'Usage: cli [OPTIONS] [download (default) / build] [CONFIG_FILE]\n\n'
                                        'Error: Invalid value for "config-file": Path "grablib.json" does not exist.\n')

    def _test_simple_case(self, *args):
        result = run_args(*args)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, 'Downloading files to: test-download-dir\n'
                                        'DOWNLOADING: jquery.min.js\n'
                                        'DOWNLOADING: bootstrap.min.css\n'
                                        'Download finished: 2 files downloaded, 0 existing and ignored\n')
        downloaded_files = {'jquery.min.js', 'bootstrap.min.css'}
        self.assertEqual(set(os.listdir('test-download-dir')), downloaded_files)
        for f in downloaded_files:
            downloaded_file = os.path.join('test-download-dir', f)
            original_file = os.path.join('test_files/download_file_cache', f)
            if f == 'jquery.min.js':
                # we have to check file which wasn't downloaded with it's orignal name
                original_file = 'test_files/download_file_cache/jquery-1.11.0.min.js'
            self.assertTrue(filecmp.cmp(downloaded_file, original_file),
                            'downloaded file does not match original: "%s"' % f)

    @mock.patch('requests.get')
    def test_simple_json_case(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self._test_simple_case('--download-root', 'test-download-dir', 'download', 'test_files/simple_case.json')

    @mock.patch('requests.get')
    def test_simple_json_case_download_root(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self.file_write("""\
        {
          "download_root": "test-download-dir",
          "libs": {"https://whatever/bootstrap.min.css": "{{ filename }}"}
        }
        """)
        result = run_args('download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(os.listdir('test-download-dir'), ['bootstrap.min.css'])

    @mock.patch('requests.get')
    def test_simple_yaml_case(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self._test_simple_case('--download-root', 'test-download-dir', 'download', 'test_files/simple_case.yml')

    def test_wrong_format(self):
        self.tmp_file = NamedTemporaryFile(suffix='.py', mode='w')
        self.tmp_file.write('anything = 1')
        self.tmp_file.flush()

        result = run_args('download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('should be json or yml/yaml', result.output)

        self.tmp_file.close()

    @mock.patch('requests.get')
    def test_download_response_404(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get

        self.file_write('{"http://code_404.js": "x"}')
        result = run_args('--download-root', 'test-download-dir', 'download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.output, 'Downloading files to: test-download-dir\n'
                                        'DOWNLOADING: x\n'
                                        'use "--verbosity high" for more details\n'
                                        'Error: \n'
                                        'Downloading "http://code_404.js" to "x"\n'
                                        '    URL: http://code_404.js\n'
                                        'Problem occurred during download, wrong status code: 404\n'
                                        '*** ABORTING ***\n')

    @mock.patch('requests.get')
    def test_simple_wrong_path_command_line(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self.file_write('{"http://xyz.com": "x"}')
        result = run_args('--download-root', 'test-download-dir', 'download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.output, 'Downloading files to: test-download-dir\n'
                                        'DOWNLOADING: x\n'
                                        'use "--verbosity high" for more details\n'
                                        'Error: \n'
                                        'Downloading "http://xyz.com" to "x"\n'
                                        '    URL: http://xyz.com\n'
                                        'Problem occurred during download: '
                                        'ConnectionError: file does not exist locally\n'
                                        '*** ABORTING ***\n')

    @mock.patch('requests.get')
    def test_invalid_json(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self.file_write('{"http://xyz.com": "x",}')
        result = run_args('--download-root', 'test-download-dir', 'download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 1)
        # output is different for different version of python
        self.assertIn('line 1 column 24 (char 23', result.output)

    @mock.patch('requests.get')
    def test_json_download_sites(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self.file_write("""\
        {
          "download_root": "test-download-dir",
          "sites":
          {
            "github": "https://raw.githubusercontent.com"
          },
          "libs": {
            "{{ github }}/twbs/bootstrap/v3.3.5/dist/css/bootstrap.min.css": "{{ filename }}"
          }
        }
        """)
        result = run_args('--download-root', 'test-download-dir', 'download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, 'Downloading files to: test-download-dir\n'
                                        'DOWNLOADING: bootstrap.min.css\n'
                                        'Download finished: 1 files downloaded, 0 existing and ignored\n')
        self.assertEqual(os.listdir('test-download-dir'), ['bootstrap.min.css'])

    @mock.patch('requests.get')
    def test_json_download_overwrite(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        os.mkdir('test-download-dir')
        with open('test-download-dir/jquery.js', 'w') as f:
            f.write('testing')
        self.file_write("""\
        {
          "download_root": "test-download-dir",
          "libs": {
            "http://code.jquery.com/jquery-1.11.0.js": "jquery.js"
          }
        }
        """)
        result = run_args('--overwrite', 'download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(os.listdir('test-download-dir'), ['jquery.js'])
        with open('test-download-dir/jquery.js') as f:
            self.assertEqual(f.read(), "/* jQuery JavaScript Library */\n$ = 'jQuery';\n")

    @mock.patch('requests.get')
    def test_json_download_dont_overwrite(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        os.mkdir('test-download-dir')
        with open('test-download-dir/jquery.js', 'w') as f:
            f.write('testing')
        self.file_write("""\
        {
          "download_root": "test-download-dir",
          "libs": {
            "http://code.jquery.com/jquery-1.11.0.js": "jquery.js"
          }
        }
        """)
        result = run_args('download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(os.listdir('test-download-dir'), ['jquery.js'])
        with open('test-download-dir/jquery.js') as f:
            self.assertEqual(f.read(), 'testing')

    @mock.patch('requests.get')
    def test_zip_download(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self.file_write("""\
        {
          "https://and-old-url.com/test_dir.zip":
          {
            ".*/(.*wanted.*)": "subdirectory/{{ filename }}"
          }
        }
        """)
        result = run_args('--download-root', 'test-download-dir',
                          '--verbosity', 'high', 'download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, (
            'Processing %s as a json file\n'
            'Downloading files to: test-download-dir\n'
            'DOWNLOADING ZIP: https://and-old-url.com/test_dir.zip...\n'
            '7 file in zip archive\n'
            '  searching for target for test_dir/c.wanted.png...\n'
            '    test_dir/c.wanted.png > subdirectory/c.wanted.png based on regex .*/(.*wanted.*)\n'
            '  searching for target for test_dir/b.wanted.js...\n'
            '    test_dir/b.wanted.js > subdirectory/b.wanted.js based on regex .*/(.*wanted.*)\n'
            '  searching for target for test_dir/a.js...\n'
            '    no target found\n'
            '  searching for target for test_dir/b.css...\n'
            '    no target found\n'
            '  searching for target for test_dir/d.png...\n'
            '    no target found\n'
            '  searching for target for test_dir/a.wanted.css...\n'
            '    test_dir/a.wanted.css > subdirectory/a.wanted.css based on regex .*/(.*wanted.*)\n'
            '3 files copied from zip archive, 0 ignored as already exist\n'
            'Download finished: 1 files downloaded, 0 existing and ignored\n') % self.tmp_file.name)
        self.assertEqual(os.listdir('test-download-dir'), ['subdirectory'])
        wanted_files = {'a.wanted.css', 'b.wanted.js', 'c.wanted.png'}
        self.assertEqual(set(os.listdir('test-download-dir/subdirectory')), wanted_files)

    @mock.patch('requests.get')
    def test_zip_download_exists(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self.file_write("""\
        {
          "download_root": "test-download-dir",
          "libs": {
            "https://and-old-url.com/test_dir.zip":
            {
              ".*/(.*wanted.*)": "subdirectory/{{ filename }}"
            }
          }
        }
        """)
        result = run_args('download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 0)
        result = run_args('download', '--verbosity', 'high', self.tmp_file.name)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('subdirectory/b.wanted.js" IGNORING', result.output)
        self.assertEqual(os.listdir('test-download-dir'), ['subdirectory'])
        wanted_files = {'a.wanted.css', 'b.wanted.js', 'c.wanted.png'}
        self.assertEqual(set(os.listdir('test-download-dir/subdirectory')), wanted_files)

    @mock.patch('requests.get')
    def test_simple_minify(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self.file_write("""\
        {
          "download_root": "test-download-dir",
          "minified_root": "test-minified-dir",
          "libs": {
            "http://code.jquery.com/jquery-1.11.0.js": "jquery.js",
            "http://getbs.com/bootstrap.css": "{{ filename }}"
          },
          "minify": {
            "jquery.min.js": ["jquery.js"],
            "bootstrap.min.css": ["bootstrap.css"]
          }
        }
        """)
        result = run_args('download', self.tmp_file.name)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, 'Downloading files to: test-download-dir\n'
                                        'DOWNLOADING: jquery.js\n'
                                        'DOWNLOADING: bootstrap.css\n'
                                        'Download finished: 2 files downloaded, 0 existing and ignored\n'
                                        '1 files combined to form "test-minified-dir/jquery.min.js"\n'
                                        '1 files combined to form "test-minified-dir/bootstrap.min.css"\n')
        self.assertEqual(set(os.listdir('test-download-dir')), {'jquery.js', 'bootstrap.css'})
        with open('test-download-dir/jquery.js') as f:
            self.assertEqual(f.read(), "/* jQuery JavaScript Library */\n$ = 'jQuery';\n")
        self.assertEqual(set(os.listdir('test-minified-dir')), {'jquery.min.js', 'bootstrap.min.css'})
        with open('test-minified-dir/jquery.min.js') as f:
            self.assertEqual(f.read(), "$='jQuery';")
        with open('test-minified-dir/bootstrap.min.css') as f:
            self.assertEqual(f.read(), "bootstrap{content:'this is boostrap'}")


class TestingLogHandler(logging.Handler):
    def __init__(self, **kwargs):
        super(TestingLogHandler, self).__init__(**kwargs)
        self.log = []

    def emit(self, record):
        self.log.append(self.format(record))


class LibraryTestCase(HouseKeepingMixin, unittest.TestCase):
    def setUp(self):
        super(LibraryTestCase, self).setUp()
        for h in logger.handlers:
            logger.removeHandler(h)
        self.hdl = TestingLogHandler()
        logger.addHandler(self.hdl)
        logger.setLevel(logging.DEBUG)

    @mock.patch('requests.get')
    def test_simple_good_case(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self.file_write('{"http://wherever.com/moment.js": "x"}')
        grablib.grab(self.tmp_file.name, download_root='test-download-dir')
        self.assertEqual(self.hdl.log, ['Processing %s as a json file' % self.tmp_file.name,
                                        'Downloading files to: test-download-dir',
                                        'DOWNLOADING: x',
                                        'Successfully downloaded x\n',
                                        'Download finished: 1 files downloaded, 0 existing and ignored'])

    @mock.patch('requests.get')
    def test_different_filenames(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
        {
          "http://wherever.com/moment.js": "x",
          "http://wherever.com/bootstrap.css": "{ filename}",
          "http://wherever.com/bootstrap.min.css": "whatever_{{filename }}",
          "http://wherever.com/unicode.js": "/"
        }
        """
        grablib.grab(json, download_root='test-download-dir')
        wanted_files = {'x', 'bootstrap.css', 'whatever_bootstrap.min.css', 'unicode.js'}
        self.assertEqual(set(os.listdir('test-download-dir')), wanted_files)

    @mock.patch('requests.get')
    def test_minify_2_files(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        self.file_write("""\
        {
          "download_root": "test-download-dir",
          "libs": {
            "http://code.jquery.com/jquery-1.11.0.js": "weird/place/jquery.js",
            "http://wherever.com/moment.js": "somewhere/very/deep/{{ filename }}"
          },
          "minified_root": "test-minified-dir",
          "minify": {
            "outputfile.min.js": [
              ".*jquery.js",
              ["somewhere/very/deep/moment.js", {"m.*?ent": "minute"}]
            ]
          }
        }
        """)
        grablib.grab(self.tmp_file.name)
        self.assertIn('2 files combined to form "test-minified-dir/outputfile.min.js"', self.hdl.log)
        self.assertEqual(os.listdir('test-minified-dir'), ['outputfile.min.js'])
        with open('test-minified-dir/outputfile.min.js') as f:
            self.assertEqual(f.read(), "$='jQuery';\nminute='minute js';")

    @mock.patch('requests.get')
    def test_minify_already_minified(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
        {
          "libs": {"http://code.jquery.com/jquery-1.11.0.min.js": "jquery.min.js"},
          "minify": {"outputfile.min.js": [".*jquery.*"]}
        }
        """
        grablib.grab(json, download_root='test-download-dir', minified_root='test-minified-dir')
        self.assertEqual(os.listdir('test-minified-dir'), ['outputfile.min.js'])
        with open('test-minified-dir/outputfile.min.js') as f:
            self.assertEqual(f.read(), "$ = 'jQuery';")

    @mock.patch('requests.get')
    def test_minify_unicode(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
        {
          "libs": {"http://unicode.js": "unicode.js"},
          "minify": {"unicode.min.js": ["unicode.js"]}
        }
        """
        grablib.grab(json, download_root='test-download-dir', minified_root='test-minified-dir')
        self.assertEqual(os.listdir('test-minified-dir'), ['unicode.min.js'])
        with open('test-minified-dir/unicode.min.js') as f:
            fstr = f.read()
            if hasattr(fstr, 'decode'):
                # PY2
                fstr = fstr.decode('utf8')
            self.assertEqual(fstr, u'months="\u4e00\u6708";')

    @mock.patch('requests.get')
    def test_minify_existing(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        os.mkdir('test-minified-dir')
        with open('test-minified-dir/whatever.txt', 'w') as f:
            f.write('hello')
        json = """\
        {
          "download_root": "test-download-dir",
          "libs": {
            "http://code.jquery.com/jquery-1.11.0.js": "weird/place/jquery.js"
          },
          "minified_root": "test-minified-dir",
          "minify": {"jquery.min.js": [".*jquery.js"]}
        }
        """
        grablib.grab(json)
        self.assertEqual(self.hdl.log, ['Downloading files to: test-download-dir',
                                        'DOWNLOADING: weird/place/jquery.js',
                                        'Successfully downloaded jquery.js\n',
                                        'Download finished: 1 files downloaded, 0 existing and ignored',
                                        'minified root directory "test-minified-dir" already existing, deleting',
                                        '1 files combined to form "test-minified-dir/jquery.min.js"'])
        self.assertEqual(os.listdir('test-minified-dir'), ['jquery.min.js'])

    @mock.patch('requests.get')
    def test_minify_local(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
        {
          "download_root": "test-download-dir",
          "minified_root": "test-minified-dir",
          "minify": {
            "jquery.min.js": [
              "./test_files/download_file_cache/jquery-1.11.0.min.js"
            ]
          }
        }
        """
        grablib.grab(json)
        self.assertEqual(self.hdl.log, ['1 files combined to form "test-minified-dir/jquery.min.js"'])
        self.assertEqual(os.listdir('test-minified-dir'), ['jquery.min.js'])

    @mock.patch('requests.get')
    def test_zip_download(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """
        {
          "https://and-old-url.com/test_assets.zip":
          {
            "test_assets/assets/(.+)": "subdirectory/{{ filename }}"
          }
        }
        """
        grablib.grab(json, download_root='test-download-dir')
        self.assertEqual(self.hdl.log, [
            'Downloading files to: test-download-dir',
            'DOWNLOADING ZIP: https://and-old-url.com/test_assets.zip...',
            '5 file in zip archive',
            '  searching for target for test_assets/not_in_assets.txt...',
            '    no target found',
            '  searching for target for test_assets/assets/b.txt...',
            '    test_assets/assets/b.txt > subdirectory/b.txt based on regex test_assets/assets/(.+)',
            '  searching for target for test_assets/assets/a.txt...',
            '    test_assets/assets/a.txt > subdirectory/a.txt based on regex test_assets/assets/(.+)',
            '2 files copied from zip archive, 0 ignored as already exist',
            'Download finished: 1 files downloaded, 0 existing and ignored'
        ])

        self.assertEqual(os.listdir('test-download-dir'), ['subdirectory'])
        wanted_files = {'a.txt', 'b.txt'}
        self.assertEqual(set(os.listdir('test-download-dir/subdirectory')), wanted_files)


if __name__ == '__main__':
    unittest.main()
