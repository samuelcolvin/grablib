import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Union

import click

from .common import GrablibError, main_logger, progress_logger

STARTS_DOWNLOAD = re.compile('^(?:DOWNLOAD|DL)/')
STARTS_NODE_M = re.compile('^(?:NODE_MODULES|NM)/')
STARTS_SRC = re.compile('^SRC/')
StrPath = Union[str, Path]


def insert_hash(path: Path, content: Union[str, bytes], *, hash_length=7, hash_algorithm=hashlib.md5):
    """
    Insert a hash based on the content into the path after the first dot.

    hash_length 7 matches git commit short references
    """
    if isinstance(content, str):
        content = content.encode()
    hash_ = hash_algorithm(content).hexdigest()[:hash_length]
    if '.' in path.name:
        new_name = re.sub(r'\.', f'.{hash_}.', path.name, count=1)
    else:
        new_name = f'{path.name}.{hash_}'
    return path.with_name(new_name)


class Builder:
    """
    main class for "building" assets eg. concatenating and minifying js and compiling sass
    """

    def __init__(self, *, build_root: StrPath, build: dict, download_root: StrPath=None, debug=False, **data):
        self.build_root = Path(build_root).absolute()
        self.build = build
        self.download_root = download_root and Path(download_root).resolve()
        self.files_built = 0
        self.debug = debug
        self._jsmin = None

    def __call__(self):
        wipe_data = self.build.get('wipe', None)
        wipe_data and self.wipe(wipe_data)

        cat_data = self.build.get('cat', None)
        cat_data and self.cat(cat_data)

        sass_data = self.build.get('sass', None)
        sass_data and self.sass(sass_data)

    def cat(self, data):
        start = datetime.now()
        total_files_combined = 0
        for dest, srcs in data.items():
            if not isinstance(srcs, list):
                raise GrablibError('source files for concatenation should be a list')

            final_content, files_combined = '', 0
            for src in srcs:
                if isinstance(src, str):
                    src = {'src': src}
                path = self._file_path(src['src'])
                content = self._read_file(path)
                files_combined += 1
                for pattern, rep in src.get('replace', {}).items():
                    content = re.sub(pattern, rep, content)
                final_content += '/* === {} === */\n{}\n'.format(path.name, content.strip('\n'))
                progress_logger.debug('  appending %s', path.name)

            if files_combined == 0:
                main_logger.warning('no files found to form "%s"', dest)
                continue
            dest_path = self._dest_path(dest)
            self._write(dest_path, final_content)
            total_files_combined += files_combined
            progress_logger.info('%d files combined to form "%s"', files_combined, dest)

        time_taken = (datetime.now() - start).total_seconds() * 1000
        main_logger.info('%d files concatenated in %0.0fms', total_files_combined, time_taken)

    def sass(self, data):
        for dest, d in data.items():
            if isinstance(d, str):
                d = {'src': d}
            src_path = self._file_path(d['src'])
            dest_path = self._dest_path(dest)
            sass_gen = SassGenerator(
                input_dir=src_path,
                output_dir=dest_path,
                download_root=self.download_root,
                include=d.get('include'),
                exclude=d.get('exclude'),
                replace=d.get('replace'),
                debug=self.debug)
            sass_gen()

    def wipe(self, regexes):
        if isinstance(regexes, str):
            regexes = [regexes]
        count = 0
        regexes = [re.compile(r) for r in regexes]
        for path in self.build_root.glob('**/*'):
            relative_path = str(path.relative_to(self.build_root))
            for regex in regexes:
                if regex.fullmatch(relative_path):
                    if path.is_dir():
                        progress_logger.debug('deleting directory "%s" based on "%s"', relative_path, regex.pattern)
                        shutil.rmtree(str(path))
                    else:
                        assert path.is_file()
                        progress_logger.debug('deleting file "%s" on "%s"', relative_path, regex.pattern)
                        path.unlink()
                    count += 1
                    break
        main_logger.info('%d paths deleted', count)

    def _dest_path(self, p):
        new_path = self.build_root.joinpath(p)
        new_path.relative_to(self.build_root)
        return new_path

    def _file_path(self, src_path: str):
        if STARTS_DOWNLOAD.match(src_path):
            assert self.download_root
            _src_path = STARTS_DOWNLOAD.sub('', src_path)
            return self.download_root.joinpath(_src_path).resolve()
        else:
            return Path(src_path).resolve()

    @property
    def jsmin(self) -> Callable[[str, str], str]:
        if self._jsmin is None:
            try:
                from jsmin import jsmin
            except ImportError as e:
                main_logger.error('ImportError importing jsmin: %s', e)
                raise GrablibError(
                    'Error importing jsmin. Build requirements probably not installed, run `pip install grablib[build]`'
                ) from e
            else:
                self._jsmin = jsmin
        return self._jsmin

    def _read_file(self, file_path: Path):
        content = file_path.read_text()
        if not self.debug and file_path.name.endswith('.js') and not file_path.name.endswith('.min.js'):
            return self.jsmin(content, quote_chars='\'"`')
        return content

    def _write(self, new_path: Path, data):
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_text(data)


class SassGenerator:
    _errors = _files_generated = None

    def __init__(self, *,
                 input_dir: Path,
                 output_dir: Path,
                 include: str=None,
                 exclude: str=None,
                 replace: dict=None,
                 download_root: Path,
                 debug: bool=False,
                 custom_functions: Union[dict, set, list]=(),
                 apply_hash: bool=False):
        self._in_dir = input_dir
        dir_hash = hashlib.md5(str(self._in_dir).encode()).hexdigest()
        self._size_cache_file = Path(tempfile.gettempdir()) / 'grablib_cache.{}.json'.format(dir_hash)
        assert self._in_dir.is_dir()
        self._out_dir = output_dir
        self._debug = debug
        self._apply_hash = apply_hash
        self._custom_functions = custom_functions
        if self._debug:
            self._out_dir_src = self._out_dir / '.src'
            self._src_dir = self._out_dir_src
        else:
            self._src_dir = self._in_dir
        self._include = re.compile(include or '/[^_][^/]+\.(?:css|sass|scss)$')
        self._exclude = exclude and re.compile(exclude)
        self._replace = replace or {}
        self.download_root = download_root
        self._nm = self._find_node_modules()
        self._old_size_cache = {}
        self._new_size_cache = {}

    def __call__(self):
        start = datetime.now()
        self._errors, self._files_generated = 0, 0

        if self._debug:
            self._out_dir.mkdir(parents=True, exist_ok=True)
            if self._out_dir_src.exists():
                raise GrablibError('With debug switched on the directory "{}" must not exist before building, '
                                   'you should delete it with the "wipe" option.'.format(self._out_dir_src))
            shutil.copytree(str(self._in_dir.resolve()), str(self._out_dir_src))

        if self._size_cache_file.exists():
            with self._size_cache_file.open() as f:
                self._old_size_cache = json.load(f)

        self.process_directory(self._src_dir)
        with self._size_cache_file.open('w') as f:
            json.dump(self._new_size_cache, f, indent=2)
        time_taken = (datetime.now() - start).total_seconds() * 1000
        if not self._errors:
            main_logger.info('%d css files generated in %0.0fms, 0 errors', self._files_generated, time_taken)
        else:
            main_logger.error('%d css files generated in %0.0fms, %d errors',
                              self._files_generated, time_taken, self._errors)
            raise GrablibError('sass errors')

    def process_directory(self, d: Path):
        assert d.is_dir()
        for p in d.iterdir():
            if p.is_dir():
                self.process_directory(p)
            else:
                assert p.is_file()
                self.process_file(p)

    def process_file(self, f: Path):
        if not self._include.search(str(f)):
            return
        if self._exclude and self._exclude.search(str(f)):
            return

        rel_path = f.relative_to(self._src_dir)
        css_path = (self._out_dir / rel_path).with_suffix('.css')

        map_path = css_path.with_name(css_path.name + '.map') if self._debug else None

        css = self.generate_css(f, map_path)
        if css is None:
            return
        log_msg = None
        apply_hash = self._apply_hash
        try:
            css_path.parent.mkdir(parents=True, exist_ok=True)
            if self._debug:
                css, css_map = css

                if apply_hash:
                    css_path = insert_hash(css_path, css)
                    map_path = insert_hash(map_path, css)
                    apply_hash = False

                # correct the link to map file in css
                css = re.sub(r'/\*# sourceMappingURL=\S+ \*/', '/*# sourceMappingURL={} */'.format(map_path.name), css)
                map_path.write_text(css_map)
            css, log_msg = self._regex_modify(rel_path, css)
        finally:
            self._log_file_creation(rel_path, css_path, css)
            if log_msg:
                progress_logger.debug(log_msg)

        if apply_hash:
            css_path = insert_hash(css_path, css)
        css_path.write_text(css)
        self._files_generated += 1

    def generate_css(self, f: Path, map_path):
        output_style = 'nested' if self._debug else 'compressed'
        sass = self.get_sass()
        try:
            return sass.compile(
                filename=str(f),
                source_map_filename=map_path and str(map_path),
                output_style=output_style,
                precision=10,
                importers=[(0, self._clever_imports)],
                custom_functions=self._custom_functions,
            )
        except sass.CompileError as e:
            self._errors += 1
            main_logger.error('"%s", compile error: %s', f, e)

    def _regex_modify(self, rel_path, css):
        log_msg = None
        for path_regex, regex_map in self._replace.items():
            if re.search(path_regex, str(rel_path)):
                progress_logger.debug('%s has regex replace matches for "%s"', rel_path, path_regex)
                for pattern, repl in regex_map.items():
                    hash1 = hash(css)
                    css = re.sub(pattern, repl, css)
                    if hash(css) == hash1:
                        log_msg = '  "{}" ➤ "{}" didn\'t modify the source'.format(pattern, repl)
                    else:
                        log_msg = '  "{}" ➤ "{}" modified the source'.format(pattern, repl)
        return css, log_msg

    def _log_file_creation(self, rel_path, css_path, css):
        src, dst = str(rel_path), str(css_path.relative_to(self._out_dir))

        size = len(css)
        p = str(css_path)
        self._new_size_cache[p] = size
        old_size = self._old_size_cache.get(p)
        c = None
        if old_size:
            change_p = (size - old_size) / old_size * 100
            if abs(change_p) > 0.5:
                c = 'green' if change_p <= 0 else 'red'
                change_p = click.style('{:+0.0f}%'.format(change_p), fg=c)
                progress_logger.info('%30s ➤ %-30s %7s %s', src, dst, fmt_size(size), change_p)
        if c is None:
            progress_logger.info('%30s ➤ %-30s %7s', src, dst, fmt_size(size))

    def _clever_imports(self, src_path):
        _new_path = None
        if STARTS_SRC.match(src_path):
            _new_path = self._in_dir.joinpath(STARTS_SRC.sub('', src_path))
        elif self._nm and STARTS_NODE_M.match(src_path):
            _new_path = self._nm.joinpath(STARTS_NODE_M.sub('', src_path))
        elif self.download_root and STARTS_DOWNLOAD.match(src_path):
            _new_path = self.download_root.joinpath(STARTS_DOWNLOAD.sub('', src_path))

        return _new_path and [(str(_new_path),)]

    def _find_node_modules(self):
        for d in self._in_dir.parents:
            nm = d / 'node_modules'
            if nm.is_dir():
                return nm

    def get_sass(self):
        try:
            import sass
        except ImportError as e:
            main_logger.error('ImportError importing sass: %s', e)
            raise GrablibError(
                'Error importing sass. Build requirements probably not installed, run `pip install grablib[build]`'
            ) from e
        return sass


KB, MB = 1024, 1024 ** 2


def fmt_size(num):
    if num <= KB:
        return '{:0.0f}B'.format(num)
    elif num <= MB:
        return '{:0.1f}KB'.format(num / KB)
    else:
        return '{:0.1f}MB'.format(num / MB)
