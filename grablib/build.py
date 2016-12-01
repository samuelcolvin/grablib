import re
from pathlib import Path

from jsmin import jsmin
from .common import GrablibError, logger


class Builder:
    """
    main class for "building" assets eg. concatenating and minifying js and compiling sass
    """

    def __init__(self, *, build_root, build, download_root: str=None, **data):
        self.build_root = Path(build_root).absolute()
        self.build = build
        self.download_root = download_root and Path(download_root).resolve()
        self.files_built = 0

    def __call__(self):
        cat_data = self.build.get('cat', None)
        if cat_data:
            self.cat(cat_data)

    def cat(self, data):
        for dest, srcs in data.items():
            if not isinstance(srcs, list):
                raise GrablibError('concatenating: source files should be a list')
            minify = dest.endswith('.min.js')

            final_content, files_combined = '', 0
            for src in srcs:
                regexes = {}
                if not isinstance(src, str):
                    # here we assume we have a 2 element list, first item being the src, second be a dict of regexes
                    src, regexes = src
                path = self._file_path(src)
                content = self._read_file(path, minify)
                files_combined += 1
                for pattern, rep in regexes.items():
                    content = re.sub(pattern, rep, content)
                final_content += '/* === {} === */\n{}\n'.format(path.name, content.strip('\n'))

            if files_combined == 0:
                logger.warning('no files found to form "%s"', dest)
                continue
            dest_path = self.build_root.joinpath(dest)
            dest_path.relative_to(self.build_root)
            self._write(dest_path, final_content)
            logger.info('%d files combined to form "%s"', files_combined, dest)

    starts_download = re.compile('^(?:DOWNLOAD|DL)/')

    def _file_path(self, src_path: str):
        if self.starts_download.match(src_path):
            assert self.download_root
            _src_path = self.starts_download.sub('', src_path)
            return self.download_root.joinpath(_src_path).resolve()
        else:
            return Path(src_path).resolve()

    @staticmethod
    def _read_file(file_path: Path, minify):
        content = file_path.read_text()
        if minify and file_path.name.endswith('.js') and not file_path.name.endswith('.min.js'):
            return jsmin(content)
        return content

    def _write(self, new_path: Path, data):
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_text(data)
