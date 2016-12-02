import hashlib
import json
import re
import zipfile
from collections import OrderedDict
from io import BytesIO as IO
from pathlib import Path

import requests
from requests.exceptions import RequestException

from .common import GrablibError, main_logger, progress_logger

ALIASES = {
    'GITHUB': 'https://raw.githubusercontent.com',
    'CDNJS': 'http://cdnjs.cloudflare.com/ajax/libs',
}
ZIP_VALUE_REF = ':zip-lookup'
ZIP_RAW_REF = ':zip-raw'


class Downloader:
    """
    main class for downloading library files based on json file.
    """

    def __init__(self, *,
                 download_root: str,
                 download: dict,
                 aliases: dict=None,
                 lock: str='.grablib.lock',
                 **data):
        """
        :param download_root: path to download file to
        :param downloads: dict of urls and paths to download from from > to
        :param aliases: extra aliases for download addresses
        """
        self.download_root = Path(download_root).absolute()
        self.download = download
        self._aliases = ALIASES.copy()
        aliases and self._aliases.update(aliases)
        self._downloaded = 0
        self._skipped = 0
        self._lock_file = lock and Path(lock)
        self._new_lock = []
        self._current_lock = {}
        self._session = requests.Session()

    def __call__(self):
        """
        perform download and save.
        """
        main_logger.info('downloading files to: %s', self.download_root)

        self._read_lock()
        for url_base, value in self.download.items():
            url = self._setup_url(url_base)
            try:
                if isinstance(value, dict):
                    self._process_zip(url, value)
                else:
                    self._process_normal_file(url, value)
            except GrablibError as e:
                # create new exception to show which file download went wrong for
                if isinstance(value, OrderedDict):
                    value = dict(value)
                raise GrablibError('Error downloading "{}" to "{}"'.format(url, value)) from e
        self._save_lock()
        main_logger.info('Download finished: %d files downloaded, %d existing and ignored',
                         self._downloaded, self._skipped)

    def _process_normal_file(self, url, dst):
        new_path = self._file_path(url, dst, regex=r'/(?P<filename>[^/]+)$')
        lock_hash, unchanged = self._file_exists_unchanged(url, new_path)
        if unchanged:
            self._add_to_lock(url, *self._current_lock[url])
            self._skipped += 1
            progress_logger.debug('%s already exists unchanged, not downloading', url)
            return

        progress_logger.info('downloading: %s > %s...', url, new_path.relative_to(self.download_root))
        content = self._get_url(url)
        remote_hash = self._data_hash(content)
        if lock_hash and remote_hash != lock_hash:
            progress_logger.error('Security warning: hash of remote file %s has changed!', url)
            raise GrablibError('remote hash mismatch')
        self._write(new_path, content, url)
        self._downloaded += 1

    def _file_exists_unchanged(self, url, path: Path):
        name_hash = self._current_lock.get(url)
        if name_hash is None:
            return None, False
        name, lock_hash = name_hash
        if name != str(path.relative_to(self.download_root)):
            return lock_hash, False
        file_hash = self._path_hash(path)
        return lock_hash, file_hash == lock_hash

    def _process_zip(self, url, value):
        value_hash = self._data_hash(json.dumps(value, sort_keys=True).encode())
        lock_hash, unchanged = self._zip_exists_unchanged(url, value_hash)
        if unchanged:
            [self._add_to_lock(url, name, lock_hash) for name, lock_hash in self._current_lock[url]]
            self._skipped += 1
            progress_logger.debug('%s already exists unchanged, not downloading', url)
            return
        progress_logger.info('downloading zip: %s...', url)
        content = self._get_url(url)
        remote_hash = self._data_hash(content)
        if lock_hash and remote_hash != lock_hash:
            progress_logger.error('Security warning: hash of remote file %s has changed!', url)
            raise GrablibError('remote hash mismatch')
        self._add_to_lock(url, ZIP_VALUE_REF, value_hash)
        self._add_to_lock(url, ZIP_RAW_REF, remote_hash)
        zcopied = self._extract_zip(url, content, value)
        progress_logger.info('%d files copied from zip archive', zcopied)
        self._downloaded += 1

    def _extract_zip(self, url, content, value):
        zipinmemory = IO(content)
        zcopied = 0
        with zipfile.ZipFile(zipinmemory) as zipf:
            progress_logger.debug('%d files in zip archive', len(zipf.namelist()))

            for filepath in zipf.namelist():
                if filepath.endswith('/'):
                    continue
                regex_pattern, targets = None, None
                for r, t in value.items():
                    if re.match(r, filepath):
                        regex_pattern, targets = r, t
                        break
                if regex_pattern is None:
                    progress_logger.debug('"%s" no target found', filepath)
                elif targets is None:
                    progress_logger.debug('"%s" skipping (regex: "%s")', filepath, regex_pattern)
                else:
                    if isinstance(targets, str):
                        targets = [targets]
                    for target in targets:
                        new_path = self._file_path(filepath, target, regex=regex_pattern)
                        progress_logger.debug('"%s" > "%s" (regex: "%s")',
                                              filepath, new_path.relative_to(self.download_root), regex_pattern)
                        self._write(new_path, zipf.read(filepath), url)
                        zcopied += 1
        return zcopied

    def _zip_exists_unchanged(self, url, value_hash):
        name_hashes = self._current_lock.get(url)
        zip_hash = None
        if name_hashes is None:
            return zip_hash, False
        found_change = False
        for name, lock_hash in name_hashes:
            if name == ZIP_RAW_REF:
                zip_hash = lock_hash
                continue
            if name == ZIP_VALUE_REF:
                file_hash = value_hash
            else:
                file_hash = self._path_hash(self.download_root.joinpath(name))
            if file_hash != lock_hash:
                found_change = True
        return zip_hash, not found_change and zip_hash is not None

    def _file_path(self, src_path, dest, regex):
        """
        check src_path complies with regex and generate new filename
        """
        m = re.search(regex, src_path)
        if dest.endswith('/') or dest == '':
            dest += '{filename}'
        names = m.groupdict()
        if not names and m.groups():
            names = {'filename': m.groups()[-1]}
        for name, value in names.items():
            dest = dest.replace('{%s}' % name, value)
        # remove starting slash so path can't be absolute
        dest = dest.strip(' /')
        if not dest:
            progress_logger.error('destination path must not resolve to be null')
            raise GrablibError('bad path')
        new_path = self.download_root.joinpath(dest)
        new_path.relative_to(self.download_root)
        return new_path

    def _setup_url(self, url_base):
        for name, value in self._aliases.items():
            url_base = url_base.replace(name, value)
        return url_base

    def _get_url(self, url):
        try:
            r = self._session.get(url)
        except RequestException as e:
            progress_logger.error('Problem occurred during download: %s: %s', e.__class__.__name__, e)
            raise GrablibError('request error') from e
        else:
            if r.status_code != 200:
                progress_logger.error('Wrong status code: %d', r.status_code)
                raise GrablibError('Wrong status code')
            return r.content

    def _write(self, new_path: Path, data: bytes, url: str):
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_bytes(data)
        h = self._path_hash(new_path)
        self._add_to_lock(url, str(new_path.relative_to(self.download_root)), h)

    def _add_to_lock(self, url: str, name: str, _hash: str):
        self._new_lock.append({
            'url': url,
            'name': name,
            'hash': _hash,
        })

    def _path_hash(self, path: Path):
        if not path.exists():
            return
        data = path.read_bytes()
        return self._data_hash(data)

    def _data_hash(self, data: bytes):
        return hashlib.md5(data).hexdigest()

    def _read_lock(self):
        if self._lock_file and self._lock_file.exists():
            with self._lock_file.open() as f:
                for line in f:
                    _hash, url, name = line.strip('\n').split(' ')
                    v = name, _hash
                    existing_v = self._current_lock.get(url)
                    if existing_v is None:
                        self._current_lock[url] = v
                    elif isinstance(existing_v, tuple):
                        self._current_lock[url] = [existing_v, v]
                    else:
                        existing_v.append(v)

    def _save_lock(self):
        if self._lock_file is None:
            return
        self._new_lock.sort(key=lambda v: (v['url'], v['name']))
        self._lock_file.write_text('\n'.join('{hash} {url} {name}'.format(**v) for v in self._new_lock) + '\n')
