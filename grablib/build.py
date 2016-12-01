import re
import shutil
from datetime import datetime
from pathlib import Path

import sass
from jsmin import jsmin

from .common import GrablibError, logger


class Builder:
    """
    main class for "building" assets eg. concatenating and minifying js and compiling sass
    """

    def __init__(self, *, build_root, build, download_root: str=None, debug=False, **data):
        self.build_root = Path(build_root).absolute()
        self.build = build
        self.download_root = download_root and Path(download_root).resolve()
        self.files_built = 0
        self.debug = debug

    def __call__(self):
        cat_data = self.build.get('cat', None)
        if cat_data:
            self.cat(cat_data)
        sass_data = self.build.get('sass', None)
        if sass_data:
            self.sass(sass_data)

    def cat(self, data):
        for dest, srcs in data.items():
            if not isinstance(srcs, list):
                raise GrablibError('concatenating: source files should be a list')

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

            if files_combined == 0:
                logger.warning('no files found to form "%s"', dest)
                continue
            dest_path = self.build_root.joinpath(dest)
            dest_path.relative_to(self.build_root)
            self._write(dest_path, final_content)
            logger.info('%d files combined to form "%s"', files_combined, dest)

    def sass(self, data):
        for dest, src in data.items():
            src_path = self._file_path(src)
            dest_path = self.build_root.joinpath(dest)
            dest_path.relative_to(self.build_root)
            sass_gen = SassGenerator(src_path, dest_path, self.debug)
            sass_gen()

    starts_download = re.compile('^(?:DOWNLOAD|DL)/')

    def _file_path(self, src_path: str):
        if self.starts_download.match(src_path):
            assert self.download_root
            _src_path = self.starts_download.sub('', src_path)
            return self.download_root.joinpath(_src_path).resolve()
        else:
            return Path(src_path).resolve()

    def _read_file(self, file_path: Path):
        content = file_path.read_text()
        if not self.debug and file_path.name.endswith('.js') and not file_path.name.endswith('.min.js'):
            return jsmin(content)
        return content

    def _write(self, new_path: Path, data):
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_text(data)


class SassGenerator:
    _errors = _files_generated = None

    def __init__(self, input_dir: Path, output_dir: Path, debug: bool=False):
        self._in_dir = input_dir
        assert self._in_dir.is_dir()
        self._out_dir = output_dir
        self._debug = debug
        if self._debug:
            self._out_dir_src = self._out_dir / '.src'
            self._src_dir = self._out_dir_src
        else:
            self._src_dir = self._in_dir

    def __call__(self):
        start = datetime.now()
        self._errors, self._files_generated = 0, 0
        # if self._out_dir.exists():
        #     shutil.rmtree(str(self._out_dir.resolve()))

        if self._debug:
            # self._out_dir.mkdir(parents=True)
            self._out_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(self._in_dir.resolve()), str(self._out_dir_src))

        self.process_directory(self._src_dir)
        time_taken = (datetime.now() - start).total_seconds() * 1000
        if self._errors:
            raise GrablibError('%d errors building sass' % self._errors)
        logger.info('%d css files generated in %0.0fms, %d errors', self._files_generated, time_taken, self._errors)

    def process_directory(self, d: Path):
        assert d.is_dir()
        for p in d.iterdir():
            if p.is_dir():
                self.process_directory(p)
            else:
                assert p.is_file()
                self.process_file(p)

    def process_file(self, f: Path):
        if f.suffix not in {'.css', '.scss', '.sass'}:
            return

        if f.name.startswith('_'):
            # mixin, not copied
            return

        rel_path = f.relative_to(self._src_dir)
        css_path = (self._out_dir / rel_path).with_suffix('.css')

        map_path = None
        if self._debug:
            map_path = css_path.with_suffix('.map')

        logger.debug('%s ▶ %s', rel_path, css_path.relative_to(self._out_dir))
        css = self.generate_css(f, map_path)
        if not css:
            return

        css_path.parent.mkdir(parents=True, exist_ok=True)
        if self._debug:
            css, css_map = css
            # correct the link to map file in css
            css = re.sub(r'/\*# sourceMappingURL=\S+ \*/', '/*# sourceMappingURL={} */'.format(map_path.name), css)
            map_path.write_text(css_map)
        css_path.write_text(css)
        self._files_generated += 1

    def generate_css(self, f: Path, map_path=None):
        output_style = 'nested' if self._debug else 'compressed'

        try:
            return sass.compile(
                filename=str(f),
                source_map_filename=map_path and str(map_path),
                output_style=output_style,
                precision=10,
            )
        except sass.CompileError as e:
            self._errors += 1
            logger.error('"%s", compile error: %s', f, e)
