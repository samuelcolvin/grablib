import os, json, urllib2, zipfile, cStringIO, re, traceback, imp

# lets try and use ujson, it's super quick and very cool
try:
    import ujson as json
except ImportError:
    import json
DEFAULT_VERBOSITY = 2
DEFAULTS = {
    'target': None, 
    'verbosity': DEFAULT_VERBOSITY,
    'overwrite': False,
    'file_permissions': None,
    'output': None,
}

class KnownError(Exception):
    pass

def download_json_path(json_path, target = None, overwrite = None, verbosity = None, file_permissions = None, output = None):
    jcontent = json.load(open(json_path, 'r'))
    options = {k:v for k,v in DEFAULTS.items()}
    if 'libs' in jcontent:
        libs_info = jcontent['libs']
        for k, v in jcontent.items():
            if k in DEFAULTS:
                options[k] = v
    else:
        libs_info = jcontent
    return _overwrite_options_download(libs_info, options, target, overwrite, verbosity, file_permissions, output)

def download_python_path(python_fpath, target = None, overwrite = None, verbosity = None, file_permissions = None, output = None):
    try:
        imp.load_source('GrabSettings', python_fpath)
        import GrabSettings
    except Exception, e:
        raise Exception('Error importing %s: %s' % (python_fpath, str(e)))
    options = {k:v for k,v in DEFAULTS.items()}
    for name in DEFAULTS.keys():
        if hasattr(GrabSettings, name):
            options[name] = getattr(GrabSettings, name)
    return _overwrite_options_download(GrabSettings.libs, options, target, overwrite, verbosity, file_permissions, output)
    
    
def _overwrite_options_download(libs_info, options, target, overwrite, verbosity, file_permissions, output):
    for attr, default in options.items():
        if locals()[attr] is not None:
            options[attr] = locals()[attr]
    if options['target'] is None:
        raise KnownError('target argument was None and target not defined in definition file')
    return DownloadLibs(libs_info, 
                        options['target'], 
                        options['overwrite'], 
                        options['verbosity'],
                        options['file_permissions'],
                        options['output']).download()
            
class DownloadLibs(object):
    """
    main class for downloading library files based on json file.
    """
    def __init__(self, libs_info, target, overwrite=False, verbosity = DEFAULT_VERBOSITY, file_perm = None, output = None):
        """
        initialize DownloadLibs.
        Args:
            def_path_string: dict, either url: destination or zip url: dict of regex: destination, see docs
            target: string, root folder to put files in
            overwrite: bool, whether or not to overwrite files that already exist, default is not to download existing
            verbosity: int, what to print 0 (nothing except errors), 1 (less), 2 (normal), 3 (everything)
            file_perm: int or None, if not None permissions to give downloaded files eg. 0666
            output: function or None, if not None alternative function to recieve output statements.
        """
        self.libs_info = libs_info
        self.target = target
        self.overwrite = overwrite
        self.verbosity = verbosity
        if output:
            self.output = output
        else:
            self.output = self._output
        if overwrite != DEFAULTS['overwrite']:
            self.output('Overwrite set to %r' % overwrite)
        if verbosity != DEFAULTS['verbosity']:
            self.output('Verbosity set to %d' % verbosity)
        self.file_perm = file_perm
        
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
        self.downloaded = 0
        self.ignored = 0
        for url, value in self.libs_info.items():
            try:
                if type(value) == dict:
                    success = self._process_zip(url, value)
                else:
                    success = self._process_normal_file(url, value)
                if success:
                    self.downloaded += 1
            except Exception, e:
                self.output('Error Downloading "%s" to "%s"' % (url, value), 0)
                self.output('ERROR: %s' % str(e), 0)
                if not isinstance(e, KnownError):
                    self.output(traceback.format_exc(), 0)
                return False
        self.output('library download finished: %d files downloaded, %d existing and ignored' % (self.downloaded, self.ignored), 1)
        return True
        
    def _process_normal_file(self, url, dst):
        path_is_valid, path = self._get_new_path(url, dst)
        if not path_is_valid:
            self.output('URL "%s" is not valid, not downloading' % url)
            return False
        exists, dest = self._generate_path(self.target, path)
        if exists and not self.overwrite:
            self.output('file already exists: "%s"' % path, 3)
            self.output('  *** IGNORING THIS DOWNLOAD ***\n', 3)
            self.ignored += 1
            return False
        self.output('DOWNLOADING: %s' % path)
        content = self._get_url(url)
        try: content = content.encode('utf8')
        except: pass
        self._write(dest, content)
        self.output('Successfully downloaded %s\n' % os.path.basename(path), 3)
        return True
    
    def _process_zip(self, url, value):
        self.output('dict value found, assuming "%s" is a zip file' % url, 3)
        zip_paths = [os.path.dirname(
                     os.path.join(self.target, p))
                     for p in value.values()]
        zip_paths_exist = [os.path.exists(p) and p != self.target
                           for p in zip_paths]
        if all(zip_paths_exist) and not self.overwrite:
            self.output('all paths already exist for zip extraction', 3)
            self.output('  *** IGNORING THIS DOWNLOAD ***\n', 3)
            self.ignored += 1
            return False
        self.output('DOWNLOADING ZIP: %s...' % url)
        content = self._get_url(url)
        zipinmemory = cStringIO.StringIO(content)
        with zipfile.ZipFile(zipinmemory) as zipf:
            self.output('%d file in zip archive' % len(zipf.namelist()))
            zcopied = 0
            for fn in zipf.namelist():
                for regex, dest_path in value.items():
                    path_is_valid, new_path = self._get_new_path(fn, dest_path, regex = regex)
                    if not path_is_valid:
                        continue
                    _, dest = self._generate_path(self.target, new_path)
                    self._write(dest, zipf.read(fn))
                    zcopied += 1
                    break
        self.output('%d files copied from zip archive to target' % zcopied)
        self.output('', 3)
        return True
    
    def _get_new_path(self, src_path, target, regex = '.*/(.*)'):
        """
        check url complies with regex and generate new filename
        """
        m = re.search(regex, src_path)
        if not m:
            return False, None
        if 'filename' in m.groupdict():
            new_fn = m.groupdict()['filename']
        else:
            new_fn = m.groups()[0]
        return True, re.sub('{{ *filename *}}', new_fn, target)
        

    def _generate_path(self, *path_args):
        dest = os.path.join(*path_args)
        if os.path.exists(dest):
            return True, dest
        dest_dir = os.path.dirname(dest)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        return False, dest
    
    def _get_url(self, url):
        try:
            response = urllib2.urlopen(url)
            return response.read()
        except Exception, e:
            raise KnownError('URL: %s\nProblem occurred during download: %r\n*** ABORTING ***' % (url, e))
    
    def _write(self, dest, content):
        open(dest, 'w').write(content)
        if self.file_perm:
            os.chmod(dest, self.file_perm)

    def _output(self, line, verbosity = DEFAULT_VERBOSITY):
        if verbosity <= self.verbosity:
            print line


