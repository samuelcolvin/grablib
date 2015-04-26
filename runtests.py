import filecmp
import os
import sys
import unittest
from requests import ConnectionError
import shutil
from grablib.common import GrabLibError

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import mock
except ImportError:
    # python3
    from unittest import mock

from grablib import parse_cmd_arguments, parser


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
        def __init__(self):
            file_name = os.path.basename(url)
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


class CmdTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists('test-download-dir'):
            shutil.rmtree('test-download-dir')

    def tearDown(self):
        # duplicates above so we can switch this one off while we're looking at the files without breaking tests
        if os.path.exists('test-download-dir'):
            shutil.rmtree('test-download-dir')

    def test_simple_wrong_path(self):
        # we always use no-colour to avoid issues with termcolor being clever and not applying colour strings on travis
        ns = parser.parse_args(['test_file', '--no-colour'])
        with GetStd() as get_std:
            r = parse_cmd_arguments(ns)
        self.assertEqual(get_std.stdout, '')
        self.assertEqual(get_std.stderr, '===================\n'
                                         'Error: File not found or not valid JSON: test_file')
        self.assertEqual(r, False)

    def test_simple_wrong_path_no_args(self):
        ns = parser.parse_args(['--no-colour'])
        with GetStd() as get_std:
            r = parse_cmd_arguments(ns)
        self.assertEqual(get_std.stdout, '')
        self.assertEqual(get_std.stderr, 'File: "grablib.json" doesn\'t exist, use "grablib -h" to get help')
        self.assertEqual(r, False)

    def _test_simple_case(self, ns):
        with GetStd() as get_std:
            r = parse_cmd_arguments(ns, from_command_line=False)
        self.assertEqual(get_std.stderr, '', 'STDERR not empty: %s' % get_std.stderr)
        self.assertEqual(get_std.stdout, 'Downloading files to: test-download-dir \n'
                                         '  DOWNLOADING: jquery.min.js \n'
                                         '  DOWNLOADING: bootstrap.min.css \n'
                                         ' Library download finished: 2 files downloaded, 0 existing and ignored')
        self.assertEqual(r, True)
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
        ns = parser.parse_args(['test_files/simple_case.json', '--libs-root', 'test-download-dir', '--no-colour'])
        self._test_simple_case(ns)

    @mock.patch('requests.get')
    def test_simple_python_case(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        ns = parser.parse_args(['test_files/simple_case.py', '--libs-root', 'test-download-dir', '--no-colour'])
        self._test_simple_case(ns)

    @mock.patch('requests.get')
    def test_simple_wrong_path(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        ns = parser.parse_args(['{"http://xyz.com": "x"}', '--libs-root', 'test-download-dir', '--no-colour'])
        with GetStd() as get_std:
            self.assertRaises(GrabLibError, parse_cmd_arguments, ns, from_command_line=False)

    @mock.patch('requests.get')
    def test_simple_wrong_path_command_line(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        ns = parser.parse_args(['{"http://xyz.com": "x"}', '--libs-root', 'test-download-dir', '--no-colour'])
        with GetStd() as get_std:
            r = parse_cmd_arguments(ns)
        self.assertEqual(get_std.stdout, 'Downloading files to: test-download-dir \n  DOWNLOADING: x')
        self.assertEqual(get_std.stderr, '===================\nError: Downloading "http://xyz.com" to "x"\n'
                                         '    URL: http://xyz.com\n'
                                         'Problem occurred during download: '
                                         'ConnectionError(\'file does not exist locally\',)\n*** ABORTING ***')
        self.assertFalse(r)

    @mock.patch('requests.get')
    def test_zip_download(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """
        {
          "https://and-old-url.com/test_dir.zip":
          {
            ".*/(.*wanted.*)": "subdirectory/{{ filename }}"
          }
        }
        """
        ns = parser.parse_args([json, '--libs-root', 'test-download-dir', '--no-colour'])
        with GetStd() as get_std:
            parse_cmd_arguments(ns, from_command_line=False)
        self.assertEqual(get_std.stderr, '')
        self.assertEqual(get_std.stdout, 'Downloading files to: test-download-dir \n'
                                         '  DOWNLOADING ZIP: https://and-old-url.com/test_dir.zip... \n'
                                         '   7 file in zip archive \n'
                                         '   3 files copied from zip archive to libs_root \n'
                                         ' Library download finished: 1 files downloaded, 0 existing and ignored')
        self.assertEqual(os.listdir('test-download-dir'), ['subdirectory'])
        wanted_files = {'a.wanted.css', 'b.wanted.js', 'c.wanted.png'}
        self.assertEqual(set(os.listdir('test-download-dir/subdirectory')), wanted_files)


if __name__ == '__main__':
    unittest.main()
