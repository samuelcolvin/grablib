from pathlib import Path
import grablib

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


def test_simple_download(mocker, tmpworkdir):
    mktree(tmpworkdir, {
        'grablib.json': '{"http://wherever.com/moment.js": "x"}'
    })
    mock_requests_get = mocker.patch('grablib.download.requests.get')
    mock_requests_get.return_value = MockResponse()
    grablib.grab('grablib.json', download_root='test-download-dir')
    assert gettree(tmpworkdir) == {
        'grablib.json': '{"http://wherever.com/moment.js": "x"}',
        'test-download-dir': {'x': 'response text'},
    }


def test_zip_download(mocker, tmpworkdir):
    mock_requests_get = mocker.patch('grablib.download.requests.get')
    mock_requests_get.side_effect = request_fixture
    mktree(tmpworkdir, {
        'grablib.json': """
    {
      "https://any-old-url.com/test_assets.zip":
      {
        "test_assets/assets/(.+)": "subdirectory/{{ filename }}"
      }
    }
    """})
    grablib.grab('grablib.json', download_root='test-download-dir')
    assert gettree(tmpworkdir.join('test-download-dir')) == {'subdirectory': {'b.txt': 'b\n', 'a.txt': 'a\n'}}
