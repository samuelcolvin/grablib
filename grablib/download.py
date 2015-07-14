import os
import zipfile
import re

import requests
from requests.exceptions import RequestException

try:
    from cStringIO import StringIO as IO
except ImportError:
    from io import BytesIO as IO

from .common import GrablibError, ProcessBase


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

    def __call__(self):
        """
        alias to download
        """
        return self.download()

    def download(self):
        """
        perform download and save.
        """
        self.output('', 3)
        self.output('Downloading files to: %s' % self.download_root, 1)
        for url_base, value in self.libs_info.items():
            url = self._setup_url(url_base)
            try:
                if isinstance(value, dict):
                    success = self._process_zip(url, value)
                else:
                    success = self._process_normal_file(url, value)
                if success:
                    self.downloaded += 1
            except GrablibError as e:
                # create new exception to show which file download went wrong for
                raise GrablibError('Downloading "%s" to "%s"\n    %s' % (url, value, e))
        self.output('Library download finished: %d files downloaded, '
                    '%d existing and ignored' % (self.downloaded, self.ignored), 1)
        return True

    def _process_normal_file(self, url, dst):
        path_is_valid, path = self._get_new_path(url, dst)
        if not path_is_valid:
            self.output('URL "%s" is not valid, not downloading' % url)
            return False
        exists, dest = self._generate_path(self.download_root, path)
        if exists and not self.overwrite:
            self.output('file already exists: "%s"' % path, 3)
            self.output('  *** IGNORING THIS DOWNLOAD ***\n', 3)
            self.ignored += 1
            return False
        self.output('DOWNLOADING: %s' % path)
        content = self._get_url(url)
        self._write(dest, content)
        self.output('Successfully downloaded %s\n' % os.path.basename(path), 3)
        return True

    def _process_zip(self, url, value):
        self.output('dict value found, assuming "%s" is a zip file' % url, 3)

        zip_paths = [os.path.dirname(os.path.join(self.download_root, p)) for p in list(value.values())]
        zip_paths_exist = [os.path.exists(p) and p != self.download_root for p in zip_paths]

        if all(zip_paths_exist) and not self.overwrite:
            self.output('all paths already exist for zip extraction', 3)
            self.output('  *** IGNORING THIS DOWNLOAD ***\n', 3)
            self.ignored += 1
            return False
        self.output('DOWNLOADING ZIP: %s...' % url)
        content = self._get_url(url)
        zipinmemory = IO(content)
        zcopied = 0
        with zipfile.ZipFile(zipinmemory) as zipf:
            self.output('%d file in zip archive' % len(zipf.namelist()), colourv=3)

            for filepath, regex in self._search_paths(zipf.namelist(), value.keys()):
                new_name_base = value[regex]
                path_is_valid, new_path = self._get_new_path(filepath, new_name_base, regex)
                if not path_is_valid:
                    raise GrablibError('filepath "%s" does not match regex "%s"' % filepath, regex)
                zcopied += 1
                _, dest = self._generate_path(self.download_root, new_path)
                self._write(dest, zipf.read(filepath))

        self.output('%d files copied from zip archive to download_root' % zcopied, colourv=3)
        self.output('', 3)
        return True

    @staticmethod
    def _get_new_path(src_path, dest, regex='.*/(.*)'):
        """
        check src_path complies with regex and generate new filename
        """
        m = re.search(regex, src_path)
        if not m:
            return False, None
        new_fn = None
        if 'filename' in m.groupdict():
            new_fn = m.groupdict()['filename']
        elif len(m.groups()) > 0:
            new_fn = m.groups()[0]
        if new_fn:
            dest = re.sub('{{ *filename *}}', new_fn, dest)
        return True, dest

    def _setup_sites(self, sites):
        if sites is None:
            return None
        if not isinstance(sites, dict):
            raise GrablibError('sites is not a dict: %r' % sites)
        # blunt way of making sure all sites in sites are replaced
        # with luck 5 files sound be enough!
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
            base = re.sub('{{ *%s *}}' % lookup, replace, base)
        return base

    def _get_url(self, url):
        try:
            r = requests.get(url)
        except RequestException as e:
            raise GrablibError('URL: %s\nProblem occurred during download: %r\n*** ABORTING ***' % (url, e))
        else:
            if r.status_code != 200:
                raise GrablibError('URL: %s\nProblem occurred during download, wrong status code: %d\n*** ABORTING ***'
                                   % (url, r.status_code))
            if r.headers['content-type'].startswith('text'):
                return r.text
            else:
                return r.content
