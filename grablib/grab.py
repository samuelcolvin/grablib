import collections
import json
import re
from pathlib import Path

import yaml
from yaml.scanner import MarkedYAMLError

from .build import Builder
from .common import GrablibError, main_logger
from .download import Downloader

STD_FILE_NAMES = [re.compile('grablib\.ya?ml'), re.compile('grablib\.json')]


class Grab:
    def __init__(self, config_file: str=None, *, download_root: str=None, debug=None):
        """
        Process a file or json string defining files to download and what to do with them.

        :param config_file: relative path to file defining what to download
        :param download_root: root_directory to download to
        :param debug: whether to run in debug mode
        """
        if config_file:
            config_path = Path(config_file).resolve()
        else:
            config_path = self.find_config_file()
        loader = self.yaml_or_json(config_path)
        with config_path.open() as f:
            try:
                self.config_data = loader(f)
            except (MarkedYAMLError, ValueError) as e:
                main_logger.error('%s: %s', e.__class__.__name__, e)
                raise GrablibError('error loading "{}"'.format(config_file))
        if download_root:
            self.config_data['download_root'] = download_root
        if debug is not None:
            self.config_data['debug'] = debug

    def download(self):
        if 'download' not in self.config_data:
            main_logger.warning('download called with no "download" info available')
            return
        download = Downloader(**self.config_data)
        download()

    def build(self):
        if 'build' not in self.config_data:
            main_logger.warning('build called with no "build" info available')
            return
        build = Builder(**self.config_data)
        build()

    @classmethod
    def yaml_or_json(cls, file_path:  Path):
        if file_path.name.endswith(('.yml', '.yaml')):
            main_logger.debug('Processing %s as a yaml file', file_path)
            return cls.yaml_load
        elif file_path.name.endswith('.json'):
            main_logger.debug('Processing %s as a json file', file_path)
            return cls.json_load
        else:
            raise GrablibError('Unexpected extension for "{}", should be json or yml/yaml'.format(file_path.name))

    @staticmethod
    def find_config_file():
        p = Path('.').resolve()
        files = [x for x in p.iterdir() if x.is_file()]
        for std_file_name in STD_FILE_NAMES:
            try:
                return next(f for f in files if std_file_name.fullmatch(f.name))
            except StopIteration:
                pass
        raise GrablibError('Unable to find config file with standard name "grablib.yml" or "grablib.json" in the '
                           'current working directory')

    @staticmethod
    def yaml_load(f):
        class OrderedLoader(yaml.Loader):
            pass

        def construct_mapping(loader, node):
            loader.flatten_mapping(node)
            return collections.OrderedDict(loader.construct_pairs(node))
        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_mapping)
        return yaml.load(f, OrderedLoader)

    @staticmethod
    def json_load(f):
        return json.load(f, object_pairs_hook=collections.OrderedDict)
