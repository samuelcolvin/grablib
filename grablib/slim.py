import os

from .common import ProcessBase

try:
    from slimit import minify
except ImportError:
    SLIM_OK = False
else:
    SLIM_OK = True


class SlimLibs(ProcessBase):
    def __init__(self, slim_info, **kw):
        """
        initialize SlimLibs.
        Args:
            slim_settings: definition of slim process
            
            libs_root_slim: root directory to put slimmed files in.
        """
        super(SlimLibs, self).__init__(**kw)
        self.slim_info = slim_info

    def slim(self):
        search_settings = []
        for dest_path, sets in self.slim_info.items():
            self.slim_info[dest_path]['files'] = []
            if isinstance(sets['regex'], list):
                for r in sets['regex']:
                    search_settings.append((r, dest_path))
            else:
                search_settings.append((sets['regex'], dest_path))

        found = self._search_paths(self._get_nameslist(self.libs_root), search_settings, self.add_file)
        self.output('%d files found for slimming' % found, 3)
        for dest_path, sets in self.slim_info.items():
            self.output('combining ' + ','.join(sets['files']), 3)
            _, dest = self._generate_path(self.libs_root_slim, dest_path)
            content = '\n'.join(open(f, 'r').read() for f in sets['files'])

            content = self._test_minify(content, sets)

            self._write(dest, content)
            self.output('%d files combined to generate %s' % (len(sets['files']), dest))
        return True

    def _get_nameslist(self, root_dir):
        nameslist = []
        for root, _, files in os.walk(root_dir):
            for f in files:
                nameslist.append(os.path.join(root, f))
        return nameslist

    def add_file(self, filename, new_path, dest_path):
        self.slim_info[dest_path]['files'].append(filename)

    def _test_minify(self, content, sets):
        if 'js_slim' in sets['options']:
            if not SLIM_OK:
                self.output('Slimit (https://github.com/rspivak/slimit) not available, not minifying!', 0)
                return content
            mangle = 'js_mangle' in sets['options']
            mangle_toplevel = 'js_mangle_toplevel' in sets['options']
            content = minify(content, mangle=mangle, mangle_toplevel=mangle_toplevel)
            self.output('content minified, mange = %r, mangle_toplevel = %r' % (mangle, mangle_toplevel), colourv=3)
        return content
