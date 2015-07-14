import filecmp
import os
import sys
import unittest
from requests import ConnectionError
import shutil
import grablib
from grablib.common import GrablibError

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import mock
except ImportError:
    # python3
    from unittest import mock

from grablib import run_cmd_arguments, parser


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


class HouseKeepingMixin(object):
    def _clear_dirs(self):
        for f in ('test-download-dir', 'test-minified-dir'):
            if os.path.exists(f):
                shutil.rmtree(f)

    def setUp(self):
        self._clear_dirs()

    def tearDown(self):
        # duplicates above so we can switch this one off while we're looking at the files without breaking tests
        self._clear_dirs()


class CmdTestCase(HouseKeepingMixin, unittest.TestCase):
    def test_simple_wrong_path(self):
        # we always use no-colour to avoid issues with termcolor being clever and not applying colour strings on travis
        ns = parser.parse_args(['test_file', '--no-colour'])
        with GetStd() as get_std:
            r = run_cmd_arguments(ns)
        self.assertEqual(get_std.stdout, '')
        self.assertEqual(get_std.stderr, '===================\n'
                                         'Error: File not found or not valid JSON: test_file')
        self.assertEqual(r, False)

    def test_simple_wrong_path_no_args(self):
        ns = parser.parse_args(['--no-colour'])
        with GetStd() as get_std:
            r = run_cmd_arguments(ns)
        self.assertEqual(get_std.stdout, '')
        self.assertEqual(get_std.stderr, 'File: "grablib.json" doesn\'t exist, use "grablib -h" to get help')
        self.assertEqual(r, False)

    def _test_simple_case(self, ns):
        with GetStd() as get_std:
            r = run_cmd_arguments(ns, from_command_line=False)
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
        ns = parser.parse_args(['test_files/simple_case.json', '--download-root', 'test-download-dir', '--no-colour'])
        self._test_simple_case(ns)

    @mock.patch('requests.get')
    def test_simple_json_case_download_root(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
        {
          "download_root": "test-download-dir",
          "libs": {"https://whatever/bootstrap.min.css": "{{ filename }}"}
        }
        """
        ns = parser.parse_args([json, '--no-colour'])
        with GetStd():
            r = run_cmd_arguments(ns)
        self.assertEqual(r, True)
        self.assertEqual(os.listdir('test-download-dir'), ['bootstrap.min.css'])

    @mock.patch('requests.get')
    def test_simple_json_case_old_name(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
        {
          "libs_root": "test-download-dir",
          "libs": {"https://whatever/bootstrap.min.css": "{{ filename }}"}
        }
        """
        ns = parser.parse_args([json, '--no-colour'])
        with GetStd():
            r = run_cmd_arguments(ns)
        self.assertEqual(r, True)
        self.assertEqual(os.listdir('test-download-dir'), ['bootstrap.min.css'])

    @mock.patch('requests.get')
    def test_simple_python_case(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        ns = parser.parse_args(['test_files/simple_case.py', '--download-root', 'test-download-dir', '--no-colour'])
        self._test_simple_case(ns)

    @mock.patch('requests.get')
    def test_simple_wrong_path(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        ns = parser.parse_args(['{"http://xyz.com": "x"}', '--download-root', 'test-download-dir', '--no-colour'])
        with GetStd():
            self.assertRaises(GrablibError, run_cmd_arguments, ns, from_command_line=False)

    @mock.patch('requests.get')
    def test_download_response_404(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        ns = parser.parse_args(['{"http://code_404.js": "x"}', '--download-root', 'test-download-dir', '--no-colour'])
        with GetStd() as get_std:
            r = run_cmd_arguments(ns)
        self.assertFalse(r)
        self.assertEqual(get_std.stdout, 'Downloading files to: test-download-dir \n  DOWNLOADING: x')
        self.assertEqual(get_std.stderr, '===================\nError: Downloading "http://code_404.js" to "x"\n'
                                         '    URL: http://code_404.js\nProblem occurred during download, '
                                         'wrong status code: 404\n*** ABORTING ***')

    @mock.patch('requests.get')
    def test_simple_wrong_path_command_line(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        ns = parser.parse_args(['{"http://xyz.com": "x"}', '--download-root', 'test-download-dir', '--no-colour'])
        with GetStd() as get_std:
            r = run_cmd_arguments(ns)
        self.assertEqual(get_std.stdout, 'Downloading files to: test-download-dir \n  DOWNLOADING: x')
        self.assertEqual(get_std.stderr, '===================\nError: Downloading "http://xyz.com" to "x"\n'
                                         '    URL: http://xyz.com\n'
                                         'Problem occurred during download: '
                                         'ConnectionError(\'file does not exist locally\',)\n*** ABORTING ***')
        self.assertFalse(r)

    @mock.patch('requests.get')
    def test_invalid_json(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        ns = parser.parse_args(['{"http://xyz.com": "x"}', '--download-root', 'test-download-dir', '--no-colour'])
        self.assertRaises(GrablibError, run_cmd_arguments, ns, from_command_line=False)

    @mock.patch('requests.get')
    def test_invalid_json(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        ns = parser.parse_args(['{"http://xyz.com": "x",}', '--download-root', 'test-download-dir', '--no-colour'])
        self.assertRaises(GrablibError, run_cmd_arguments, ns, from_command_line=False)

    @mock.patch('requests.get')
    def test_json_download_sites(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
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
        """
        ns = parser.parse_args([json, '--no-colour'])
        with GetStd() as get_std:
            run_cmd_arguments(ns, from_command_line=False)
        self.assertEqual(get_std.stderr, '')
        self.assertEqual(get_std.stdout, 'Downloading files to: test-download-dir \n'
                                         '  DOWNLOADING: bootstrap.min.css \n'
                                         ' Library download finished: 1 files downloaded, 0 existing and ignored')
        self.assertEqual(os.listdir('test-download-dir'), ['bootstrap.min.css'])

    @mock.patch('requests.get')
    def test_json_download_overwrite(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        os.mkdir('test-download-dir')
        with open('test-download-dir/jquery.js', 'w') as f:
            f.write('testing')
        json = """\
        {
          "download_root": "test-download-dir",
          "libs": {
            "http://code.jquery.com/jquery-1.11.0.js": "jquery.js"
          }
        }
        """
        ns = parser.parse_args([json, '-w'])
        with GetStd() as get_std:
            run_cmd_arguments(ns, from_command_line=False)
        self.assertEqual(get_std.stderr, '')
        self.assertEqual(os.listdir('test-download-dir'), ['jquery.js'])
        with open('test-download-dir/jquery.js') as f:
            self.assertEqual(f.read(), "/*! jQuery JavaScript Library */\n$ = 'jQuery';\n")

    @mock.patch('requests.get')
    def test_json_download_dont_overwrite(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        os.mkdir('test-download-dir')
        with open('test-download-dir/jquery.js', 'w') as f:
            f.write('testing')
        json = """\
        {
          "download_root": "test-download-dir",
          "libs": {
            "http://code.jquery.com/jquery-1.11.0.js": "jquery.js"
          }
        }
        """
        ns = parser.parse_args([json])
        with GetStd() as get_std:
            run_cmd_arguments(ns, from_command_line=False)
        self.assertEqual(get_std.stderr, '')
        self.assertEqual(os.listdir('test-download-dir'), ['jquery.js'])
        with open('test-download-dir/jquery.js') as f:
            self.assertEqual(f.read(), 'testing')

    @mock.patch('requests.get')
    def test_zip_download(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
        {
          "https://and-old-url.com/test_dir.zip":
          {
            ".*/(.*wanted.*)": "subdirectory/{{ filename }}"
          }
        }
        """
        ns = parser.parse_args([json, '--download-root', 'test-download-dir', '--no-colour'])
        with GetStd() as get_std:
            run_cmd_arguments(ns, from_command_line=False)
        self.assertEqual(get_std.stderr, '')
        self.assertEqual(get_std.stdout, 'Downloading files to: test-download-dir \n'
                                         '  DOWNLOADING ZIP: https://and-old-url.com/test_dir.zip... \n'
                                         '   7 file in zip archive \n'
                                         '   3 files copied from zip archive to download_root \n'
                                         ' Library download finished: 1 files downloaded, 0 existing and ignored')
        self.assertEqual(os.listdir('test-download-dir'), ['subdirectory'])
        wanted_files = {'a.wanted.css', 'b.wanted.js', 'c.wanted.png'}
        self.assertEqual(set(os.listdir('test-download-dir/subdirectory')), wanted_files)

    @mock.patch('requests.get')
    def test_simple_minify(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
        {
          "libs": {
            "http://code.jquery.com/jquery-1.11.0.js": "jquery.js",
            "http://getbs.com/bootstrap.css": "{{ filename }}"
          },
          "minify": {
            "jquery.min.js": ["jquery.js"],
            "bootstrap.min.css": ["bootstrap.css"]
          }
        }
        """
        ns = parser.parse_args([json, '-d', 'test-download-dir', '-m', 'test-minified-dir', '--no-colour'])
        with GetStd() as get_std:
            run_cmd_arguments(ns, from_command_line=False)
        self.assertEqual(get_std.stderr, '')
        self.assertEqual(get_std.stdout, 'Downloading files to: test-download-dir \n'
                                         '  DOWNLOADING: jquery.js \n'
                                         '  DOWNLOADING: bootstrap.css \n'
                                         ' Library download finished: 2 files downloaded, 0 existing and ignored \n'
                                         '  1 files combined to form "test-minified-dir/jquery.min.js" \n'
                                         '  1 files combined to form "test-minified-dir/bootstrap.min.css"')
        self.assertEqual(set(os.listdir('test-download-dir')), {'jquery.js', 'bootstrap.css'})
        with open('test-download-dir/jquery.js') as f:
            self.assertEqual(f.read(), "/*! jQuery JavaScript Library */\n$ = 'jQuery';\n")
        self.assertEqual(set(os.listdir('test-minified-dir')), {'jquery.min.js', 'bootstrap.min.css'})
        with open('test-minified-dir/jquery.min.js') as f:
            self.assertEqual(f.read(), "$='jQuery';")
        with open('test-minified-dir/bootstrap.min.css') as f:
            self.assertEqual(f.read(), "bootstrap{content:'this is boostrap'}")


class LibraryTestCase(HouseKeepingMixin, unittest.TestCase):
    def setUp(self):
        super(LibraryTestCase, self).setUp()
        self.lines = []

    def _take_output(self, line, verbosity=None, colourv=None):
        self.lines.append((line, verbosity))

    def test_simple_good_case(self):
        r = grablib.grab('{"http://xyz.com": "x"}', download_root='test-download-dir', output=self._take_output)
        self.assertTrue(r)
        self.assertEqual(self.lines, [('', 3), ('Downloading files to: test-download-dir', 1),
                                      ('DOWNLOADING: x', None),
                                      ('Successfully downloaded x\n', 3),
                                      ('Library download finished: 1 files downloaded, 0 existing and ignored', 1)])

    def test_bad_verbosity(self):
        self.assertRaises(GrablibError, grablib.grab, '{"http://xyz.com": "x"}', verbosity='foo', output='silent')

    @mock.patch('requests.get')
    def test_minify_2_files(self, mock_requests_get):
        mock_requests_get.side_effect = local_requests_get
        json = """\
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
        """
        r = grablib.grab(json, output=self._take_output)
        self.assertTrue(r)
        self.assertEqual(self.lines, [('', 3),
                                      ('Downloading files to: test-download-dir', 1),
                                      ('DOWNLOADING: weird/place/jquery.js', None),
                                      ('Successfully downloaded jquery.js\n', 3),
                                      ('DOWNLOADING: somewhere/very/deep/moment.js', None),
                                      ('Successfully downloaded moment.js\n', 3),
                                      ('Library download finished: 2 files downloaded, 0 existing and ignored', 1),
                                      ('2 files combined to form "test-minified-dir/outputfile.min.js"', 2)])
        self.assertEqual(os.listdir('test-minified-dir'), ['outputfile.min.js'])
        with open('test-minified-dir/outputfile.min.js') as f:
            self.assertEqual(f.read(), "$='jQuery';minute='minute js';")

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
        r = grablib.grab(json, output=self._take_output)
        self.assertTrue(r)
        self.assertEqual(self.lines, [('1 files combined to form "test-minified-dir/jquery.min.js"', 2)])
        self.assertEqual(os.listdir('test-minified-dir'), ['jquery.min.js'])


if __name__ == '__main__':
    unittest.main()
