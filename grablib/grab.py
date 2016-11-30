import collections
import json
import re
from pathlib import Path

import yaml
from yaml.scanner import MarkedYAMLError

from .common import GrablibError, logger
from .download import Downloader
# from . import download, minify


YAML_MATCH = re.compile('grablib\.ya?ml')
JSON_MATCH = re.compile('grablib\.json')
STD_FILE_NAMES = [YAML_MATCH, JSON_MATCH]


def yaml_or_json(file_path:  Path):
    if YAML_MATCH.fullmatch(file_path.name):
        logger.debug('Processing %s as a yaml file', file_path)
        return yaml_load
    elif JSON_MATCH.fullmatch(file_path.name):
        logger.debug('Processing %s as a json file', file_path)
        return json_load
    else:
        raise GrablibError('Unexpected extension for "{}", should be json or yml/yaml'.format(file_path))


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


def grab(*, config_file: str=None, download_root: str=None):
    """
    Process a file or json string defining files to download and what to do with them.

    :param config_file: relative path to file defining what to download
    :param download_root: root_directory to download to
    """
    if config_file:
        config_path = Path(config_file).resolve()
    else:
        config_path = find_config_file()
    loader = yaml_or_json(config_path)
    with config_path.open() as f:
        try:
            config_data = loader(f)
        except (MarkedYAMLError, ValueError) as e:
            logger.error('%s: %s', e.__class__.__name__, e)
            raise GrablibError('error loading "{}"'.format(config_file))
    if download_root:
        config_data['download_root'] = download_root

    download = Downloader(**config_data)
    download()
    # if libs_info:
    #     download.DownloadLibs(libs_info, **options).download()
    # if minify_info:
    #     minify.MinifyLibs(minify_info, **options).minify()


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


def json_load(f):
    return json.load(f, object_pairs_hook=collections.OrderedDict)
