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
    downloaded = 0
    ignored = 0

    def __init__(self, libs_info, sites=None, **kw):
        """
        initialize DownloadLibs.
        Args:
            libs_info: dict, either url: destination or zip url: dict of regex: destination, see docs
            
            sites: dict of names of sites to simplify similar urls, see examples.
        """
        super(DownloadLibs, self).__init__(**kw)
        self.libs_info = libs_info
        self.sites = self._setup_sites(sites)

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
        self.output('Downloading files to: %s' % self.libs_root, 1)
        for url_base, value in list(self.libs_info.items()):
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
        exists, dest = self._generate_path(self.libs_root, path)
        if exists and not self.overwrite:
            self.output('file already exists: "%s"' % path, 3)
            self.output('  *** IGNORING THIS DOWNLOAD ***\n', 3)
            self.ignored += 1
            return False
        self.output('DOWNLOADING: %s' % path)
        content = self._get_url(url)
        try:
            content = content.encode('utf8')
        except (UnicodeDecodeError, AttributeError):
            pass
        self._write(dest, content)
        self.output('Successfully downloaded %s\n' % os.path.basename(path), 3)
        return True

    def _process_zip(self, url, value):
        self.output('dict value found, assuming "%s" is a zip file' % url, 3)
        zip_paths = [os.path.dirname(
            os.path.join(self.libs_root, p))
                     for p in list(value.values())]
        zip_paths_exist = [os.path.exists(p) and p != self.libs_root
                           for p in zip_paths]
        if all(zip_paths_exist) and not self.overwrite:
            self.output('all paths already exist for zip extraction', 3)
            self.output('  *** IGNORING THIS DOWNLOAD ***\n', 3)
            self.ignored += 1
            return False
        self.output('DOWNLOADING ZIP: %s...' % url)
        content = self._get_url(url)
        zipinmemory = IO(content)
        with zipfile.ZipFile(zipinmemory) as zipf:
            def save_file(filename, new_path, dest_path):
                _, dest = self._generate_path(self.libs_root, new_path)
                self._write(dest, zipf.read(filename))

            self.output('%d file in zip archive' % len(zipf.namelist()), colourv=3)
            zcopied = self._search_paths(zipf.namelist(), value.items(), save_file)
        self.output('%d files copied from zip archive to libs_root' % zcopied, colourv=3)
        self.output('', 3)
        return True

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
            if r.headers['content-type'].startswith('text'):
                return r.text
            else:
                return r.content
        except RequestException as e:
            raise GrablibError('URL: %s\nProblem occurred during download: %r\n*** ABORTING ***' % (url, e))
