import grablib

from .conftest import gettree, mktree


class MockResponse:
    def __init__(self, *, status_code=200, text='response text', headers=None):
        self.status_code = status_code
        self.text = text
        self.content = text.encode()
        self.headers = headers or {
            'content-type': 'application/json',
            'server': 'Mock'
        }


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
