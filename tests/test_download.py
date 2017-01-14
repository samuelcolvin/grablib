from pathlib import Path

import pytest
from pytest_toolbox import gettree, mktree
from requests import HTTPError

from grablib import Grab
from grablib.common import GrablibError

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
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x"
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='test-download-dir')
    grab.download()
    grab.build()
    assert gettree(tmpworkdir) == {
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x",
        'test-download-dir': {'x': 'response text'},
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js x\n'
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
        'grablib.notjson': '{"download": {"http://wherever.com/file.js": "x"}}'
    })
    with pytest.raises(GrablibError) as excinfo:
        Grab('grablib.notjson', download_root='test-download-dir')
    assert excinfo.value.args[0] == 'Unexpected extension for "grablib.notjson", should be json or yml/yaml'


def test_no_lock(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': "lock: null\ndownload:\n  'http://wherever.com/file.js': x"
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='s')
    grab.download()
    assert gettree(tmpworkdir) == {
        'grablib.yml': "lock: null\ndownload:\n  'http://wherever.com/file.js': x",
        's': {'x': 'response text'},
    }


def test_simple_lock(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': "lock: the.lock\ndownload:\n  'http://wherever.com/file.js': x"
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    Grab(download_root='static').download()
    assert mock_requests_get.call_count == 1
    assert gettree(tmpworkdir) == {
        'grablib.yml': "lock: the.lock\ndownload:\n  'http://wherever.com/file.js': x",
        'static': {'x': 'response text'},
        'the.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js x\n'
    }
    Grab(download_root='static').download()
    assert mock_requests_get.call_count == 1


def test_lock_one_change(mocker, tmpworkdir):
    yml = """\
    download_root: droot
    download:
      'http://wherever.com/file.js': file.js
      'http://wherever.com/file2.js': file2.js"""
    mktree(tmpworkdir, {'grablib.yml': yml})
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    Grab().download()
    assert mock_requests_get.call_count == 2
    assert gettree(tmpworkdir, max_len=None) == {
        'grablib.yml': yml,
        'droot': {'file.js': 'response text', 'file2.js': 'response text'},
        '.grablib.lock': """\
b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js file.js
b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file2.js file2.js\n"""
    }
    tmpworkdir.join('droot/file.js').remove()
    print('##################')
    Grab().download()
    assert mock_requests_get.call_count == 3
    assert gettree(tmpworkdir, max_len=None) == {
        'grablib.yml': yml,
        'droot': {'file.js': 'response text', 'file2.js': 'response text'},
        '.grablib.lock': """\
b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js file.js
b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file2.js file2.js\n"""
    }


def test_lock_local_file_changes(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x"
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    Grab(download_root='test-download-dir').download()
    assert mock_requests_get.call_count == 1
    assert gettree(tmpworkdir) == {
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x",
        'test-download-dir': {'x': 'response text'},
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js x\n'
    }
    mktree(tmpworkdir, {
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x2"
    })
    Grab(download_root='test-download-dir').download()
    assert mock_requests_get.call_count == 2
    assert gettree(tmpworkdir) == {
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x2",
        'test-download-dir': {'x2': 'response text'},
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js x2\n'
    }


def test_lock_remote_file_changes(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x"
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.side_effect = [
        MockResponse(),
        MockResponse(content=b'changed')
    ]
    Grab(download_root='s').download()
    assert mock_requests_get.call_count == 1
    assert gettree(tmpworkdir) == {
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x",
        's': {'x': 'response text'},
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js x\n'
    }
    tmpworkdir.join('s/x').remove()
    with pytest.raises(GrablibError):
        Grab(download_root='s').download()


zip_dowload_yml = """\
download_root: droot
download:
  'https://any-old-url.com/test_assets.zip':
    'test_assets/assets/(.+)': 'subdirectory/{filename}'"""
zip_downloaded_directory = {
    'grablib.yml': zip_dowload_yml,
    'droot': {'subdirectory': {'b.txt': 'b\n', 'a.txt': 'a\n'}},
    '.grablib.lock': """\
b56e6adc64a2a57319285ae64e64d2ec https://any-old-url.com/test_assets.zip :zip-lookup
0d815adb49aeaa79990afa6387b36014 https://any-old-url.com/test_assets.zip :zip-raw
60b725f10c9c85c70d97880dfe8191b3 https://any-old-url.com/test_assets.zip subdirectory/a.txt
3b5d5c3712955042212316173ccf37be https://any-old-url.com/test_assets.zip subdirectory/b.txt\n"""
}


def test_lock_zip(mocker, tmpworkdir):
    mktree(tmpworkdir, {'grablib.yml': zip_dowload_yml})
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.side_effect = request_fixture
    Grab().download()
    assert mock_requests_get.call_count == 1
    assert zip_downloaded_directory == gettree(tmpworkdir, max_len=None)
    Grab().download()
    assert mock_requests_get.call_count == 1
    assert zip_downloaded_directory == gettree(tmpworkdir, max_len=None)
    Grab().download()
    assert mock_requests_get.call_count == 1
    assert zip_downloaded_directory == gettree(tmpworkdir, max_len=None)
    tmpworkdir.join('droot/subdirectory/a.txt').remove()

    Grab().download()
    assert mock_requests_get.call_count == 2
    assert zip_downloaded_directory == gettree(tmpworkdir, max_len=None)


def test_lock_zip_remote_changed(mocker, tmpworkdir):
    mktree(tmpworkdir, {'grablib.yml': zip_dowload_yml})
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    zip_r = request_fixture('https://any-old-url.com/test_assets.zip')
    mock_requests_get.side_effect = [
        MockResponse(content=zip_r.content, headers={'content-type': 'application/zip'}),
        MockResponse(content=zip_r.content + b'x', headers={'content-type': 'application/zip'}),
    ]
    Grab().download()
    assert mock_requests_get.call_count == 1
    assert zip_downloaded_directory == gettree(tmpworkdir, max_len=None)
    tmpworkdir.join('droot/subdirectory/a.txt').remove()

    with pytest.raises(GrablibError):
        Grab().download()
    assert mock_requests_get.call_count == 2


def test_lock_unchanged(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x",
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js x\n',
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='test-download-dir')
    grab.download()
    assert gettree(tmpworkdir) == {
        'grablib.yml': "download:\n  'http://wherever.com/file.js': x",
        'test-download-dir': {'x': 'response text'},
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js x\n'
    }


def test_lock_extended(mocker, tmpworkdir):
    gl = """\
    download:
      'http://wherever.com/file1.js': x
      'http://wherever.com/file2.js': y
    """
    mktree(tmpworkdir, {
        'grablib.yml': gl,
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file1.js x\n',
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='test-download-dir')
    grab.download()
    assert gettree(tmpworkdir, max_len=0) == {
        'grablib.yml': gl,
        'test-download-dir': {'x': 'response text', 'y': 'response text'},
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file1.js x\n'
                         'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file2.js y\n'
    }


def test_lock_truncated_file_deleted(mocker, tmpworkdir):
    gl = """\
    download:
      'http://wherever.com/file1.js': x
    """
    mktree(tmpworkdir, {
        'grablib.yml': gl,
        'test-download-dir': {'x': 'response text', 'y': 'response text'},
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file1.js x\n'
                         'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file2.js y\n',
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='test-download-dir')
    grab.download()
    assert gettree(tmpworkdir, max_len=0) == {
        'grablib.yml': gl,
        'test-download-dir': {'x': 'response text'},
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file1.js x\n'
    }


def test_changed_file_url(mocker, tmpworkdir):
    gl = """\
    download:
      'http://wherever.com/file_different.js': x
    """
    mktree(tmpworkdir, {
        'grablib.yml': gl,
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js x\n',
        'test-download-dir': {'x': 'response text'},
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='test-download-dir')
    grab.download()
    assert gettree(tmpworkdir, max_len=0) == {
        'grablib.yml': gl,
        'test-download-dir': {'x': 'response text'},
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file_different.js x\n'
    }


def test_stale_changed(mocker, tmpworkdir):
    gl = """\
    download:
      'http://wherever.com/file.js': x
    """
    mktree(tmpworkdir, {
        'grablib.yml': gl,
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js old\n',
        'test-download-dir': {'old': 'response text - different'},
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='test-download-dir')
    with pytest.raises(GrablibError):
        grab.download()
    assert gettree(tmpworkdir) == {
        'grablib.yml': gl,
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js old\n',
        'test-download-dir': {'old': 'response text - different', 'x': 'response text'},
    }


def test_delete_stale_dir(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': 'download: {}',
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js path/to/x\n',
        'test-download-dir/path/to': {'x': 'response text'},
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='test-download-dir')
    grab.download()
    assert gettree(tmpworkdir, max_len=0) == {
        'grablib.yml': 'download: {}',
        'test-download-dir': {},
        '.grablib.lock': '\n'
    }


def test_already_deleted(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.yml': 'download: {}',
        '.grablib.lock': 'b5a3344a4b3651ebd60a1e15309d737c http://wherever.com/file.js path/to/x\n',
        'test-download-dir': {'foo': 'bar'},
    })
    mock_requests_get = mocker.patch('grablib.download.requests.Session.get')
    mock_requests_get.return_value = MockResponse()
    grab = Grab(download_root='test-download-dir')
    grab.download()
    assert gettree(tmpworkdir, max_len=0) == {
        'grablib.yml': 'download: {}',
        'test-download-dir': {'foo': 'bar'},
        '.grablib.lock': '\n'
    }
