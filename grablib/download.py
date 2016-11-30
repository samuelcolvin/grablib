import re
import zipfile
from io import BytesIO as IO
from pathlib import Path

import requests
from requests.exceptions import RequestException

from .common import GrablibError, logger

ALIASES = {
    'GITHUB': 'https://raw.githubusercontent.com',
    'CDNJS': 'http://cdnjs.cloudflare.com/ajax/libs',
}


class Downloader:
    """
    main class for downloading library files based on json file.
    """

    def __init__(self, *, download_root, downloads, aliases=None, **data):
        """
        :param libs_info: dict, either url: destination or zip url: dict of regex: destination, see docs
        :param sites: dict of names of sites to simplify similar urls, see examples.
        """
        self.download_root = Path(download_root).absolute()
        self.downloads = downloads
        self.aliases = ALIASES.copy()
        if aliases:
            self.aliases.update(aliases)
        self.downloaded = 0

    def __call__(self):
        """
        perform download and save.
        """
        logger.info('Downloading files to: %s', self.download_root)

        for url_base, value in self.downloads.items():
            url = self._setup_url(url_base)
            try:
                if isinstance(value, dict):
                    self._process_zip(url, value)
                else:
                    self._process_normal_file(url, value)
            except GrablibError as e:
                # create new exception to show which file download went wrong for
                raise GrablibError('Downloading "%s" to "%s"\n    %s' % (url, value, e))
        logger.info('Download finished: %d files downloaded', self.downloaded)

    def _process_normal_file(self, url, dst):
        new_path = self._file_path(url, dst, regex=r'/(?P<filename>[^/]+)$')
        logger.info('downloading: %s > %s...', url, new_path.relative_to(self.download_root))
        content = self._get_url(url)
        self._write(new_path, content)
        self.downloaded += 1

    def _process_zip(self, url, value):
        logger.info('downloading zip: %s...', url)
        content = self._get_url(url)
        zipinmemory = IO(content)
        zcopied = 0
        with zipfile.ZipFile(zipinmemory) as zipf:
            logger.debug('%d file in zip archive', len(zipf.namelist()))

            for filepath in zipf.namelist():
                if filepath.endswith('/'):
                    continue
                target_found = False
                logger.debug('  searching for target for %s...', filepath)
                for regex_pattern, targets in value.items():
                    if not re.match(regex_pattern, filepath):
                        continue
                    target_found = True
                    if targets is None:
                        logger.debug('    target null, skipping')
                        break
                    if isinstance(targets, str):
                        targets = [targets]
                    for target in targets:
                        new_path = self._file_path(filepath, target, regex=regex_pattern)
                        logger.debug('    %s > %s based on regex %s',
                                     filepath, new_path.relative_to(self.download_root), regex_pattern)
                        self._write(new_path, zipf.read(filepath))
                        zcopied += 1
                    break
                if not target_found:
                    logger.debug('    no target found')
        logger.info('%d files copied from zip archive', zcopied)
        self.downloaded += 1

    def _file_path(self, src_path, dest, regex):
        """
        check src_path complies with regex and generate new filename
        """
        m = re.search(regex, src_path)
        if dest.endswith('/'):
            dest += '{filename}'
        if m:
            names = m.groupdict() or {'filename': m.groups()[-1]}
            for name, value in names.items():
                dest = dest.replace('{%s}' % name, value)
        # remove starting slash so path can't be absolute
        dest = dest.lstrip(' /')
        if not dest:
            raise GrablibError('destination path may not resolve to be null')
        new_path = self.download_root.joinpath(dest)
        new_path.relative_to(self.download_root)
        return new_path

    def _setup_url(self, url_base):
        for name, value in self.aliases.items():
            url_base = url_base.replace(name, value)
        return url_base

    def _get_url(self, url):
        try:
            r = requests.get(url)
        except RequestException as e:
            raise GrablibError('URL: {}\n'
                               'Problem occurred during download: {}: {}\n'
                               '*** ABORTING ***'.format(url, e.__class__.__name__, e))
        else:
            if r.status_code != 200:
                raise GrablibError('URL: %s\nProblem occurred during download, wrong status code: %d\n*** ABORTING ***'
                                   % (url, r.status_code))
            return r.content

    def _write(self, new_path: Path, data):
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_bytes(data)
