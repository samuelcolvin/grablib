import os, json, zipfile, re, traceback, imp, requests, six
if six.PY3:
    from io import BytesIO as IO
else:
    from cStringIO import StringIO as IO

try:
    from termcolor import cprint
except:
    def cprint(string, *args, **kw):
        end = kw.get('end', None)
        print(string, end)
            
colour_lookup = {0: ('red',),
                 1: ('yellow',),
                 2: ('cyan',),
                 3: ('green',)}

DEFAULT_VERBOSITY = 2
DEFAULTS = {
    'target': '.', 
    'verbosity': DEFAULT_VERBOSITY,
    'overwrite': False,
    'file_permissions': None,
    'output': None,
}

class KnownError(Exception):
    """
    Exception used when the error is clear so no traceback is required.
    """
    pass

def process_args(args):
    try:
        if args.verbosity is not None:
            try:
                args.verbosity = int(args.verbosity)
            except Exception:
                raise KnownError('problem converting verbosity to int, value: "%s" is not an integer'\
                                          % args.verbosity)
        
        if not os.path.exists(args.def_path):
            raise KnownError('Libs definition file not found: %s' % args.def_path)
        path_lower = args.def_path.lower()
        if not any([path_lower.endswith(ext) for ext in ('.py', '.json')]):
            raise KnownError('Libs definition file does not have extension .py or .json: %s' % args.def_path)
        dfunc = (process_json_path, process_python_path)[path_lower.endswith('.py')]

        libs_info, options = dfunc(args.def_path)
        
        options = overwrite_options(options, {'target': args.target, 
                                              'overwrite': args.overwrite, 
                                              'verbosity': args.verbosity, 
                                              'file_permissions': args.file_permissions, 
                                              'output': None})

        return DownloadLibs(libs_info, **options).download()
    except KnownError as e:
        print('===================\nError: %s' % str(e))
    except Exception as e:
        print('Error: %s' % str(e))
        traceback.print_exc()
    return False

def process_json_path(json_path):
    """
    Takes the path of a json file and extracts libs_info and options
    """ 
    jcontent = json.load(open(json_path, 'r'))
    options = {k:v for k,v in list(DEFAULTS.items())}
    if 'libs' in jcontent:
        libs_info = jcontent['libs']
        for k, v in list(jcontent.items()):
            if k in DEFAULTS:
                options[k] = v
    else:
        libs_info = jcontent
    return libs_info, options

def process_python_path(python_fpath):
    """
    Takes the path of a python file and extracts libs_info and options
    """ 
    try:
        imp.load_source('GrabSettings', python_fpath)
        import GrabSettings
    except Exception as e:
        raise KnownError('Error importing %s: %s' % (python_fpath, str(e)))
    options = {k:v for k,v in list(DEFAULTS.items())}
    for name in list(DEFAULTS.keys()):
        if hasattr(GrabSettings, name):
            options[name] = getattr(GrabSettings, name)
    return GrabSettings.libs, options
    
    
def overwrite_options(options, overwrite_options):
    """
    Overwrite options (from settings file) with overwrite_options (typically from command line)
    """
    for attr in list(options.keys()):
        if overwrite_options[attr] is overwrite_options:
            options[attr] = overwrite_options[attr]
    if options['target'] is None:
        raise KnownError('target argument was None and target not defined in definition file')
    return options
            
class DownloadLibs(object):
    """
    main class for downloading library files based on json file.
    """
    def __init__(self, libs_info, target, overwrite=False, verbosity = DEFAULT_VERBOSITY, file_permissions = None, output = None):
        """
        initialize DownloadLibs.
        Args:
            def_path_string: dict, either url: destination or zip url: dict of regex: destination, see docs
            target: string, root folder to put files in
            overwrite: bool, whether or not to overwrite files that already exist, default is not to download existing
            verbosity: int, what to print 0 (nothing except errors), 1 (less), 2 (default), 3 (everything)
            file_permissions: int or None, if not None permissions to give downloaded files eg. 0666
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
        self.file_perm = file_permissions
        
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
        for url, value in list(self.libs_info.items()):
            try:
                if type(value) == dict:
                    success = self._process_zip(url, value)
                else:
                    success = self._process_normal_file(url, value)
                if success:
                    self.downloaded += 1
            except Exception as e:
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
                     for p in list(value.values())]
        zip_paths_exist = [os.path.exists(p) and p != self.target
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
            self.output('%d file in zip archive' % len(zipf.namelist()), colourv = 3)
            zcopied = 0
            for fn in zipf.namelist():
                for regex, dest_path in list(value.items()):
                    path_is_valid, new_path = self._get_new_path(fn, dest_path, regex = regex)
                    if not path_is_valid:
                        continue
                    _, dest = self._generate_path(self.target, new_path)
                    self._write(dest, zipf.read(fn))
                    zcopied += 1
                    break
        self.output('%d files copied from zip archive to target' % zcopied, colourv = 3)
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
            r = requests.get(url)
            if r.headers['content-type'].startswith('text'):
                return r.text
            else:
                return r.content
        except Exception as e:
            raise KnownError('URL: %s\nProblem occurred during download: %r\n*** ABORTING ***' % (url, e))
    
    def _write(self, dest, content):
        open(dest, 'wb').write(content)
        if self.file_perm:
            os.chmod(dest, self.file_perm)
    def _output(self, line, verbosity = DEFAULT_VERBOSITY, colourv = None):
        if verbosity <= self.verbosity:
            cv = (colourv, verbosity)[colourv is None]
            args = colour_lookup.get(cv, ())
            text = '%s%s' % (' ' * cv, line[:500])
            cprint(text, *args)

