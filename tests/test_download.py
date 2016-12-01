from pathlib import Path

import pytest
from requests import HTTPError

from grablib import Grab
from grablib.common import GrablibError

from .conftest import gettree, mktree

FIXTURES = Path(__file__).resolve().parent / Path('fixtures')


class MockResponse:
    def __init__(self, *, status_code=200, content=b'response text', headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {
            'content-type': 'application/json',
            'server': 'Mock'
        }


def request_fixture(url, **kwargs):
    filename = url.split('/')[-1]
    p = FIXTURES.joinpath(filename)
    return MockResponse(content=p.read_bytes(), headers={'content-type': 'application/zip'})


def test_simple(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.json': '{"download": {"http://wherever.com/moment.js": "x"}}'
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='test-download-dir')
    grab.download()
    grab.build()
    assert gettree(tmpworkdir) == {
        'grablib.json': '{"download": {"http://wherever.com/moment.js": "x"}}',
        'test-download-dir': {'x': 'response text'},
    }


def test_zip(mocker, tmpworkdir):
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.side_effect = request_fixture
    mktree(tmpworkdir, {
        'grablib.json': """
    {
      "download": {
        "https://any-old-url.com/test_assets.zip":
        {
          "test_assets/assets/(.+)": "subdirectory/{filename}"
        }
      }
    }
    """})
    Grab('grablib.json', download_root='test-download-dir').download()
    assert gettree(tmpworkdir.join('test-download-dir')) == {'subdirectory': {'b.txt': 'b\n', 'a.txt': 'a\n'}}


def test_zip_null(mocker, tmpworkdir):
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.side_effect = request_fixture
    mktree(tmpworkdir, {
        'grablib.yaml': """
      "download":
        "https://any-old-url.com/test_assets.zip":
           "test_assets/assets/a.txt": null
           "test_assets/assets/(.+)": "subdirectory/{filename}"
    """})
    Grab(download_root='test-download-dir').download()
    assert gettree(tmpworkdir.join('test-download-dir')) == {'subdirectory': {'b.txt': 'b\n'}}


def test_zip_double(mocker, tmpworkdir):
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.side_effect = request_fixture
    mktree(tmpworkdir, {
        'grablib.yaml': """
      'download':
        'https://any-old-url.com/test_assets.zip':
           'test_assets/assets/a.txt':
             - a.txt
             - a_again.txt
           'test_assets/assets/(.+)': '{filename}'
    """})
    Grab(download_root='test-download-dir').download()
    assert gettree(tmpworkdir.join('test-download-dir')) == {'b.txt': 'b\n', 'a.txt': 'a\n', 'a_again.txt': 'a\n'}


def test_zip_error(mocker, tmpworkdir):
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.side_effect = request_fixture
    mktree(tmpworkdir, {
        'grablib.json': """
    {
      "download_root": "test-download-dir",
      "download": {
        "https://any-old-url.com/test_assets.zip":
        {
          "test_assets/assets/(.+)": "   "
        }
      }
    }
    """})
    with pytest.raises(GrablibError) as excinfo:
        Grab().download()
    assert excinfo.value.args == ('Error downloading "https://any-old-url.com/test_assets.zip" '
                                  'to "{\'test_assets/assets/(.+)\': \'   \'}"',)


def test_with_aliases(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """\
        download_root: download_to
        aliases:
          WHATEVER: https://www.whatever.com
        download:
          "WHATEVER/foo.js": "js/"
        """
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    Grab().download()
    mock_requests_get.assert_called_with('https://www.whatever.com/foo.js')
    assert gettree(tmpworkdir.join('download_to')) == {
        'js': {
            'foo.js': 'response text'
        }
    }


def test_download_403(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """\
        download_root: download_to
        download:
          "https://www.whatever.com/foo.js": "js/"
        """
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse(status_code=403)
    with pytest.raises(GrablibError) as excinfo:
        Grab().download()
    assert excinfo.value.args == ('Error downloading "https://www.whatever.com/foo.js" to "js/"',)


def test_download_error(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': """\
        download_root: download_to
        download:
          "https://www.whatever.com/foo.js": "js/"
        """
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.side_effect = HTTPError('boom')
    with pytest.raises(GrablibError) as excinfo:
        Grab().download()
    assert excinfo.value.args == ('Error downloading "https://www.whatever.com/foo.js" to "js/"',)


def test_no_standard_file():
    with pytest.raises(GrablibError) as excinfo:
        Grab(download_root='test-download-dir')
    assert excinfo.value.args[0].startswith('Unable to find config file with standard name "grablib.yml" or')


def test_wrong_extension(tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.notjson': '{"download": {"http://wherever.com/moment.js": "x"}}'
    })
    with pytest.raises(GrablibError) as excinfo:
        Grab('grablib.notjson', download_root='test-download-dir')
    assert excinfo.value.args[0] == 'Unexpected extension for "grablib.notjson", should be json or yml/yaml'
