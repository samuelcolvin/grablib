from __future__ import unicode_literals

import os
import re
import shutil
import zipfile

import requests
from requests.exceptions import RequestException

try:
    from cStringIO import StringIO as IO
except ImportError:
    from io import BytesIO as IO

from .common import GrablibError, ProcessBase, logger, str


class DownloadLibs(ProcessBase):
    """
    main class for downloading library files based on json file.
    """

    def __init__(self, libs_info, sites=None, **kwargs):
        """
        initialize DownloadLibs.
        :param libs_info: dict, either url: destination or zip url: dict of regex: destination, see docs
        :param sites: dict of names of sites to simplify similar urls, see examples.
        """
        super(DownloadLibs, self).__init__(**kwargs)
        self.libs_info = libs_info
        self.sites = self._setup_sites(sites)
        self.downloaded = 0
        self.ignored = 0

    def download(self):
        """
        perform download and save.
        """
        logger.warning('Downloading files to: %s', self.download_root)
        if self.overwrite and os.path.exists(self.download_root):
            logger.warning('Overwrite true, deleting %s entirely', self.download_root)
            shutil.rmtree(self.download_root)
            os.mkdir(self.download_root)

        for url_base, value in self.libs_info.items():
            url = self._setup_url(url_base)
            try:
                if isinstance(value, dict):
                    self._process_zip(url, value)
                else:
                    self._process_normal_file(url, value)
            except GrablibError as e:
                # create new exception to show which file download went wrong for
                raise GrablibError('Downloading "%s" to "%s"\n    %s' % (url, value, e))
        logger.warning('Download finished: %d files downloaded, %d existing and ignored', self.downloaded, self.ignored)

    def _process_normal_file(self, url, dst):
        path = self._file_path(url, dst)
        exists, full_path = self._generate_path(self.download_root, path)
        if exists and not self.overwrite:
            logger.debug('file already exists: "%s" IGNORING', path)
            self.ignored += 1
            return
        logger.info('DOWNLOADING: %s', path)
        content = self._get_url(url)
        self._write(full_path, content)
        logger.debug('Successfully downloaded %s\n', os.path.basename(path))
        self.downloaded += 1

    def _process_zip(self, url, value):
        logger.info('DOWNLOADING ZIP: %s...', url)
        content = self._get_url(url)
        zipinmemory = IO(content)
        zcopied, zignored = 0, 0
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
                        path = self._file_path(filepath, target, regex_pattern)
                        exists, full_path = self._generate_path(self.download_root, path)
                        logger.debug('    %s > %s based on regex %s', filepath, path, regex_pattern)
                        if exists and not self.overwrite:
                            zignored += 1
                            logger.debug('    file already exists: "%s" IGNORING', path)
                        else:
                            zcopied += 1
                            self._write(full_path, zipf.read(filepath))
                    break
                if not target_found:
                    logger.debug('    no target found')
        logger.info('%d files copied from zip archive, %d ignored as already exist', zcopied, zignored)
        self.downloaded += 1

    def _file_path(self, src_path, dest, regex=r'/([^/]+)$'):
        """
        check src_path complies with regex and generate new filename
        """
        m = re.search(regex, src_path)
        if m.groups():
            new_fn = m.groups()[-1]
            if dest.endswith('/'):
                dest += '{name}'
            dest = re.sub(r'{{? ?(?:filename|name) ?}?}', new_fn, dest)
        # remove starting slash so path can't be absolute
        return dest.lstrip(' /')

    def _setup_sites(self, sites):
        if sites is None:
            return None
        if not isinstance(sites, dict):
            raise GrablibError('sites is not a dict: %r' % sites)
        # blunt way of making sure all sites in sites are replaced, with luck 5 loops should be enough
        for _ in range(5):
            for k in sites:
                sites[k] = self._replace_all(sites[k], sites)
        return sites

    def _setup_url(self, url_base):
        if self.sites is None:
            return url_base
        else:
            return self._replace_all(url_base, self.sites)

    def _replace_all(self, base, context):
        for lookup, replace in context.items():
            base = re.sub('{{? ?%s ?}?}' % lookup, replace, base)
        return base

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
            if r.headers['content-type'].startswith('text'):
                return r.text
            else:
                return r.content
